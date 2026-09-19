#!/usr/bin/env python3
"""pytest suite for log.py - deterministic tests only."""

import json
import sys
import io
from datetime import date, timedelta


def capture_stdout(fn, *args, **kwargs):
    """Capture stdout from a function call."""
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        fn(*args, **kwargs)
        return sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout


def test_log_fails_without_open_workout(log_module):
    """log should fail cleanly when no workout is open, never auto-create."""
    c = log_module.conn()
    try:
        log_module.cmd_log("bench", 100, 5, "", "chest")
        assert False, "should have exited"
    except SystemExit as e:
        assert "no open workout" in str(e).lower()


def test_update_rejects_invalid_fields(log_module):
    """update should reject fields outside allowed set."""
    c = log_module.conn()
    log_module.cmd_start("test")
    log_module.cmd_log("bench", 100, 5, "", "chest")
    sets = c.execute("SELECT id FROM sets").fetchall()
    set_id = sets[0]["id"]
    try:
        log_module.cmd_update(set_id, "invalid_field", "value")
        assert False, "should have exited"
    except SystemExit as e:
        assert "field must be one of" in str(e).lower()


def test_muscle_cleaning_normalizes(log_module):
    """clean_muscles normalizes whitespace, case, removes duplicates."""
    assert log_module.clean_muscles(" chest , back , CHEST ") == "chest,back"
    assert log_module.clean_muscles("quads, glutes ,quads") == "quads,glutes"
    assert log_module.clean_muscles("  triceps  ") == "triceps"
    assert log_module.clean_muscles("") == ""
    assert log_module.clean_muscles("a, , b, ,") == "a,b"


def test_delete_set_returns_accurate_payload_and_removes(log_module):
    """delete-set returns was payload and actually removes row."""
    c = log_module.conn()
    log_module.cmd_start("test")
    log_module.cmd_log("bench", 100, 5, "", "chest")
    log_module.cmd_log("squat", 150, 5, "", "quads,glutes")
    sets = c.execute("SELECT * FROM sets ORDER BY id").fetchall()
    set_id = sets[0]["id"]
    output = capture_stdout(log_module.cmd_delete_set, str(set_id))
    data = json.loads(output)
    assert data["deleted"] == set_id
    assert "was" in data
    assert data["was"]["exercise"] == "bench"
    assert data["was"]["weight"] == 100
    assert data["was"]["reps"] == 5
    remaining = c.execute("SELECT COUNT(*) n FROM sets").fetchone()["n"]
    assert remaining == 1


def test_delete_workout_returns_accurate_payload_and_removes(log_module):
    """delete-workout returns was payload and removes workout + sets."""
    c = log_module.conn()
    log_module.cmd_start("test")
    log_module.cmd_log("bench", 100, 5, "", "chest")
    log_module.cmd_log("squat", 150, 5, "", "quads,glutes")
    workouts = c.execute("SELECT * FROM workouts").fetchall()
    workout_id = workouts[0]["id"]
    output = capture_stdout(log_module.cmd_delete_workout, str(workout_id))
    data = json.loads(output)
    assert data["deleted_workout"] == workout_id
    assert data["deleted_sets"] == 2
    w_count = c.execute("SELECT COUNT(*) n FROM workouts").fetchone()["n"]
    s_count = c.execute("SELECT COUNT(*) n FROM sets").fetchone()["n"]
    assert w_count == 0
    assert s_count == 0


def test_weigh_produces_correct_payload(log_module):
    """weigh produces correctly shaped payload."""
    output = capture_stdout(log_module.cmd_weigh, "84.5", "fasted")
    data = json.loads(output)
    assert "weigh_id" in data
    assert data["kg"] == 84.5
    assert data["date"].count("-") == 2


def test_update_workout_rejects_bad_status(log_module):
    """update-workout rejects invalid status values."""
    c = log_module.conn()
    log_module.cmd_start("test")
    workouts = c.execute("SELECT id FROM workouts").fetchall()
    wid = workouts[0]["id"]
    try:
        log_module.cmd_update_workout(str(wid), "status", "invalid")
        assert False, "should have exited"
    except SystemExit as e:
        assert "status must be open, done or rest" in str(e).lower()


def test_update_workout_validates_date_format(log_module):
    """update-workout validates date format."""
    c = log_module.conn()
    log_module.cmd_start("test")
    workouts = c.execute("SELECT id FROM workouts").fetchall()
    wid = workouts[0]["id"]
    try:
        log_module.cmd_update_workout(str(wid), "date", "not-a-date")
        assert False, "should have exited"
    except SystemExit:
        pass


