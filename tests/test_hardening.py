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


def _dump_sql_for_db(db_path):
    import sqlite3
    c = sqlite3.connect(db_path)
    sql_path = __import__("os").path.join(__import__("os").path.dirname(db_path), "workouts.sql")
    with open(sql_path, "w") as f:
        for line in c.iterdump():
            f.write(line + "\n")
    c.close()
    return sql_path


def test_restore_poisoned_dump_leaves_live_db_untouched(log_module, tmp_db):
    """A malformed dump exits cleanly with all tables and rows intact."""
    c = log_module.conn()
    log_module.cmd_start("test")
    log_module.cmd_log("bench", 100, 5, "", "chest")
    log_module.cmd_end("done")
    sql_path = _dump_sql_for_db(tmp_db)
    with open(sql_path) as f:
        lines = f.read().split("\n")
    lines.insert(5, "THIS IS NOT SQL AT ALL;")
    with open(sql_path, "w") as f:
        f.write("\n".join(lines))
    try:
        log_module.cmd_restore()
        assert False, "should have exited"
    except SystemExit as e:
        assert "live DB untouched" in str(e)
    tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    assert "sets" in tables and "workouts" in tables
    assert c.execute("SELECT COUNT(*) n FROM sets").fetchone()["n"] == 1


def test_restore_success_path(log_module, tmp_db):
    """A valid dump restores lost rows."""
    c = log_module.conn()
    log_module.cmd_start("test")
    log_module.cmd_log("bench", 100, 5, "", "chest")
    log_module.cmd_end("done")
    sql_path = _dump_sql_for_db(tmp_db)
    c.execute("DELETE FROM sets")
    c.execute("DELETE FROM workouts")
    c.commit()
    assert c.execute("SELECT COUNT(*) n FROM sets").fetchone()["n"] == 0
    log_module.cmd_restore()
    c2 = log_module.conn()
    assert c2.execute("SELECT COUNT(*) n FROM sets").fetchone()["n"] == 1


def test_rename_refuses_conflicting_mapping(log_module):
    """Merging into a differently-mapped name refuses instead of overwriting."""
    c = log_module.conn()
    log_module.cmd_start("test")
    log_module.cmd_log("bp", 50, 8, "", "chest,triceps")
    log_module.cmd_log("press", 60, 8, "", "chest,front delt")
    log_module.cmd_end("done")
    try:
        log_module.cmd_rename("bp", "press")
        assert False, "should have exited"
    except SystemExit as e:
        assert "already maps to" in str(e)
    row = c.execute("SELECT muscles FROM lift_muscle_map WHERE exercise = 'press'").fetchone()
    assert row["muscles"] == "chest,front delt"
    assert c.execute("SELECT COUNT(*) n FROM sets WHERE exercise = 'bp'").fetchone()["n"] == 1


def test_rename_refuses_identical_names(log_module):
    """Renaming onto itself exits instead of deleting the mapping."""
    c = log_module.conn()
    log_module.cmd_start("test")
    log_module.cmd_log("bench", 100, 5, "", "chest")
    log_module.cmd_end("done")
    try:
        log_module.cmd_rename("bench", "bench")
        assert False, "should have exited"
    except SystemExit as e:
        assert "identical" in str(e).lower()
    assert c.execute("SELECT COUNT(*) n FROM lift_muscle_map WHERE exercise = 'bench'").fetchone()["n"] == 1


def test_rename_same_mapping_merges(log_module):
    """Same muscles on both sides still merges cleanly."""
    c = log_module.conn()
    log_module.cmd_start("test")
    log_module.cmd_log("bp", 50, 8, "", "chest")
    log_module.cmd_log("bench", 100, 5, "", "chest")
    log_module.cmd_end("done")
    out = json.loads(capture_stdout(log_module.cmd_rename, "bp", "bench"))
    assert out["renamed"] == 1
    assert out["map_moved"] is True


