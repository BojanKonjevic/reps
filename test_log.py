#!/usr/bin/env python3
"""pytest suite for log.py - deterministic tests only."""

import json
import os
import sys
import tempfile
import io
from datetime import date, timedelta
from importlib import reload

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))


def reload_log_module():
    """Reload log module to pick up new REPS_DB."""
    import log
    reload(log)
    return log


def get_funcs():
    log = reload_log_module()
    return log


def setup_tmp_db():
    """Create a temp DB and return its path."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.environ["REPS_DB"] = path
    reload_log_module()
    return path


def teardown_tmp_db(path):
    """Clean up temp DB."""
    try:
        os.unlink(path)
    except OSError:
        pass


def capture_stdout(fn, *args, **kwargs):
    """Capture stdout from a function call."""
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        fn(*args, **kwargs)
        return sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout


def test_log_fails_without_open_workout():
    """log should fail cleanly when no workout is open, never auto-create."""
    path = setup_tmp_db()
    try:
        log = get_funcs()
        c = log.conn()
        try:
            log.cmd_log("bench", 100, 5, "", "chest")
            assert False, "should have exited"
        except SystemExit as e:
            assert "no open workout" in str(e).lower()
    finally:
        teardown_tmp_db(path)


def test_update_rejects_invalid_fields():
    """update should reject fields outside allowed set."""
    path = setup_tmp_db()
    try:
        log = get_funcs()
        c = log.conn()
        log.cmd_start("test")
        log.cmd_log("bench", 100, 5, "", "chest")
        sets = c.execute("SELECT id FROM sets").fetchall()
        set_id = sets[0]["id"]
        try:
            log.cmd_update(set_id, "invalid_field", "value")
            assert False, "should have exited"
        except SystemExit as e:
            assert "field must be one of" in str(e).lower()
    finally:
        teardown_tmp_db(path)


def test_muscle_cleaning_normalizes():
    """clean_muscles normalizes whitespace, case, removes duplicates."""
    log = get_funcs()
    assert log.clean_muscles(" chest , back , CHEST ") == "chest,back"
    assert log.clean_muscles("quads, glutes ,quads") == "quads,glutes"
    assert log.clean_muscles("  triceps  ") == "triceps"
    assert log.clean_muscles("") == ""
    assert log.clean_muscles("a, , b, ,") == "a,b"


def test_delete_set_returns_accurate_payload_and_removes():
    """delete-set returns was payload and actually removes row."""
    path = setup_tmp_db()
    try:
        log = get_funcs()
        c = log.conn()
        log.cmd_start("test")
        log.cmd_log("bench", 100, 5, "", "chest")
        log.cmd_log("squat", 150, 5, "", "quads,glutes")
        sets = c.execute("SELECT * FROM sets ORDER BY id").fetchall()
        set_id = sets[0]["id"]
        output = capture_stdout(log.cmd_delete_set, str(set_id))
        data = json.loads(output)
        assert data["deleted"] == set_id
        assert "was" in data
        assert data["was"]["exercise"] == "bench"
        assert data["was"]["weight"] == 100
        assert data["was"]["reps"] == 5
        remaining = c.execute("SELECT COUNT(*) n FROM sets").fetchone()["n"]
        assert remaining == 1
    finally:
        teardown_tmp_db(path)


def test_delete_workout_returns_accurate_payload_and_removes():
    """delete-workout returns was payload and removes workout + sets."""
    path = setup_tmp_db()
    try:
        log = get_funcs()
        c = log.conn()
        log.cmd_start("test")
        log.cmd_log("bench", 100, 5, "", "chest")
        log.cmd_log("squat", 150, 5, "", "quads,glutes")
        workouts = c.execute("SELECT * FROM workouts").fetchall()
        workout_id = workouts[0]["id"]
        output = capture_stdout(log.cmd_delete_workout, str(workout_id))
        data = json.loads(output)
        assert data["deleted_workout"] == workout_id
        assert data["deleted_sets"] == 2
        w_count = c.execute("SELECT COUNT(*) n FROM workouts").fetchone()["n"]
        s_count = c.execute("SELECT COUNT(*) n FROM sets").fetchone()["n"]
        assert w_count == 0
        assert s_count == 0
    finally:
        teardown_tmp_db(path)


def test_weigh_produces_correct_payload():
    """weigh produces correctly shaped payload."""
    path = setup_tmp_db()
    try:
        log = get_funcs()
        output = capture_stdout(log.cmd_weigh, "84.5", "fasted")
        data = json.loads(output)
        assert "weigh_id" in data
        assert data["kg"] == 84.5
        assert data["date"].count("-") == 2
    finally:
        teardown_tmp_db(path)


def test_update_workout_rejects_bad_status():
    """update-workout rejects invalid status values."""
    path = setup_tmp_db()
    try:
        log = get_funcs()
        c = log.conn()
        log.cmd_start("test")
        workouts = c.execute("SELECT id FROM workouts").fetchall()
        wid = workouts[0]["id"]
        try:
            log.cmd_update_workout(str(wid), "status", "invalid")
            assert False, "should have exited"
        except SystemExit as e:
            assert "status must be open or done" in str(e).lower()
    finally:
        teardown_tmp_db(path)


def test_update_workout_validates_date_format():
    """update-workout validates date format."""
    path = setup_tmp_db()
    try:
        log = get_funcs()
        c = log.conn()
        log.cmd_start("test")
        workouts = c.execute("SELECT id FROM workouts").fetchall()
        wid = workouts[0]["id"]
        try:
            log.cmd_update_workout(str(wid), "date", "not-a-date")
            assert False, "should have exited"
        except SystemExit:
            pass
    finally:
        teardown_tmp_db(path)


def test_context_returns_correct_scope():
    """context returns last N workouts with correct structure."""
    path = setup_tmp_db()
    try:
        log = get_funcs()
        c = log.conn()
        for i in range(5):
            log.cmd_start(f"workout {i}")
            log.cmd_log("bench", 100 + i * 5, 5, "", "chest")
            log.cmd_end("done")
        output = capture_stdout(log.cmd_context, "3")
        data = json.loads(output)
        assert len(data["recent"]) == 3
        assert "lifts" in data
        assert "workouts_total" in data
        assert "bodyweight_last" in data
        assert data["recent"][0]["workout"]["notes"] == "workout 2 done"
        assert data["recent"][2]["workout"]["notes"] == "workout 4 done"
    finally:
        teardown_tmp_db(path)


def test_session_returns_correct_workout_ids():
    """session returns workouts for the given date with correct IDs."""
    path = setup_tmp_db()
    try:
        log = get_funcs()
        c = log.conn()
        log.cmd_start("push day")
        log.cmd_log("bench", 100, 5, "", "chest")
        log.cmd_end("done")
        today = date.today().isoformat()
        output = capture_stdout(log.cmd_session, today)
        data = json.loads(output)
        assert data["date"] == today
        assert len(data["workouts"]) == 1
        assert data["workouts"][0]["workout"]["notes"] == "push day done"
        assert len(data["workouts"][0]["sets"]) == 1
    finally:
        teardown_tmp_db(path)


def test_range_returns_correct_date_bounds():
    """range returns workouts within date bounds."""
    path = setup_tmp_db()
    try:
        log = get_funcs()
        c = log.conn()
        today = date.today()
        d0 = (today - timedelta(days=10)).isoformat()
        d1 = (today - timedelta(days=5)).isoformat()
        d2 = today.isoformat()
        for d, note in [(d0, "old"), (d1, "mid"), (d2, "new")]:
            cur = c.execute("INSERT INTO workouts (date, status, notes) VALUES (?, 'done', ?)", (d, note))
            c.commit()
            wid = cur.lastrowid
            c.execute("INSERT INTO sets (workout_id, exercise, weight, reps, note, created, muscles) VALUES (?, 'bench', 100, 5, '', datetime('now'), 'chest')", (wid,))
            c.commit()
        output = capture_stdout(log.cmd_range, d1, d2)
        data = json.loads(output)
        assert data["from"] == d1
        assert data["to"] == d2
        assert len(data["workouts"]) == 2
        notes = [w["workout"]["notes"] for w in data["workouts"]]
        assert "mid" in notes
        assert "new" in notes
        assert "old" not in notes
    finally:
        teardown_tmp_db(path)


def test_update_muscles_uses_cleaning():
    """update with muscles field uses clean_muscles normalization."""
    path = setup_tmp_db()
    try:
        log = get_funcs()
        c = log.conn()
        log.cmd_start("test")
        log.cmd_log("bench", 100, 5, "", "chest")
        sets = c.execute("SELECT id FROM sets").fetchall()
        set_id = sets[0]["id"]
        log.cmd_update(set_id, "muscles", " chest , back , CHEST ")
        updated = c.execute("SELECT muscles FROM sets WHERE id = ?", (set_id,)).fetchone()
        assert updated["muscles"] == "chest,back"
    finally:
        teardown_tmp_db(path)


def test_update_exercise_normalizes_case():
    """update with exercise field normalizes to lowercase."""
    path = setup_tmp_db()
    try:
        log = get_funcs()
        c = log.conn()
        log.cmd_start("test")
        log.cmd_log("bench", 100, 5, "", "chest")
        sets = c.execute("SELECT id FROM sets").fetchall()
        set_id = sets[0]["id"]
        log.cmd_update(set_id, "exercise", "Incline Bench")
        updated = c.execute("SELECT exercise FROM sets WHERE id = ?", (set_id,)).fetchone()
        assert updated["exercise"] == "incline bench"
    finally:
        teardown_tmp_db(path)


def test_rename_updates_all_matching_exercises():
    """rename updates all sets with matching exercise name."""
    path = setup_tmp_db()
    try:
        log = get_funcs()
        c = log.conn()
        log.cmd_start("day 1")
        log.cmd_log("bench", 100, 5, "", "chest")
        log.cmd_end("done")
        log.cmd_start("day 2")
        log.cmd_log("bench", 105, 5, "", "chest")
        log.cmd_end("done")
        output = capture_stdout(log.cmd_rename, "bench", "flat bench")
        data = json.loads(output)
        assert data["renamed"] == 2
        exercises = [r["exercise"] for r in c.execute("SELECT exercise FROM sets").fetchall()]
        assert all(e == "flat bench" for e in exercises)
    finally:
        teardown_tmp_db(path)


def test_retag_updates_all_matching_exercises():
    """retag updates muscles for all sets of an exercise."""
    path = setup_tmp_db()
    try:
        log = get_funcs()
        c = log.conn()
        log.cmd_start("day 1")
        log.cmd_log("bench", 100, 5, "", "chest")
        log.cmd_end("done")
        log.cmd_start("day 2")
        log.cmd_log("bench", 105, 5, "", "chest")
        log.cmd_end("done")
        output = capture_stdout(log.cmd_retag, "bench", "chest,triceps")
        data = json.loads(output)
        assert data["updated"] == 2
        muscles = [r["muscles"] for r in c.execute("SELECT muscles FROM sets").fetchall()]
        assert all(m == "chest,triceps" for m in muscles)
    finally:
        teardown_tmp_db(path)


def test_start_reuses_open_workout():
    """start returns existing open workout instead of creating new."""
    path = setup_tmp_db()
    try:
        log = get_funcs()
        c = log.conn()
        out1 = json.loads(capture_stdout(log.cmd_start, "first"))
        out2 = json.loads(capture_stdout(log.cmd_start, "second"))
        assert out1["workout_id"] == out2["workout_id"]
        assert out1["reused"] is False
        assert out2["reused"] is True
    finally:
        teardown_tmp_db(path)


def test_log_strips_exercise_name():
    """log normalizes exercise name to lowercase stripped."""
    path = setup_tmp_db()
    try:
        log = get_funcs()
        c = log.conn()
        log.cmd_start("test")
        log.cmd_log("  Incline Bench  ", 100, 5, "", "chest")
        ex = c.execute("SELECT exercise FROM sets").fetchone()["exercise"]
        assert ex == "incline bench"
    finally:
        teardown_tmp_db(path)


def test_stats_returns_correct_shape():
    """stats returns workouts count and per-exercise aggregates."""
    path = setup_tmp_db()
    try:
        log = get_funcs()
        c = log.conn()
        log.cmd_start("test")
        log.cmd_log("bench", 100, 5, "", "chest")
        log.cmd_log("bench", 105, 5, "", "chest")
        log.cmd_log("squat", 150, 5, "", "quads,glutes")
        log.cmd_end("done")
        output = capture_stdout(log.cmd_stats)
        data = json.loads(output)
        assert data["workouts"] == 1
        assert data["by_exercise"]["bench"]["sets"] == 2
        assert data["by_exercise"]["bench"]["max_weight"] == 105
        assert data["by_exercise"]["squat"]["sets"] == 1
        assert data["by_exercise"]["squat"]["max_weight"] == 150
    finally:
        teardown_tmp_db(path)


def test_history_returns_correct_exercise_sets():
    """history returns sets for specific exercise, limited correctly."""
    path = setup_tmp_db()
    try:
        log = get_funcs()
        c = log.conn()
        for i in range(10):
            log.cmd_start(f"w{i}")
            log.cmd_log("bench", 100 + i, 5, "", "chest")
            log.cmd_end("done")
        output = capture_stdout(log.cmd_history, "bench", "3")
        data = json.loads(output)
        assert len(data) == 3
        assert data[0]["weight"] == 109
        assert data[2]["weight"] == 107
    finally:
        teardown_tmp_db(path)


def test_end_closes_workout():
    """end sets status to done and adds note."""
    path = setup_tmp_db()
    try:
        log = get_funcs()
        c = log.conn()
        log.cmd_start("initial note")
        log.cmd_log("bench", 100, 5, "", "chest")
        output = capture_stdout(log.cmd_end, "final note")
        data = json.loads(output)
        assert "closed" in data
        w = c.execute("SELECT * FROM workouts WHERE id = ?", (data["closed"],)).fetchone()
        assert w["status"] == "done"
        assert "initial note" in w["notes"]
        assert "final note" in w["notes"]
    finally:
        teardown_tmp_db(path)


def test_calendar_returns_gaps():
    """calendar computes gap_since_prev correctly."""
    path = setup_tmp_db()
    try:
        log = get_funcs()
        c = log.conn()
        today = date.today()
        d0 = (today - timedelta(days=10)).isoformat()
        d1 = (today - timedelta(days=5)).isoformat()
        d2 = today.isoformat()
        for d in [d0, d1, d2]:
            cur = c.execute("INSERT INTO workouts (date, status, notes) VALUES (?, 'done', '')", (d,))
            c.commit()
        output = capture_stdout(log.cmd_calendar)
        data = json.loads(output)
        dates = [d["date"] for d in data["dates"]]
        assert len(dates) == 3
        today_entry = next(d for d in data["dates"] if d["date"] == d2)
        assert today_entry["gap_since_prev"] == 4
    finally:
        teardown_tmp_db(path)


def test_notes_returns_only_nonempty():
    """notes only returns workouts/sets with non-empty notes."""
    path = setup_tmp_db()
    try:
        log = get_funcs()
        c = log.conn()
        log.cmd_start("has note")
        log.cmd_log("bench", 100, 5, "set note", "chest")
        log.cmd_end("end note")
        log.cmd_start("")
        log.cmd_log("squat", 150, 5, "", "quads")
        log.cmd_end("")
        output = capture_stdout(log.cmd_notes, "10")
        data = json.loads(output)
        assert len(data["workout_notes"]) == 1
        assert data["workout_notes"][0]["notes"] == "has note end note"
        assert len(data["set_notes"]) == 1
        assert data["set_notes"][0]["note"] == "set note"
    finally:
        teardown_tmp_db(path)


def test_export_shape():
    """export returns correctly shaped payload with all tables."""
    path = setup_tmp_db()
    try:
        log = get_funcs()
        c = log.conn()
        log.cmd_start("test")
        log.cmd_log("bench", 100, 5, "", "chest")
        log.cmd_end("done")
        log.cmd_weigh("84.0", "")
        output = capture_stdout(log.cmd_export)
        data = json.loads(output)
        assert "exported" in data
        assert "workouts" in data
        assert "sets" in data
        assert "bodyweight" in data
        assert len(data["workouts"]) >= 1
        assert len(data["sets"]) >= 1
        assert len(data["bodyweight"]) >= 1
    finally:
        teardown_tmp_db(path)


def test_update_weight_rejects_empty():
    """update weight rejects empty value."""
    path = setup_tmp_db()
    try:
        log = get_funcs()
        c = log.conn()
        log.cmd_start("test")
        log.cmd_log("bench", 100, 5, "", "chest")
        sets = c.execute("SELECT id FROM sets").fetchall()
        set_id = sets[0]["id"]
        try:
            log.cmd_update(set_id, "weight", "")
            assert False, "should have exited"
        except SystemExit as e:
            assert "weight cannot be empty" in str(e).lower()
    finally:
        teardown_tmp_db(path)


def test_update_reps_converts_to_int():
    """update reps converts string to int."""
    path = setup_tmp_db()
    try:
        log = get_funcs()
        c = log.conn()
        log.cmd_start("test")
        log.cmd_log("bench", 100, 5, "", "chest")
        sets = c.execute("SELECT id FROM sets").fetchall()
        set_id = sets[0]["id"]
        log.cmd_update(set_id, "reps", "8")
        updated = c.execute("SELECT reps FROM sets WHERE id = ?", (set_id,)).fetchone()
        assert updated["reps"] == 8
    finally:
        teardown_tmp_db(path)


def test_today_returns_open_false_when_none():
    """today returns open: false when no workout open."""
    path = setup_tmp_db()
    try:
        log = get_funcs()
        output = capture_stdout(log.cmd_today)
        data = json.loads(output)
        assert data["open"] is False
    finally:
        teardown_tmp_db(path)


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))