def test_context_returns_correct_scope(log_module):
    """context returns last N workouts with correct structure."""
    c = log_module.conn()
    for i in range(5):
        log_module.cmd_start(f"workout {i}")
        log_module.cmd_log("bench", 100 + i * 5, 5, "", "chest")
        log_module.cmd_end("done")
    output = capture_stdout(log_module.cmd_context, "3")
    data = json.loads(output)
    assert len(data["recent"]) == 3
    assert "lifts" in data
    assert "workouts_total" in data
    assert "bodyweight_last" in data
    assert data["recent"][0]["workout"]["notes"] == "workout 2 done"
    assert data["recent"][2]["workout"]["notes"] == "workout 4 done"


def test_session_returns_correct_workout_ids(log_module):
    """session returns workouts for the given date with correct IDs."""
    c = log_module.conn()
    log_module.cmd_start("push day")
    log_module.cmd_log("bench", 100, 5, "", "chest")
    log_module.cmd_end("done")
    today = date.today().isoformat()
    output = capture_stdout(log_module.cmd_session, today)
    data = json.loads(output)
    assert data["date"] == today
    assert len(data["workouts"]) == 1
    assert data["workouts"][0]["workout"]["notes"] == "push day done"
    assert len(data["workouts"][0]["sets"]) == 1


def test_range_returns_correct_date_bounds(log_module):
    """range returns workouts within date bounds."""
    c = log_module.conn()
    today = date.today()
    d0 = (today - timedelta(days=10)).isoformat()
    d1 = (today - timedelta(days=5)).isoformat()
    d2 = today.isoformat()
    for d, note in [(d0, "old"), (d1, "mid"), (d2, "new")]:
        cur = c.execute("INSERT INTO workouts (date, status, notes) VALUES (?, 'done', ?)", (d, note))
        c.commit()
        wid = cur.lastrowid
        cur2 = c.execute("INSERT INTO sets (workout_id, exercise, weight, reps, note, created) VALUES (?, 'bench', 100, 5, '', datetime('now'))", (wid,))
        c.execute("INSERT INTO set_muscles (set_id, muscle) VALUES (?, 'chest')", (cur2.lastrowid,))
        c.commit()
    output = capture_stdout(log_module.cmd_range, d1, d2)
    data = json.loads(output)
    assert data["from"] == d1
    assert data["to"] == d2
    assert len(data["workouts"]) == 2
    notes = [w["workout"]["notes"] for w in data["workouts"]]
    assert "mid" in notes
    assert "new" in notes
    assert "old" not in notes


def test_update_muscles_uses_cleaning(log_module):
    """update with muscles field uses clean_muscles normalization."""
    c = log_module.conn()
    log_module.cmd_start("test")
    log_module.cmd_log("bench", 100, 5, "", "chest")
    sets = c.execute("SELECT id FROM sets").fetchall()
    set_id = sets[0]["id"]
    log_module.cmd_update(set_id, "muscles", " chest , back , CHEST ")
    updated = c.execute("SELECT muscle FROM set_muscles WHERE set_id = ? ORDER BY muscle", (set_id,)).fetchall()
    assert [r["muscle"] for r in updated] == ["back", "chest"]


def test_update_exercise_normalizes_case(log_module):
    """update with exercise field normalizes to lowercase."""
    c = log_module.conn()
    log_module.cmd_start("test")
    log_module.cmd_log("bench", 100, 5, "", "chest")
    sets = c.execute("SELECT id FROM sets").fetchall()
    set_id = sets[0]["id"]
    # Add mapping for target exercise first
    c.execute("INSERT INTO lift_muscle_map (exercise, muscles, is_bodyweight_only) VALUES (?, ?, ?)",
              ("incline bench", "chest,triceps", 0))
    c.commit()
    log_module.cmd_update(set_id, "exercise", "Incline Bench")
    updated = c.execute("SELECT exercise FROM sets WHERE id = ?", (set_id,)).fetchone()
    assert updated["exercise"] == "incline bench"


def test_rename_updates_all_matching_exercises(log_module):
    """rename updates all sets with matching exercise name."""
    c = log_module.conn()
    log_module.cmd_start("day 1")
    log_module.cmd_log("bench", 100, 5, "", "chest")
    log_module.cmd_end("done")
    log_module.cmd_start("day 2")
    log_module.cmd_log("bench", 105, 5, "", "chest")
    log_module.cmd_end("done")
    output = capture_stdout(log_module.cmd_rename, "bench", "flat bench")
    data = json.loads(output)
    assert data["renamed"] == 2
    exercises = [r["exercise"] for r in c.execute("SELECT exercise FROM sets").fetchall()]
    assert all(e == "flat bench" for e in exercises)