def test_update_rejects_empty_muscles(log_module):
    """Empty muscles on update exits, junction rows untouched."""
    c = log_module.conn()
    log_module.cmd_start("test")
    log_module.cmd_log("bench", 100, 5, "", "chest")
    set_id = c.execute("SELECT id FROM sets").fetchone()["id"]
    try:
        log_module.cmd_update(set_id, "muscles", "   ")
        assert False, "should have exited"
    except SystemExit as e:
        assert "cannot be empty" in str(e).lower()
    assert [r["muscle"] for r in c.execute("SELECT muscle FROM set_muscles").fetchall()] == ["chest"]


def test_retag_rejects_empty_muscles(log_module):
    """Empty muscles on retag exits, mapping untouched."""
    c = log_module.conn()
    log_module.cmd_start("test")
    log_module.cmd_log("bench", 100, 5, "", "chest")
    log_module.cmd_end("done")
    try:
        log_module.cmd_retag("bench", " , ")
        assert False, "should have exited"
    except SystemExit as e:
        assert "cannot be empty" in str(e).lower()
    row = c.execute("SELECT muscles FROM lift_muscle_map WHERE exercise = 'bench'").fetchone()
    assert row["muscles"] == "chest"


def test_bad_numeric_inputs_exit_cleanly(log_module):
    """Every numeric/date conversion exits with a message, never a traceback."""
    c = log_module.conn()
    log_module.cmd_start("test")
    log_module.cmd_log("bench", 100, 5, "", "chest")
    set_id = c.execute("SELECT id FROM sets").fetchone()["id"]
    wid = c.execute("SELECT id FROM workouts").fetchone()["id"]
    cases = [
        (log_module.cmd_log, ("bench", "abc", 5, "", "chest"), "must be a number"),
        (log_module.cmd_weigh, ("abc", ""), "must be a number"),
        (log_module.cmd_history, ("bench", "abc"), "integer"),
        (log_module.cmd_session, ("not-a-date",), "YYYY-MM-DD"),
        (log_module.cmd_range, ("not-a-date", "2026-01-01"), "YYYY-MM-DD"),
        (log_module.cmd_update, (set_id, "weight", "abc"), "must be a number"),
        (log_module.cmd_update, (set_id, "reps", "abc"), "integer"),
        (log_module.cmd_delete_set, ("abc",), "no such set"),
        (log_module.cmd_delete_workout, ("abc",), "no such workout"),
        (log_module.cmd_update_workout, ("abc", "notes", "x"), "no such workout"),
    ]
    for fn, args, needle in cases:
        try:
            fn(*args)
            assert False, f"should have exited: {fn.__name__}{args}"
        except SystemExit as e:
            assert needle in str(e), f"{fn.__name__}: {e}"


def test_restore_truncated_valid_dump_refused(log_module, tmp_db):
    """A syntactically valid but incomplete dump exits with the live DB intact."""
    import sqlite3
    c = log_module.conn()
    log_module.cmd_start("test")
    log_module.cmd_log("bench", 100, 5, "", "chest")
    log_module.cmd_end("done")
    db_path = tmp_db
    con = sqlite3.connect(db_path)
    schema = con.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='bodyweight'").fetchone()[0]
    con.close()
    sql_path = __import__("os").path.join(__import__("os").path.dirname(db_path), "workouts.sql")
    with open(sql_path, "w") as f:
        f.write(schema + ";\n")
    try:
        log_module.cmd_restore()
        assert False, "should have exited"
    except SystemExit as e:
        assert "missing tables" in str(e)
    c2 = log_module.conn()
    tables = {r[0] for r in c2.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert tables == {"workouts", "sets", "set_muscles", "bodyweight", "lift_muscle_map"}
    assert c2.execute("SELECT COUNT(*) n FROM sets").fetchone()["n"] == 1


def test_rename_same_muscles_different_order_merges(log_module):
    """Reordered-but-identical muscle sets are not a conflict."""
    c = log_module.conn()
    log_module.cmd_start("test")
    log_module.cmd_log("bp", 50, 8, "", "triceps,chest")
    log_module.cmd_log("bench", 60, 8, "", "chest,triceps")
    log_module.cmd_end("done")
    out = json.loads(capture_stdout(log_module.cmd_rename, "bp", "bench"))
    assert out["renamed"] == 1
    assert out["map_moved"] is True
    assert c.execute("SELECT COUNT(*) n FROM sets WHERE exercise = 'bench'").fetchone()["n"] == 2
