#!/usr/bin/env python3
"""pytest suite for hardening guards: log/update warnings and state refusals."""

import io
import json
import sys
from datetime import date, timedelta


def capture_stdout(fn, *args, **kwargs):
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        fn(*args, **kwargs)
        return sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout


def test_log_warns_on_magnitude_jump_but_logs(log_module):
    """A 2x e1RM jump warns without blocking."""
    log_module.cmd_start("test")
    log_module.cmd_log("bench", 100, 5, "", "chest")
    out = json.loads(capture_stdout(log_module.cmd_log, "bench", 200, 5, "", "chest"))
    assert "warnings" in out
    assert any("50%" in w for w in out["warnings"])
    assert "set_id" in out


def test_log_warns_on_same_workout_collapse(log_module):
    """Under a third of this workout's earlier e1RM warns."""
    log_module.cmd_start("test")
    log_module.cmd_log("bench", 100, 5, "", "chest")
    out = json.loads(capture_stdout(log_module.cmd_log, "bench", 10, 5, "", "chest"))
    assert "warnings" in out
    assert any("third" in w for w in out["warnings"])


def test_log_warns_on_near_duplicate_name(log_module):
    """A typo'd exercise name warns with the existing spelling."""
    c = log_module.conn()
    log_module.cmd_start("test")
    log_module.cmd_log("flat barbell bench press", 90, 5, "", "chest")
    out = json.loads(capture_stdout(log_module.cmd_log, "flat barbell bench pres", 90, 5, "", "chest"))
    assert "warnings" in out
    assert any("flat barbell bench press" in w for w in out["warnings"])


def test_log_warns_on_stale_open_workout(log_module):
    """Logging into a previous day's open workout warns."""
    c = log_module.conn()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    c.execute("INSERT INTO workouts (date, status, notes) VALUES (?, 'open', '')", (yesterday,))
    c.commit()
    out = json.loads(capture_stdout(log_module.cmd_log, "bench", 100, 5, "", "chest"))
    assert "warnings" in out
    assert any(yesterday in w for w in out["warnings"])


def test_log_warns_on_muscle_drift(log_module):
    """Muscles differing from the mapping warn, mapping kept for the set."""
    c = log_module.conn()
    log_module.cmd_start("test")
    log_module.cmd_log("bench", 100, 5, "", "chest")
    out = json.loads(capture_stdout(log_module.cmd_log, "bench", 100, 5, "", "back"))
    assert "warnings" in out
    assert any("mapping kept" in w for w in out["warnings"])


def test_log_clean_sets_have_no_warnings_key(log_module):
    """Normal logging output shape is unchanged."""
    log_module.cmd_start("test")
    out = json.loads(capture_stdout(log_module.cmd_log, "bench", 100, 5, "", "chest"))
    assert "warnings" not in out


def test_update_rejects_missing_set(log_module):
    """Updating a nonexistent set exits instead of reporting success."""
    try:
        log_module.cmd_update("9999", "note", "x")
        assert False, "should have exited"
    except SystemExit as e:
        assert "no such set" in str(e).lower()


def test_update_rejects_garbage_id(log_module):
    """Non-numeric ids exit cleanly, no traceback."""
    try:
        log_module.cmd_update("abc", "note", "x")
        assert False, "should have exited"
    except SystemExit as e:
        assert "no such set" in str(e).lower()


def test_update_warns_on_magnitude(log_module):
    """Editing weight past 150% of best (excluding itself) warns."""
    c = log_module.conn()
    log_module.cmd_start("test")
    log_module.cmd_log("bench", 100, 5, "", "chest")
    log_module.cmd_log("bench", 90, 5, "", "chest")
    sets = c.execute("SELECT id FROM sets ORDER BY id").fetchall()
    out = json.loads(capture_stdout(log_module.cmd_update, sets[1]["id"], "weight", "200"))
    assert "warnings" in out


def test_update_workout_rejects_future_date(log_module):
    """update-workout date refuses future dates."""
    c = log_module.conn()
    log_module.cmd_start("test")
    wid = c.execute("SELECT id FROM workouts").fetchone()["id"]
    future = (date.today() + timedelta(days=1)).isoformat()
    try:
        log_module.cmd_update_workout(str(wid), "date", future)
        assert False, "should have exited"
    except SystemExit as e:
        assert "future" in str(e).lower()


def test_update_workout_rejects_second_open(log_module):
    """Only one open workout may exist at a time."""
    c = log_module.conn()
    log_module.cmd_start("first")
    cur = c.execute("INSERT INTO workouts (date, status, notes) VALUES (?, 'done', '')", (date.today().isoformat(),))
    c.commit()
    try:
        log_module.cmd_update_workout(str(cur.lastrowid), "status", "open")
        assert False, "should have exited"
    except SystemExit as e:
        assert "already open" in str(e).lower()


def test_restore_refuses_open_workout(log_module):
    """Restore aborts while a session is open; force bypasses."""
    log_module.cmd_start("test")
    try:
        log_module.cmd_restore()
        assert False, "should have exited"
    except SystemExit as e:
        assert "still open" in str(e).lower()


def test_weigh_rejects_absurd_values(log_module):
    """Bodyweight typos exit instead of polluting the chart."""
    for bad in ("842", "10"):
        try:
            log_module.cmd_weigh(bad, "")
            assert False, "should have exited"
        except SystemExit as e:
            assert "implausible" in str(e).lower()


def test_end_reports_sets_and_next(log_module):
    """End output nudges the agent toward audit, sync, commit."""
    log_module.cmd_start("test")
    log_module.cmd_log("bench", 100, 5, "", "chest")
    out = json.loads(capture_stdout(log_module.cmd_end, "done"))
    assert out["sets"] == 1
    assert "sync" in out["next"]


def test_audit_flags_steep_drop(log_module):
    """A 70% e1RM collapse flags medium without explanation."""
    c = log_module.conn()
    from datetime import timedelta as td
    base = date.today() - td(days=9)
    for offset, weight in [(0, 100), (3, 30)]:
        d = (base + td(days=offset)).isoformat()
        cur = c.execute("INSERT INTO workouts (date, status, notes) VALUES (?, 'done', '')", (d,))
        c.commit()
        wid = cur.lastrowid
        cur2 = c.execute("INSERT INTO sets (workout_id, exercise, weight, reps, note, created) VALUES (?, 'bench', ?, 5, '', datetime('now'))", (wid, weight))
        c.execute("INSERT INTO set_muscles (set_id, muscle) VALUES (?, 'chest')", (cur2.lastrowid,))
        c.commit()
    old = sys.stdout
    sys.stdout = io.StringIO()
    try:
        log_module.cmd_audit()
        out = sys.stdout.getvalue()
    finally:
        sys.stdout = old
    flags = json.loads(out.strip().splitlines()[-1])["flags"]
    drops = [f for f in flags if f["check"] == "progression_drop"]
    assert len(drops) == 1
    assert drops[0]["severity"] == "medium"