def test_retag_updates_all_matching_exercises(log_module):
    """retag updates muscles for all sets of an exercise."""
    c = log_module.conn()
    log_module.cmd_start("day 1")
    log_module.cmd_log("bench", 100, 5, "", "chest")
    log_module.cmd_end("done")
    log_module.cmd_start("day 2")
    log_module.cmd_log("bench", 105, 5, "", "chest")
    log_module.cmd_end("done")
    output = capture_stdout(log_module.cmd_retag, "bench", "chest,triceps")
    data = json.loads(output)
    assert data["updated"] == 2
    for r in c.execute("SELECT id FROM sets").fetchall():
        muscles = sorted(x["muscle"] for x in c.execute("SELECT muscle FROM set_muscles WHERE set_id = ?", (r["id"],)).fetchall())
        assert muscles == ["chest", "triceps"]


def test_start_reuses_open_workout(log_module):
    """start returns existing open workout instead of creating new."""
    c = log_module.conn()
    out1 = json.loads(capture_stdout(log_module.cmd_start, "first"))
    out2 = json.loads(capture_stdout(log_module.cmd_start, "second"))
    assert out1["workout_id"] == out2["workout_id"]
    assert out1["reused"] is False
    assert out2["reused"] is True


def test_log_strips_exercise_name(log_module):
    """log normalizes exercise name to lowercase stripped."""
    c = log_module.conn()
    log_module.cmd_start("test")
    log_module.cmd_log("  Incline Bench  ", 100, 5, "", "chest")
    ex = c.execute("SELECT exercise FROM sets").fetchone()["exercise"]
    assert ex == "incline bench"


def test_stats_returns_correct_shape(log_module):
    """stats returns workouts count and per-exercise aggregates."""
    c = log_module.conn()
    log_module.cmd_start("test")
    log_module.cmd_log("bench", 100, 5, "", "chest")
    log_module.cmd_log("bench", 105, 5, "", "chest")
    log_module.cmd_log("squat", 150, 5, "", "quads,glutes")
    log_module.cmd_end("done")
    output = capture_stdout(log_module.cmd_stats)
    data = json.loads(output)
    assert data["workouts"] == 1
    assert data["by_exercise"]["bench"]["sets"] == 2
    assert data["by_exercise"]["bench"]["max_weight"] == 105
    assert data["by_exercise"]["squat"]["sets"] == 1
    assert data["by_exercise"]["squat"]["max_weight"] == 150


def test_history_returns_correct_exercise_sets(log_module):
    """history returns sets for specific exercise, limited correctly."""
    c = log_module.conn()
    for i in range(10):
        log_module.cmd_start(f"w{i}")
        log_module.cmd_log("bench", 100 + i, 5, "", "chest")
        log_module.cmd_end("done")
    output = capture_stdout(log_module.cmd_history, "bench", "3")
    data = json.loads(output)
    assert len(data) == 3
    assert data[0]["weight"] == 109
    assert data[2]["weight"] == 107


def test_end_closes_workout(log_module):
    """end sets status to done and adds note."""
    c = log_module.conn()
    log_module.cmd_start("initial note")
    log_module.cmd_log("bench", 100, 5, "", "chest")
    output = capture_stdout(log_module.cmd_end, "final note")
    data = json.loads(output)
    assert "closed" in data
    w = c.execute("SELECT * FROM workouts WHERE id = ?", (data["closed"],)).fetchone()
    assert w["status"] == "done"
    assert "initial note" in w["notes"]
    assert "final note" in w["notes"]


def test_calendar_returns_gaps(log_module):
    """calendar computes gap_since_prev correctly."""
    c = log_module.conn()
    today = date.today()
    d0 = (today - timedelta(days=10)).isoformat()
    d1 = (today - timedelta(days=5)).isoformat()
    d2 = today.isoformat()
    for d in [d0, d1, d2]:
        cur = c.execute("INSERT INTO workouts (date, status, notes) VALUES (?, 'done', '')", (d,))
        c.commit()
    output = capture_stdout(log_module.cmd_calendar)
    data = json.loads(output)
    dates = [d["date"] for d in data["dates"]]
    assert len(dates) == 3
    today_entry = next(d for d in data["dates"] if d["date"] == d2)
    assert today_entry["gap_since_prev"] == 4


def test_notes_returns_only_nonempty(log_module):
    """notes only returns workouts/sets with non-empty notes."""
    c = log_module.conn()
    log_module.cmd_start("has note")
    log_module.cmd_log("bench", 100, 5, "set note", "chest")
    log_module.cmd_end("end note")
    log_module.cmd_start("")
    log_module.cmd_log("squat", 150, 5, "", "quads")
    log_module.cmd_end("")
    output = capture_stdout(log_module.cmd_notes, "10")
    data = json.loads(output)
    assert len(data["workout_notes"]) == 1
    assert data["workout_notes"][0]["notes"] == "has note end note"
    assert len(data["set_notes"]) == 1
    assert data["set_notes"][0]["note"] == "set note"


