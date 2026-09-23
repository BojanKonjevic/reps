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
    from conftest import seed_split
    log.start("test")
    log.log("bench", 100, 5, "", "chest")
    log.log("squat", 150, 5, "", "quads,glutes")
    seed_split(log, "Test", ("bench", 2), ("squat", 2))
    w = log.open_workout(log.conn())
    return w["id"]


def test_end_blocked_without_progression(log_module):
    log = log_module
    _seed_session(log)
    out, code = _run(log.end, "")
    assert code == 1
    assert "missing progression: bench" in out
    assert "missing progression: squat" in out
    assert "progression_set" in out
    assert log.open_workout(log.conn()) is not None


def test_check_dry_run_matches_end(log_module):
    log = log_module
    _seed_session(log)
    out, code = _run(log.check)
    assert code == 1
    assert "not ready to close" in out


def test_progression_next_requires_reps(log_module):
    log = log_module
    _seed_session(log)
    with pytest.raises(SystemExit, match="weight x reps"):
        log.progression_set("bench", "hit", "102.5", "up")


def test_end_succeeds_after_progression(log_module):
    log = log_module
    _seed_session(log)
    log.progression_set("bench", "hit", "102.5x5", "up")
    log.progression_set("squat", "hold", "150x5", "flat")
    out, code = _run(log.check)
    assert code == 0
    assert json.loads(out)["ready"]
    out, code = _run(log.end, "good session")
    assert code == 0
    assert json.loads(out)["sets"] == 2
    assert log.open_workout(log.conn()) is None


def test_end_blocked_on_muscleless_set(log_module):
    log = log_module
    log.start("test")
    c = log.conn()
    wid = log.open_workout(c)["id"]
    c.execute("INSERT INTO sets (workout_id, exercise, weight, reps, note, created) VALUES (?, 'bench', 100, 5, '', datetime('now'))", (wid,))
    c.commit()
    out, code = _run(log.end, "")
    assert code == 1
    assert "has no muscles" in out


def test_end_force_cannot_skip_muscles(log_module):
    log = log_module
    log.start("test")
    c = log.conn()
    wid = log.open_workout(c)["id"]
    c.execute("INSERT INTO sets (workout_id, exercise, weight, reps, note, created) VALUES (?, 'bench', 100, 5, '', datetime('now'))", (wid,))
    c.commit()
    out, code = _run(log.end, "", "force it")
    assert code == 1
    assert "hard items" in out
    assert "muscle_map_set" in out


def test_end_force_records_reason(log_module):
    log = log_module
    _seed_session(log)
    out, code = _run(log.end, "", "short session, skipping writeback")
    assert code == 0
    assert json.loads(out)["forced"] == "short session, skipping writeback"
    row = log.conn().execute("SELECT notes FROM workouts WHERE status = 'done'").fetchone()
    assert "forced: short session" in row["notes"]


def test_end_requires_deload_note(log_module):
    log = log_module
    _seed_session(log)
    log.deload_set("lift", "bench")
    log.progression_set("bench", "hold", "100x5", "flat")
    log.progression_set("squat", "hold", "150x5", "flat")
    out, code = _run(log.end, "easy day")
    assert code == 1
    assert "deload" in out
    out, code = _run(log.end, "easy deload day")
    assert code == 0


def test_end_requires_deload_note_for_slot_scope(log_module):
    from conftest import seed_split
    log = log_module
    log.start("test")
    log.log("bench", 100, 5, "", "chest")
    seed_split(log, "Upper A", ("bench", 2))
    log.progression_set("bench", "hold", "100x5", "flat")
    log.deload_set("slot", "upper a")
    assert log.active_deloads(log.conn())[0]["subject"] == "Upper A"
    out, code = _run(log.end, "easy day")
    assert code == 1
    assert "deload" in out
    out, code = _run(log.end, "easy deload day")
    assert code == 0


