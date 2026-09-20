#!/usr/bin/env python3
"""Phase 2: the end gate enforces session writeback at close time."""

import datetime as _dt
import io
import json
import sys
from contextlib import redirect_stdout

import pytest


def _run(fn, *args):
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            fn(*args)
    except SystemExit as e:
        return buf.getvalue(), e.code
    return buf.getvalue(), 0


def _seed_session(log):
    log.cmd_start("test")
    log.cmd_log("bench", 100, 5, "", "chest")
    log.cmd_log("squat", 150, 5, "", "quads,glutes")
    w = log.open_workout(log.conn())
    return w["id"]


def test_end_blocked_without_progression(log_module):
    log = log_module
    _seed_session(log)
    out, code = _run(log.cmd_end, "")
    assert code == 1
    assert "missing progression: bench" in out
    assert "missing progression: squat" in out
    assert "progression set" in out
    assert log.open_workout(log.conn()) is not None


def test_check_dry_run_matches_end(log_module):
    log = log_module
    _seed_session(log)
    out, code = _run(log.cmd_check)
    assert code == 1
    assert "not ready to close" in out


def test_end_succeeds_after_progression(log_module):
    log = log_module
    _seed_session(log)
    log.cmd_progression_set("bench", "hit", "102.5x5", "up")
    log.cmd_progression_set("squat", "hold", "150x5", "flat")
    out, code = _run(log.cmd_check)
    assert code == 0
    assert json.loads(out)["ready"]
    out, code = _run(log.cmd_end, "good session")
    assert code == 0
    assert json.loads(out)["sets"] == 2
    assert log.open_workout(log.conn()) is None


def test_end_blocked_on_muscleless_set(log_module):
    log = log_module
    log.cmd_start("test")
    c = log.conn()
    wid = log.open_workout(c)["id"]
    c.execute("INSERT INTO sets (workout_id, exercise, weight, reps, note, created) VALUES (?, 'bench', 100, 5, '', datetime('now'))", (wid,))
    c.commit()
    out, code = _run(log.cmd_end, "")
    assert code == 1
    assert "has no muscles" in out


def test_end_force_records_reason(log_module):
    log = log_module
    _seed_session(log)
    out, code = _run(log.cmd_end, "", "short session, skipping writeback")
    assert code == 0
    assert json.loads(out)["forced"] == "short session, skipping writeback"
    row = log.conn().execute("SELECT notes FROM workouts WHERE status = 'done'").fetchone()
    assert "forced: short session" in row["notes"]


def test_end_requires_deload_note(log_module):
    log = log_module
    _seed_session(log)
    log.cmd_deload_set("lift", "bench")
    log.cmd_progression_set("bench", "hold", "100x5", "flat")
    log.cmd_progression_set("squat", "hold", "150x5", "flat")
    out, code = _run(log.cmd_end, "easy day")
    assert code == 1
    assert "deload" in out
    out, code = _run(log.cmd_end, "easy deload day")
    assert code == 0


def test_progression_rejects_unknown_exercise(log_module):
    log = log_module
    _seed_session(log)
    with pytest.raises(SystemExit, match="no sets in workout"):
        log.cmd_progression_set("deadlift", "hit", "180x5", "up")


def test_deload_clear_appends_state_line(log_module, tmp_path, monkeypatch):
    log = log_module
    p = tmp_path / "MEMORY.md"
    p.write_text("# memory\n\n## State\n\n- old line\n\n## Other\n")
    monkeypatch.setattr(log, "MEMORY_FILE", str(p))
    log.cmd_deload_set("lift", "bench")
    log.cmd_deload_clear()
    text = p.read_text()
    assert "deload completed for lift bench" in text
    assert "- old line" in text


def test_plan_consumes_flags(log_module):
    log = log_module
    log.cmd_flag_add("bench", "watch this")
    buf = io.StringIO()
    with redirect_stdout(buf):
        log.cmd_plan()
    bundle = json.loads(buf.getvalue())
    assert [f["subject"] for f in bundle["flags"]] == ["bench"]
    buf = io.StringIO()
    with redirect_stdout(buf):
        log.cmd_plan()
    assert json.loads(buf.getvalue())["flags"] == []


