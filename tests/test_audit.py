#!/usr/bin/env python3
"""Deterministic audit checks - pytest version of AUDIT.md checklist items that can be automated."""

import json
import os
import sys
import tempfile
from importlib import reload

sys.path.insert(0, os.path.dirname(__file__))

import pytest


@pytest.fixture
def audit_db():
    """Create a temp DB with test data for audit checks."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.environ["REPS_DB"] = path
    import log
    reload(log)
    from log import conn
    c = conn()
    yield log, c
    try:
        os.unlink(path)
    except OSError:
        pass


def test_audit_missing_muscle_tags(audit_db):
    """Check 2: Find sets where muscles is empty or ''."""
    log, c = audit_db
    log.cmd_start("test")
    log.cmd_log("bench", 100, 5, "", "chest")
    # Insert directly to bypass validation for audit test (no junction rows)
    wid = c.execute("SELECT id FROM workouts WHERE status = 'open'").fetchone()["id"]
    c.execute("INSERT INTO sets (workout_id, exercise, weight, reps, note, created) VALUES (?, 'squat', 150, 5, '', datetime('now'))", (wid,))
    c.commit()

    missing = c.execute("""
        SELECT s.id, s.exercise FROM sets s
        LEFT JOIN set_muscles sm ON sm.set_id = s.id
        WHERE sm.muscle IS NULL
    """).fetchall()
    assert len(missing) == 1
    assert missing[0]["exercise"] == "squat"


def test_audit_zero_weight_non_bodyweight(audit_db):
    """Zero weight sets only allowed for bodyweight exercises."""
    log, c = audit_db
    log.cmd_start("test")
    # This should fail - bench is not a bodyweight exercise
    try:
        log.cmd_log("bench", 0, 5, "", "chest")
        assert False, "should have exited"
    except SystemExit as e:
        assert "zero weight not allowed" in str(e).lower()

    # Set up pullup as bodyweight exercise
    c.execute("INSERT INTO lift_muscle_map (exercise, muscles, is_bodyweight_only) VALUES (?, ?, ?)",
              ("pullup", "back,biceps", 1))
    c.commit()

    # This should work - pullup is bodyweight
    log.cmd_log("pullup", 0, 5, "", "back")


def test_audit_muscle_mapping_drift(audit_db):
    """Check 3: Compare logged muscles against lift_muscle_map."""
    log, c = audit_db
    log.cmd_start("test")
    log.cmd_log("bench", 100, 5, "", "chest")  # creates mapping chest
    log.cmd_log("squat", 150, 5, "", "quads,glutes")  # creates mapping quads,glutes
    log.cmd_end("done")

    # Manually corrupt one set's muscles via the junction table
    bench_id = c.execute("SELECT id FROM sets WHERE exercise = 'bench'").fetchone()["id"]
    c.execute("DELETE FROM set_muscles WHERE set_id = ?", (bench_id,))
    c.execute("INSERT INTO set_muscles (set_id, muscle) VALUES (?, 'back')", (bench_id,))
    c.commit()

    # Check for drift (compare as sets, order-insensitive)
    drift = c.execute("""
        SELECT s.id, s.exercise,
               group_concat(sm.muscle, ',') as logged,
               m.muscles as mapped
        FROM sets s
        JOIN lift_muscle_map m ON m.exercise = s.exercise
        LEFT JOIN set_muscles sm ON sm.set_id = s.id
        GROUP BY s.id
    """).fetchall()
    drift = [d for d in drift
             if set((d["logged"] or "").split(",")) != set(d["mapped"].split(","))]

    assert len(drift) == 1
    assert drift[0]["exercise"] == "bench"
    assert drift[0]["logged"] == "back"
    assert drift[0]["mapped"] == "chest"


def test_audit_stale_open_workout(audit_db):
    """Check 7: Stale open workouts (age_days >= 1 or gap > 8h)."""
    from datetime import date, timedelta
    log, c = audit_db

    # Create a workout from yesterday
    d_yesterday = (date.today() - timedelta(days=1)).isoformat()
    cur = c.execute("INSERT INTO workouts (date, status, notes) VALUES (?, 'open', 'stale')", (d_yesterday,))
    c.commit()
    wid = cur.lastrowid
    cur2 = c.execute("INSERT INTO sets (workout_id, exercise, weight, reps, note, created) VALUES (?, 'bench', 100, 5, '', datetime('now'))", (wid,))
    c.execute("INSERT INTO set_muscles (set_id, muscle) VALUES (?, 'chest')", (cur2.lastrowid,))
    c.commit()

    # Also create a fresh open workout
    log.cmd_start("fresh")
    log.cmd_log("bench", 100, 5, "", "chest")

    stale = c.execute("""
        SELECT w.id, w.date FROM workouts w
        WHERE w.status = 'open'
          AND (date(w.date) < date('now') OR
               (SELECT MAX(created) FROM sets WHERE workout_id = w.id) < datetime('now', '-8 hours'))
    """).fetchall()

    assert len(stale) >= 1
    assert any(s["id"] == wid for s in stale)


def test_audit_duplicate_exercise_names(audit_db):
    """Check 1: Exercise name duplicates (Levenshtein <= 2)."""
    import itertools

    def levenshtein(a, b):
        if len(a) < len(b):
            a, b = b, a
        if len(b) == 0:
            return len(a)
        previous_row = list(range(len(b) + 1))
        for i, ca in enumerate(a):
            current_row = [i + 1]
            for j, cb in enumerate(b):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (ca != cb)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        return previous_row[-1]

    log, c = audit_db
    log.cmd_start("test")
    # Add some exercises with near-duplicate names (Levenshtein <= 2)
    for ex in ["bench", "benches", "squat", "sqaut", "deadlift"]:
        log.cmd_log(ex, 100, 5, "", "chest")
    log.cmd_end("done")

    exercises = [r["exercise"] for r in c.execute("SELECT DISTINCT exercise FROM sets").fetchall()]

    near_dupes = []
    for a, b in itertools.combinations(exercises, 2):
        if levenshtein(a, b) <= 2:
            near_dupes.append((a, b))

    # Should find near-duplicates (bench/benches, squat/sqaut)
    assert len(near_dupes) >= 1


def test_audit_progression_jumps(audit_db):
    """Check 4: Implausible e1RM jumps (> bounds per SCIENCE.md)."""
    from datetime import date, timedelta
    log, c = audit_db

    # Create sessions with normal progression on different days
    base = date.today() - timedelta(days=20)
    for i, w in enumerate([100, 102.5, 105, 107.5, 110]):  # ~2.5% jumps
        d = (base + timedelta(days=i*3)).isoformat()
        cur = c.execute("INSERT INTO workouts (date, status, notes) VALUES (?, 'done', '')", (d,))
        c.commit()
        wid = cur.lastrowid
        cur2 = c.execute("INSERT INTO sets (workout_id, exercise, weight, reps, note, created) VALUES (?, 'bench', ?, 5, '', datetime('now'))", (wid, w))
        c.execute("INSERT INTO set_muscles (set_id, muscle) VALUES (?, 'chest')", (cur2.lastrowid,))
        c.commit()

    # Add an implausible jump (20%) on a later date
    d = (base + timedelta(days=20)).isoformat()
    cur = c.execute("INSERT INTO workouts (date, status, notes) VALUES (?, 'done', '')", (d,))
    c.commit()
    wid = cur.lastrowid
    cur2 = c.execute("INSERT INTO sets (workout_id, exercise, weight, reps, note, created) VALUES (?, 'bench', 132, 5, '', datetime('now'))", (wid,))
    c.execute("INSERT INTO set_muscles (set_id, muscle) VALUES (?, 'chest')", (cur2.lastrowid,))
    c.commit()

    # Check for jumps > 1% (intermediate compound bound from SCIENCE.md)
    sets = c.execute("""
        SELECT s.id, s.weight, s.reps, w.date,
               s.weight * (1 + s.reps / 30.0) as e1rm
        FROM sets s JOIN workouts w ON w.id = s.workout_id
        WHERE s.exercise = 'bench' ORDER BY w.date, s.id
    """).fetchall()

    # Compute session-to-session e1RM changes
    by_session = {}
    for s in sets:
        d = s["date"]
        if d not in by_session:
            by_session[d] = s["e1rm"]
        else:
            by_session[d] = max(by_session[d], s["e1rm"])

    dates = sorted(by_session.keys())
    big_jumps = []
    for i in range(1, len(dates)):
        prev = by_session[dates[i-1]]
        curr = by_session[dates[i]]
        if prev > 0:
            pct = (curr - prev) / prev * 100
            if pct > 1.0:  # intermediate compound bound
                big_jumps.append((dates[i-1], dates[i], pct))

    assert len(big_jumps) >= 1
    assert big_jumps[-1][2] > 15  # the 20% jump


def test_audit_volume_below_mev(audit_db):
    """Check 8: Muscle groups below MEV for 4+ consecutive weeks."""
    from datetime import date, timedelta
    log, c = audit_db

    # Add data across 5 weeks with low chest volume
    base = date.today() - timedelta(weeks=6)
    for week in range(5):
        d = (base + timedelta(weeks=week)).isoformat()
        cur = c.execute("INSERT INTO workouts (date, status, notes) VALUES (?, 'done', '')", (d,))
        c.commit()
        wid = cur.lastrowid
        for ex, wt, rp in [("bench", 100, 5), ("fly", 20, 10)]:
            cur2 = c.execute("INSERT INTO sets (workout_id, exercise, weight, reps, note, created) VALUES (?, ?, ?, ?, '', datetime('now'))", (wid, ex, wt, rp))
            c.execute("INSERT INTO set_muscles (set_id, muscle) VALUES (?, 'chest')", (cur2.lastrowid,))
        c.commit()

    # Compute weekly chest sets
    weeks = c.execute("""
        SELECT strftime('%Y-%W', w.date) as week, COUNT(*) as sets
        FROM sets s JOIN workouts w ON w.id = s.workout_id
        JOIN set_muscles sm ON sm.set_id = s.id
        WHERE sm.muscle = 'chest'
        GROUP BY week ORDER BY week
    """).fetchall()

    # MEV for chest is 8 sets/week from SCIENCE.md
    mev = 8
    low_weeks = sum(1 for w in weeks if w["sets"] < mev)

    # With only 2 sets/week, all 5 weeks are below MEV
    assert low_weeks == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