def test_export_shape(log_module):
    """export returns correctly shaped payload with all tables."""
    c = log_module.conn()
    log_module.cmd_start("test")
    log_module.cmd_log("bench", 100, 5, "", "chest")
    log_module.cmd_end("done")
    log_module.cmd_weigh("84.0", "")
    output = capture_stdout(log_module.cmd_export)
    data = json.loads(output)
    assert "exported" in data
    assert "workouts" in data
    assert "sets" in data
    assert "bodyweight" in data
    assert len(data["workouts"]) >= 1
    assert len(data["sets"]) >= 1
    assert len(data["bodyweight"]) >= 1


def test_update_weight_rejects_empty(log_module):
    """update weight rejects empty value."""
    c = log_module.conn()
    log_module.cmd_start("test")
    log_module.cmd_log("bench", 100, 5, "", "chest")
    sets = c.execute("SELECT id FROM sets").fetchall()
    set_id = sets[0]["id"]
    try:
        log_module.cmd_update(set_id, "weight", "")
        assert False, "should have exited"
    except SystemExit as e:
        assert "weight cannot be empty" in str(e).lower()


def test_update_reps_converts_to_int(log_module):
    """update reps converts string to int."""
    c = log_module.conn()
    log_module.cmd_start("test")
    log_module.cmd_log("bench", 100, 5, "", "chest")
    sets = c.execute("SELECT id FROM sets").fetchall()
    set_id = sets[0]["id"]
    log_module.cmd_update(set_id, "reps", "8")
    updated = c.execute("SELECT reps FROM sets WHERE id = ?", (set_id,)).fetchone()
    assert updated["reps"] == 8


def test_today_returns_open_false_when_none(log_module):
    """today returns open: false when no workout open."""
    output = capture_stdout(log_module.cmd_today)
    data = json.loads(output)
    assert data["open"] is False


def test_log_bw_flag_bootstraps_bodyweight_exercise(log_module):
    """log with bw flag allows zero weight on a brand new exercise."""
    c = log_module.conn()
    log_module.cmd_start("test")
    log_module.cmd_log("pullup", 0, 8, "", "back,biceps", True)
    mapping = c.execute("SELECT is_bodyweight_only FROM lift_muscle_map WHERE exercise = 'pullup'").fetchone()
    assert mapping["is_bodyweight_only"] == 1


def test_log_zero_weight_rejected_without_bw_flag(log_module):
    """zero weight on a mapped non bodyweight lift fails even with muscles given."""
    c = log_module.conn()
    log_module.cmd_start("test")
    log_module.cmd_log("bench", 100, 5, "", "chest")
    try:
        log_module.cmd_log("bench", 0, 5, "", "chest")
        assert False, "should have exited"
    except SystemExit as e:
        assert "zero weight not allowed" in str(e).lower()


def test_log_rejects_negative_weight_and_bad_reps(log_module):
    """negative weight and non positive reps never reach the db."""
    c = log_module.conn()
    log_module.cmd_start("test")
    for w, r in [(-5, 5), (100, 0), (100, -3)]:
        try:
            log_module.cmd_log("bench", w, r, "", "chest")
            assert False, "should have exited"
        except SystemExit:
            pass
    assert c.execute("SELECT COUNT(*) n FROM sets").fetchone()["n"] == 0


def test_rename_moves_muscle_mapping(log_module):
    """rename moves the lift_muscle_map entry so the new name stays mapped."""
    c = log_module.conn()
    log_module.cmd_start("test")
    log_module.cmd_log("bench", 100, 5, "", "chest")
    log_module.cmd_end("done")
    output = capture_stdout(log_module.cmd_rename, "bench", "flat bench")
    data = json.loads(output)
    assert data["renamed"] == 1
    assert data["map_moved"] is True
    assert c.execute("SELECT COUNT(*) n FROM lift_muscle_map WHERE exercise = 'bench'").fetchone()["n"] == 0
    row = c.execute("SELECT muscles FROM lift_muscle_map WHERE exercise = 'flat bench'").fetchone()
    assert row["muscles"] == "chest"


def test_context_reports_max_e1rm(log_module):
    """context lifts report max e1RM, not just max top weight."""
    c = log_module.conn()
    log_module.cmd_start("test")
    log_module.cmd_log("bench", 100, 10, "", "chest")
    log_module.cmd_log("bench", 105, 1, "", "chest")
    log_module.cmd_end("done")
    output = capture_stdout(log_module.cmd_context, "3")
    data = json.loads(output)
    bench = next(x for x in data["lifts"] if x["exercise"] == "bench")
    assert bench["max_e1rm"] == round(100 * (1 + 10 / 30.0), 1)
    assert bench["max_weight"] == 100