def test_plan_consumes_only_day_relevant_flags(log_module):
    from datetime import timedelta
    log = log_module
    c = log.conn()
    d = (_dt.date.today() - timedelta(days=1)).isoformat()
    cur = c.execute("INSERT INTO workouts (date, status, notes) VALUES (?, 'done', '')", (d,))
    c.commit()
    for ex in ["incline barbell bench press", "hammer strength row", "pec deck"]:
        cur2 = c.execute(
            "INSERT INTO sets (workout_id, exercise, weight, reps, note, created) VALUES (?, ?, 80, 6, '', datetime('now'))",
            (cur.lastrowid, ex))
        c.execute("INSERT INTO set_muscles (set_id, muscle) VALUES (?, 'chest')", (cur2.lastrowid,))
    c.commit()
    log.cmd_flag_add("hack squat", "watch depth")
    log.cmd_flag_add("incline barbell bench press", "old news")
    buf = io.StringIO()
    with redirect_stdout(buf):
        log.cmd_plan()
    bundle = json.loads(buf.getvalue())
    assert bundle["slot_guess"]["day"] == "Lower A"
    assert {f["subject"] for f in bundle["flags"]} == {"hack squat", "incline barbell bench press"}
    buf = io.StringIO()
    with redirect_stdout(buf):
        log.cmd_plan()
    assert [f["subject"] for f in json.loads(buf.getvalue())["flags"]] == ["incline barbell bench press"]


def test_read_commands_roundtrip(log_module):
    log = log_module
    _seed_session(log)
    log.cmd_progression_set("bench", "hit", "102.5x5", "up")
    buf = io.StringIO()
    with redirect_stdout(buf):
        log.cmd_progression_show("bench")
    assert json.loads(buf.getvalue())[0]["next_target"] == "102.5x5"
    buf = io.StringIO()
    with redirect_stdout(buf):
        log.cmd_progression_show()
    assert [r["exercise"] for r in json.loads(buf.getvalue())] == ["bench"]
    log.cmd_flag_add("bench", "watch this")
    buf = io.StringIO()
    with redirect_stdout(buf):
        log.cmd_flag_list()
    assert json.loads(buf.getvalue())[0]["reason"] == "watch this"
    log.cmd_priority_set("chest", "priority", None)
    buf = io.StringIO()
    with redirect_stdout(buf):
        log.cmd_priority_list()
    assert json.loads(buf.getvalue())[0]["tier"] == "priority"
    log.cmd_priority_clear("chest")
    buf = io.StringIO()
    with redirect_stdout(buf):
        log.cmd_priority_list()
    assert json.loads(buf.getvalue()) == []


def test_deload_set_idempotent(log_module):
    log = log_module
    buf = io.StringIO()
    with redirect_stdout(buf):
        log.cmd_deload_set("lift", "bench")
    first = json.loads(buf.getvalue())
    buf = io.StringIO()
    with redirect_stdout(buf):
        log.cmd_deload_set("lift", "bench")
    second = json.loads(buf.getvalue())
    assert second["deload_id"] == first["deload_id"]
    assert second["reused"] is True
    assert len(log.active_deloads(log.conn())) == 1


def test_check_accepts_prospective_note(log_module):
    log = log_module
    _seed_session(log)
    log.cmd_deload_set("lift", "bench")
    log.cmd_progression_set("bench", "hold", "100x5", "flat")
    log.cmd_progression_set("squat", "hold", "150x5", "flat")
    _, code = _run(log.cmd_check, "")
    assert code == 1
    out, code = _run(log.cmd_check, "easy deload day")
    assert code == 0
    assert json.loads(out)["ready"]


def test_plan_surfaces_priority_and_deload(log_module):
    log = log_module
    log.cmd_priority_set("chest", "priority", None)
    log.cmd_deload_set("slot", "Upper A")
    buf = io.StringIO()
    with redirect_stdout(buf):
        log.cmd_plan()
    bundle = json.loads(buf.getvalue())
    assert bundle["priority"]["chest"]["tier"] == "priority"
    assert bundle["deload"][0] == {"id": 1, "scope": "slot", "subject": "upper a",
                                  "set_on": _dt.date.today().isoformat(), "cleared_on": None}


def test_restore_accepts_new_tables(log_module, tmp_path, monkeypatch):
    """cmd_restore's expected set derives from SCHEMA, so new tables pass."""
    log = log_module
    _seed_session(log)
    log.cmd_progression_set("bench", "baseline", "100x5", "flat")
    live = str(tmp_path / "live.db")
    monkeypatch.setattr(log, "DB", live)
    with open(tmp_path / "workouts.sql", "w") as f:
        for line in log.conn().iterdump():
            f.write(f"{line}\n")
    buf = io.StringIO()
    with redirect_stdout(buf):
        log.cmd_restore()
    assert json.loads(buf.getvalue())["restored"] is True
    tables = {r[0] for r in log.conn().execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert {"progression", "flags", "priority", "deload_state", "meta"} <= tables
