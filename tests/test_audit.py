#!/usr/bin/env python3
"""Deterministic audit checks - pytest version of AUDIT.md checklist items that can be automated."""

import json
import io
import os
import sys
import tempfile
from importlib import reload

sys.path.insert(0, os.path.dirname(__file__))

import pytest

from contextlib import redirect_stdout
from datetime import date

from conftest import close_session


@pytest.fixture
def audit_db():
    """Create a temp DB with test data for audit checks."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.environ["REPS_DB"] = path
    import reps.db
    reps.db.DB = path
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
    log.cmd_log("pullup", 0, 5, "", "back,biceps")


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
    close_session(log, "done")

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


def _seed_jump(c, second_notes):
    """Two done workouts 3 days apart: bench 100x5 then 130x5 (~30% e1RM jump)."""
    from datetime import date, timedelta
    base = date.today() - timedelta(days=9)
    for offset, weight, notes in [(0, 100, ""), (3, 130, second_notes)]:
        d = (base + timedelta(days=offset)).isoformat()
        cur = c.execute("INSERT INTO workouts (date, status, notes) VALUES (?, 'done', ?)", (d, notes))
        c.commit()
        wid = cur.lastrowid
        cur2 = c.execute("INSERT INTO sets (workout_id, exercise, weight, reps, note, created) VALUES (?, 'bench', ?, 5, '', datetime('now'))", (wid, weight))
        c.execute("INSERT INTO set_muscles (set_id, muscle) VALUES (?, 'chest')", (cur2.lastrowid,))
        c.commit()


def _run_cmd_audit(log):
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        log.cmd_audit()
        return sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout


def test_cmd_audit_flags_unexplained_jump(audit_db):
    """cmd_audit check 4: unexplained ~30% e1RM jump is flagged."""
    log, c = audit_db
    _seed_jump(c, "")
    out = _run_cmd_audit(log)
    flags = json.loads(out.strip().splitlines()[-1])["flags"]
    jumps = [f for f in flags if f["check"] == "progression_jump"]
    assert len(jumps) == 1
    assert jumps[0]["severity"] == "high"


def test_cmd_audit_skips_explained_jump(audit_db):
    """cmd_audit check 4: jump explained by workout note is skipped."""
    log, c = audit_db
    _seed_jump(c, "return after deload week")
    out = _run_cmd_audit(log)
    flags = json.loads(out.strip().splitlines()[-1])["flags"]
    assert [f for f in flags if f["check"] == "progression_jump"] == []


def _seed_progression(c, first, second):
    """Two done workouts 3 days apart with given (weight, reps) bench sets."""
    from datetime import date, timedelta
    base = date.today() - timedelta(days=9)
    for offset, (weight, reps) in [(0, first), (3, second)]:
        d = (base + timedelta(days=offset)).isoformat()
        cur = c.execute("INSERT INTO workouts (date, status, notes) VALUES (?, 'done', '')", (d,))
        c.commit()
        wid = cur.lastrowid
        cur2 = c.execute("INSERT INTO sets (workout_id, exercise, weight, reps, note, created) VALUES (?, 'bench', ?, ?, '', datetime('now'))", (wid, weight, reps))
        c.execute("INSERT INTO set_muscles (set_id, muscle) VALUES (?, 'chest')", (cur2.lastrowid,))
        c.commit()


def _progression_jumps(log):
    out = _run_cmd_audit(log)
    flags = json.loads(out.strip().splitlines()[-1])["flags"]
    return [f for f in flags if f["check"] == "progression_jump"]


def test_cmd_audit_ignores_routine_rep_pr(audit_db):
    """check 4: +1 rep (+2.9% e1RM) is below the 2-6 band bound, no flag."""
    log, c = audit_db
    _seed_progression(c, (100, 5), (100, 6))
    assert _progression_jumps(log) == []


def test_cmd_audit_ignores_high_rep_plus_one(audit_db):
    """check 4: +1 rep at high reps (+3.3%) is below the 11-15 band bound."""
    log, c = audit_db
    _seed_progression(c, (80, 12), (80, 13))
    assert _progression_jumps(log) == []


def test_cmd_audit_skips_above_15_reps(audit_db):
    """check 4: e1RM above 15 reps never flags, however large the jump."""
    log, c = audit_db
    _seed_progression(c, (100, 16), (140, 16))
    assert _progression_jumps(log) == []


def test_cmd_audit_flags_single_to_double(audit_db):
    """check 4: same-weight single to double (+6.7%) exceeds the low band."""
    log, c = audit_db
    _seed_progression(c, (100, 1), (100, 2))
    jumps = _progression_jumps(log)
    assert len(jumps) == 1
    assert jumps[0]["severity"] == "high"


def _seed_muscle_weeks(c, muscle, week_sets):
    """One done workout (Wednesday) per listed week: {weeks_ago: set_count}."""
    from datetime import date, timedelta
    monday = date.today() - timedelta(days=date.today().weekday())
    for ago, nsets in week_sets.items():
        d = (monday - timedelta(weeks=ago) + timedelta(days=2)).isoformat()
        cur = c.execute("INSERT INTO workouts (date, status, notes) VALUES (?, 'done', '')", (d,))
        c.commit()
        wid = cur.lastrowid
        for _ in range(nsets):
            cur2 = c.execute("INSERT INTO sets (workout_id, exercise, weight, reps, note, created) VALUES (?, 'bench', 100, 5, '', datetime('now'))", (wid,))
            c.execute("INSERT INTO set_muscles (set_id, muscle) VALUES (?, ?)", (cur2.lastrowid, muscle))
        c.commit()


def _chest_volume_flags(log, check):
    out = _run_cmd_audit(log)
    flags = json.loads(out.strip().splitlines()[-1])["flags"]
    return [f for f in flags if f["check"] == check and f["evidence"].startswith("chest:")]


def test_cmd_audit_volume_zero(audit_db):
    """check 8: 4 of last 8 weeks at zero sets fires volume_zero, high."""
    log, c = audit_db
    _seed_muscle_weeks(c, "chest", {0: 8, 1: 8, 2: 8, 3: 8})
    zeros = _chest_volume_flags(log, "volume_zero")
    assert len(zeros) == 1
    assert zeros[0]["severity"] == "high"
    assert "0 sets in 4 of last 8 weeks" in zeros[0]["evidence"]
    assert _chest_volume_flags(log, "volume_low") == []


def test_cmd_audit_mev_zero_never_flags_zero(audit_db):
    """check 8: MEV 0 muscles (front delts) never flag volume_zero, zero meets the floor."""
    log, c = audit_db
    out = _run_cmd_audit(log)
    flags = json.loads(out.strip().splitlines()[-1])["flags"]
    front_zero = [f for f in flags if f["check"] == "volume_zero" and f["evidence"].startswith("front delts:")]
    assert front_zero == []
    # sanity: a nonzero-MEV muscle with no data still flags
    assert _chest_volume_flags(log, "volume_zero") != []


def test_cmd_audit_volume_low(audit_db):
    """check 8: 4 of last 8 weeks low-but-nonzero fires volume_low, medium."""
    log, c = audit_db
    _seed_muscle_weeks(c, "chest", {0: 2, 1: 2, 2: 2, 3: 2, 4: 8, 5: 8, 6: 8, 7: 8})
    lows = _chest_volume_flags(log, "volume_low")
    assert len(lows) == 1
    assert lows[0]["severity"] == "medium"
    assert "below MEV in 4 of last 8 weeks" in lows[0]["evidence"]
    assert _chest_volume_flags(log, "volume_zero") == []


def test_cmd_audit_volume_scattered_below_threshold(audit_db):
    """check 8: 3 bad weeks out of 8 fires nothing."""
    log, c = audit_db
    _seed_muscle_weeks(c, "chest", {0: 8, 1: 8, 2: 8, 3: 8, 4: 8})
    assert _chest_volume_flags(log, "volume_zero") == []
    assert _chest_volume_flags(log, "volume_low") == []


def test_cmd_audit_volume_no_streak_reset(audit_db):
    """check 8: a good week splitting bad weeks does not reset the count."""
    log, c = audit_db
    _seed_muscle_weeks(c, "chest", {2: 8, 5: 8, 6: 8, 7: 8})
    zeros = _chest_volume_flags(log, "volume_zero")
    assert len(zeros) == 1
    assert "0 sets in 4 of last 8 weeks" in zeros[0]["evidence"]


def test_cmd_audit_volume_never_trained(audit_db):
    """check 8: a muscle absent from every week still flags as zero."""
    log, c = audit_db
    zeros = _chest_volume_flags(log, "volume_zero")
    assert len(zeros) == 1
    assert zeros[0]["severity"] == "high"
    assert "0 sets in 8 of last 8 weeks" in zeros[0]["evidence"]


EXPECTED_MEV = {
    "chest": 8, "back": 10, "front delts": 0, "side delts": 6, "rear delts": 6,
    "biceps": 6, "triceps": 6, "quads": 8, "hamstrings": 6, "glutes": 6,
    "adductors": 4, "abs": 6, "forearms": 6,
}

JSON_BLOCK = """```json mev-bounds
{
  "chest": 8,
  "back": 10,
  "front delts": 0,
  "side delts": 6,
  "rear delts": 6,
  "biceps": 6,
  "triceps": 6,
  "quads": 8,
  "hamstrings": 6,
  "glutes": 6,
  "adductors": 4,
  "abs": 6,
  "forearms": 6
}
```"""


def test_parse_mev_reads_constants(audit_db):
    """parse_mev_from_science returns the MEV map from constants.json."""
    log, _ = audit_db
    assert log.parse_mev_from_science() == EXPECTED_MEV


def test_load_constants_fails_loud_on_bad_json(audit_db, tmp_path, monkeypatch):
    """Unparseable constants.json exits instead of falling back silently."""
    import json as _json
    log, _ = audit_db
    p = tmp_path / "constants.json"
    p.write_text("{not json")
    monkeypatch.setattr("reps.constants.CONSTANTS_FILE", str(p))
    with pytest.raises(SystemExit, match="unreadable"):
        log.load_constants()


def test_load_constants_fails_on_empty_muscles(audit_db, tmp_path, monkeypatch):
    """A constants file with an empty muscles map exits instead of warning."""
    import json as _json
    import reps.constants
    log, _ = audit_db
    full = _json.loads(open(reps.constants.CONSTANTS_FILE).read())
    full["muscles"] = {}
    p = tmp_path / "constants.json"
    p.write_text(_json.dumps(full))
    monkeypatch.setattr("reps.constants.CONSTANTS_FILE", str(p))
    with pytest.raises(SystemExit, match="muscles"):
        log.load_constants()


def test_doctor_flags_deleted_tracked_muscle(audit_db):
    """Deleting a tracked muscle still referenced by sets fails doctor, not load."""
    log, c = audit_db
    log.cmd_start("test")
    log.cmd_log("bench", 100, 5, "", "chest")
    c.execute("DELETE FROM lift_muscle_map WHERE exercise = 'bench'")
    import json as _json
    import reps.constants
    full = _json.loads(open(reps.constants.CONSTANTS_FILE).read())
    del full["muscles"]["chest"]
    import tempfile, os
    fd, path = tempfile.mkstemp(suffix=".json")
    os.write(fd, _json.dumps(full).encode())
    os.close(fd)
    old = reps.constants.CONSTANTS_FILE
    reps.constants.CONSTANTS_FILE = path
    try:
        buf = io.StringIO()
        with redirect_stdout(buf):
            try:
                log.cmd_doctor()
                assert False, "should have exited"
            except SystemExit as e:
                assert e.code == 1
        assert "chest" in buf.getvalue()
    finally:
        reps.constants.CONSTANTS_FILE = old
        os.unlink(path)


def test_rep_band_bound_uses_constants(audit_db):
    """Rep-band thresholds come from constants.json, None above 15 reps."""
    log, _ = audit_db
    assert log.rep_band_bound(5) == 4.0
    assert log.rep_band_bound(8) == 5.0
    assert log.rep_band_bound(13) == 8.0
    assert log.rep_band_bound(16) is None


def test_priority_set_and_list(audit_db):
    """priority set writes the table, list reads it back."""
    log, _ = audit_db
    log.cmd_priority_set("side delts", "priority", None)
    assert log.read_priorities(log.conn()) == {
        "side delts": {"tier": "priority", "since": date.today().isoformat(), "until": None}
    }


def test_priority_rejects_untracked_muscle(audit_db):
    """Tier A: writing a priority tier for an untracked muscle fails."""
    log, _ = audit_db
    with pytest.raises(SystemExit, match="not a tracked muscle"):
        log.cmd_priority_set("neck", "priority", None)


def test_priority_rejects_bad_tier(audit_db):
    log, _ = audit_db
    with pytest.raises(SystemExit, match="tier must be"):
        log.cmd_priority_set("chest", "urgent", None)


def test_cmd_audit_downgrades_deprioritized_volume(audit_db, tmp_path, monkeypatch):
    """check 8: a deprioritize muscle still flags, one severity lower, annotated."""
    log, c = audit_db
    log.cmd_priority_set("chest", "deprioritize", None)
    _seed_muscle_weeks(c, "chest", {0: 8, 1: 8, 2: 8, 3: 8})
    zeros = _chest_volume_flags(log, "volume_zero")
    assert len(zeros) == 1
    assert zeros[0]["severity"] == "medium"
    assert "priority: deprioritize" in zeros[0]["evidence"]


def test_cmd_audit_no_downgrade_without_priority_entry(audit_db, tmp_path, monkeypatch):
    """check 8: without a priority entry the same data flags at full severity."""
    log, c = audit_db
    _seed_muscle_weeks(c, "chest", {0: 8, 1: 8, 2: 8, 3: 8})
    zeros = _chest_volume_flags(log, "volume_zero")
    assert len(zeros) == 1
    assert zeros[0]["severity"] == "high"
    assert "priority: deprioritize" not in zeros[0]["evidence"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