def test_deload_set_rejects_unknown_day(log_module):
    log = log_module
    with pytest.raises(SystemExit, match="no active split day"):
        log.deload_set("slot", "Nope C")


def test_progression_rejects_unknown_exercise(log_module):
    log = log_module
    _seed_session(log)
    with pytest.raises(SystemExit, match="no sets in workout"):
        log.progression_set("deadlift", "hit", "180x5", "up")


def test_deload_clear_appends_state_line(log_module, tmp_path, monkeypatch):
    log = log_module
    p = tmp_path / "MEMORY.md"
    p.write_text("# memory\n\n## State\n\n- old line\n\n## Other\n")
    monkeypatch.setattr("reps.memory.MEMORY_FILE", str(p))
    log.retag("bench", "chest")
    log.deload_set("lift", "bench")
    log.deload_clear()
    text = p.read_text()
    assert "deload completed for lift bench" in text
    assert "- old line" in text


def test_plan_read_never_consumes(log_module):
    log = log_module
    log.flag_add("bench", "watch this")
    for _ in range(2):
        buf = io.StringIO()
        with redirect_stdout(buf):
            log.plan()
        assert [f["subject"] for f in json.loads(buf.getvalue())["flags"]] == ["bench"]


def test_end_consumes_session_flags(log_module):
    log = log_module
    _seed_session(log)
    log.flag_add("bench", "watch this")
    log.flag_add("squat", "watch that")
    log.flag_add("deadlift", "unrelated")
    log.progression_set("bench", "hold", "100x5", "flat")
    log.progression_set("squat", "hold", "150x5", "flat")
    buf = io.StringIO()
    with redirect_stdout(buf):
        log.end("done")
    assert json.loads(buf.getvalue())["flags_consumed"] == 2
    buf = io.StringIO()
    with redirect_stdout(buf):
        log.flag_list()
    assert [f["subject"] for f in json.loads(buf.getvalue())] == ["deadlift"]
    buf = io.StringIO()
    with redirect_stdout(buf):
        log.flag_consume(3)
    assert json.loads(buf.getvalue()) == {"consumed": 3}


def test_plan_consumes_only_day_relevant_flags(log_module):
    import json as _json
    from datetime import timedelta
    from conftest import seed_split
    log = log_module
    c = log.conn()
    for ex in ["incline barbell bench press", "hammer strength row", "pec deck", "hack squat"]:
        c.execute("INSERT OR IGNORE INTO lift_muscle_map (exercise, muscles, is_bodyweight_only) VALUES (?, 'chest', 0)", (ex,))
    c.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('rotation', ?)",
              (_json.dumps(["Upper A", "Lower A"]),))
    c.commit()
    seed_split(log, "Upper A", ("incline barbell bench press", 3), ("hammer strength row", 2), ("pec deck", 2))
    seed_split(log, "Lower A", ("hack squat", 2))
    d = (_dt.date.today() - timedelta(days=1)).isoformat()
    cur = c.execute("INSERT INTO workouts (date, status, notes) VALUES (?, 'done', '')", (d,))
    c.commit()
    for ex in ["incline barbell bench press", "hammer strength row", "pec deck"]:
        cur2 = c.execute(
            "INSERT INTO sets (workout_id, exercise, weight, reps, note, created) VALUES (?, ?, 80, 6, '', datetime('now'))",
            (cur.lastrowid, ex))
        c.execute("INSERT INTO set_muscles (set_id, muscle) VALUES (?, 'chest')", (cur2.lastrowid,))
    c.commit()
    log.flag_add("hack squat", "watch depth")
    log.flag_add("incline barbell bench press", "old news")
    for _ in range(2):
        buf = io.StringIO()
        with redirect_stdout(buf):
            log.plan()
        bundle = json.loads(buf.getvalue())
        assert bundle["slot_guess"]["day"] == "Lower A"
        assert {f["subject"] for f in bundle["flags"]} == {"hack squat", "incline barbell bench press"}


def test_read_commands_roundtrip(log_module):
    log = log_module
    _seed_session(log)
    log.progression_set("bench", "hit", "102.5x5", "up")
    buf = io.StringIO()
    with redirect_stdout(buf):
        log.progression_show("bench")
    assert json.loads(buf.getvalue())[0]["next_target"] == "102.5x5"
    buf = io.StringIO()
    with redirect_stdout(buf):
        log.progression_show()
    assert [r["exercise"] for r in json.loads(buf.getvalue())] == ["bench"]
    log.flag_add("bench", "watch this")
    buf = io.StringIO()
    with redirect_stdout(buf):
        log.flag_list()
    assert json.loads(buf.getvalue())[0]["reason"] == "watch this"
    log.priority_set("chest", "priority", None)
    buf = io.StringIO()
    with redirect_stdout(buf):
        log.priority_list()
    assert json.loads(buf.getvalue())[0]["tier"] == "priority"
    log.priority_clear("chest")
    buf = io.StringIO()
    with redirect_stdout(buf):
        log.priority_list()
    assert json.loads(buf.getvalue()) == []


def test_deload_set_idempotent(log_module):
    log = log_module
    log.retag("bench", "chest")
    buf = io.StringIO()
    with redirect_stdout(buf):
        log.deload_set("lift", "bench")
    first = json.loads(buf.getvalue())
    buf = io.StringIO()
    with redirect_stdout(buf):
        log.deload_set("lift", "bench")
    second = json.loads(buf.getvalue())
    assert second["deload_id"] == first["deload_id"]
    assert second["reused"] is True
    assert len(log.active_deloads(log.conn())) == 1


def test_check_accepts_prospective_note(log_module):
    log = log_module
    _seed_session(log)
    log.deload_set("lift", "bench")
    log.progression_set("bench", "hold", "100x5", "flat")
    log.progression_set("squat", "hold", "150x5", "flat")
    _, code = _run(log.check, "")
    assert code == 1
    out, code = _run(log.check, "easy deload day")
    assert code == 0
    assert json.loads(out)["ready"]


def test_expired_priority_stops_applying(log_module):
    import datetime as _dt2
    log = log_module
    log.priority_set("chest", "deprioritize", (_dt.date.today() - _dt.timedelta(days=1)).isoformat())
    assert log.read_priorities(log.conn()) == {}
    buf = io.StringIO()
    with redirect_stdout(buf):
        log.plan()
    needs = json.loads(buf.getvalue())["rules"]["needs_confirm"]
    assert [n for n in needs if n.get("muscle") == "chest" and n.get("expired")]


def test_plan_surfaces_priority_and_deload(log_module):
    from conftest import seed_split
    log = log_module
    log.retag("bench", "chest")
    seed_split(log, "Upper A", ("bench", 2))
    log.priority_set("chest", "priority", None)
    log.deload_set("slot", "Upper A")
    buf = io.StringIO()
    with redirect_stdout(buf):
        log.plan()
    bundle = json.loads(buf.getvalue())
    assert bundle["priority"]["chest"]["tier"] == "priority"
    assert bundle["deload"][0] == {"id": 1, "scope": "slot", "subject": "Upper A",
                                  "set_on": _dt.date.today().isoformat(), "cleared_on": None}


def test_restore_accepts_new_tables(log_module, tmp_path, monkeypatch):
    """restore's expected set derives from SCHEMA, so new tables pass."""
    log = log_module
    _seed_session(log)
    log.progression_set("bench", "baseline", "100x5", "flat")
    live = str(tmp_path / "live.db")
    monkeypatch.setattr("reps.db.DB", live)
    with open(tmp_path / "workouts.sql", "w") as f:
        for line in log.conn().iterdump():
            f.write(f"{line}\n")
    buf = io.StringIO()
    with redirect_stdout(buf):
        log.restore()
    assert json.loads(buf.getvalue())["restored"] is True
    tables = {r[0] for r in log.conn().execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert {"progression", "flags", "priority", "deload_state", "meta"} <= tables
