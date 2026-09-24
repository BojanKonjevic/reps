#!/usr/bin/env python3
"""Phase 2: the end gate enforces session writeback at close time."""

import datetime as _dt

import pytest

from reps.errors import RepsError


def _run(fn, *args):
    try:
        return fn(*args), True
    except RepsError as e:
        return str(e), False


def _seed_session(log):
    from conftest import seed_split
    log.start_workout("test")
    log.log_set("bench", 100, 5, "", "chest")
    log.log_set("squat", 150, 5, "", "quads,glutes")
    seed_split(log, "Test", ("bench", 2), ("squat", 2))
    w = log.open_workout(log.conn())
    return w["id"]


def test_end_blocked_without_progression(log_module):
    log = log_module
    _seed_session(log)
    out, code = _run(log.end_workout, "")
    assert code is False
    assert "missing progression: bench" in out
    assert "missing progression: squat" in out
    assert "progression_set" in out
    assert log.open_workout(log.conn()) is not None


def test_check_dry_run_matches_end(log_module):
    log = log_module
    _seed_session(log)
    out, code = _run(log.check_end_gate)
    assert code is False
    assert "not ready to close" in out


def test_progression_next_requires_reps(log_module):
    log = log_module
    _seed_session(log)
    with pytest.raises(RepsError, match="next reps must be an integer"):
        log.set_progression("bench", "hit", 102.5, "up", "up")


def test_end_succeeds_after_progression(log_module):
    log = log_module
    _seed_session(log)
    log.set_progression("bench", "hit", 102.5, 5, "up")
    log.set_progression("squat", "hold", 150, 5, "flat")
    out, code = _run(log.check_end_gate)
    assert code is True
    assert out["ready"]
    out, code = _run(log.end_workout, "good session")
    assert code is True
    assert out["sets"] == 2
    assert log.open_workout(log.conn()) is None


def test_end_blocked_on_muscleless_set(log_module):
    log = log_module
    log.start_workout("test")
    c = log.conn()
    wid = log.open_workout(c)["id"]
    from conftest import seed_lift as _seed
    _seed(c, "bench", None)
    c.execute("INSERT INTO sets (workout_id, exercise, weight, reps, note, created) VALUES (?, 'bench', 100, 5, '', datetime('now'))", (wid,))
    c.commit()
    out, code = _run(log.end_workout, "")
    assert code is False
    assert "has no muscles" in out


def test_end_force_cannot_skip_muscles(log_module):
    log = log_module
    log.start_workout("test")
    c = log.conn()
    wid = log.open_workout(c)["id"]
    from conftest import seed_lift as _seed2
    _seed2(c, "bench", None)
    c.execute("INSERT INTO sets (workout_id, exercise, weight, reps, note, created) VALUES (?, 'bench', 100, 5, '', datetime('now'))", (wid,))
    c.commit()
    out, code = _run(log.end_workout, "", "force it")
    assert code is False
    assert "hard items" in out
    assert "muscle_map_set" in out


def test_end_force_records_reason(log_module):
    log = log_module
    _seed_session(log)
    out, code = _run(log.end_workout, "", "short session, skipping writeback")
    assert code is True
    assert out["forced"] == "short session, skipping writeback"
    row = log.conn().execute("SELECT notes FROM workouts WHERE status = 'done'").fetchone()
    assert "forced: short session" in row["notes"]


def test_end_requires_deload_note(log_module):
    log = log_module
    _seed_session(log)
    log.set_deload("lift", "bench")
    log.set_progression("bench", "hold", 100, 5, "flat")
    log.set_progression("squat", "hold", 150, 5, "flat")
    out, code = _run(log.end_workout, "easy day")
    assert code is False
    assert "deload" in out
    out, code = _run(log.end_workout, "easy deload day")
    assert code is True


def test_end_requires_deload_note_for_slot_scope(log_module):
    from conftest import seed_split
    log = log_module
    log.start_workout("test")
    log.log_set("bench", 100, 5, "", "chest")
    seed_split(log, "Upper A", ("bench", 2))
    log.set_progression("bench", "hold", 100, 5, "flat")
    log.set_deload("slot", "upper a")
    assert log.active_deloads(log.conn())[0]["subject"] == "Upper A"
    out, code = _run(log.end_workout, "easy day")
    assert code is False
    assert "deload" in out
    out, code = _run(log.end_workout, "easy deload day")
    assert code is True


def test_deload_set_rejects_unknown_day(log_module):
    log = log_module
    with pytest.raises(RepsError, match="no active split day"):
        log.set_deload("slot", "Nope C")


def test_progression_rejects_unknown_exercise(log_module):
    log = log_module
    _seed_session(log)
    with pytest.raises(RepsError, match="no sets in workout"):
        log.set_progression("deadlift", "hit", 180, 5, "up")


def test_deload_clear_appends_state_line(log_module, tmp_path, monkeypatch):
    log = log_module
    p = tmp_path / "MEMORY.md"
    p.write_text("# memory\n\n## State\n\n- old line\n\n## Other\n")
    monkeypatch.setattr("reps.memory.MEMORY_FILE", str(p))
    log.set_exercise_mapping("bench", "chest")
    log.set_deload("lift", "bench")
    log.clear_deload()
    text = p.read_text()
    assert "deload completed for lift bench" in text
    assert "- old line" in text


def test_plan_read_never_consumes(log_module):
    log = log_module
    log.add_flag("bench", "watch this")
    for _ in range(2):
        assert [f["subject"] for f in log.get_plan()["flags"]] == ["bench"]


def test_end_consumes_session_flags(log_module):
    log = log_module
    _seed_session(log)
    log.add_flag("bench", "watch this")
    log.add_flag("squat", "watch that")
    log.add_flag("deadlift", "unrelated")
    log.set_progression("bench", "hold", 100, 5, "flat")
    log.set_progression("squat", "hold", 150, 5, "flat")
    assert log.end_workout("done")["flags_consumed"] == 2
    assert [f["subject"] for f in log.list_flags()] == ["deadlift"]
    assert log.consume_flag(3) == {"consumed": 3}


def test_plan_consumes_only_day_relevant_flags(log_module):
    import json as _json
    from datetime import timedelta
    from conftest import seed_split
    log = log_module
    c = log.conn()
    for ex in ["incline barbell bench press", "hammer strength row", "pec deck", "hack squat"]:
        log.set_exercise_mapping(ex, "chest")
    seed_split(log, "Upper A", ("incline barbell bench press", 3), ("hammer strength row", 2), ("pec deck", 2))
    seed_split(log, "Lower A", ("hack squat", 2))
    log.set_rotation(["Upper A", "Lower A"])
    d = (_dt.date.today() - timedelta(days=1)).isoformat()
    cur = c.execute("INSERT INTO workouts (date, status, notes) VALUES (?, 'done', '')", (d,))
    c.commit()
    for ex in ["incline barbell bench press", "hammer strength row", "pec deck"]:
        cur2 = c.execute(
            "INSERT INTO sets (workout_id, exercise, weight, reps, note, created) VALUES (?, ?, 80, 6, '', datetime('now'))",
            (cur.lastrowid, ex))
        pass
    c.commit()
    log.add_flag("hack squat", "watch depth")
    log.add_flag("incline barbell bench press", "old news")
    for _ in range(2):
        bundle = log.get_plan()
        assert bundle["slot_guess"]["day"] == "Lower A"
        assert {f["subject"] for f in bundle["flags"]} == {"hack squat", "incline barbell bench press"}


def test_read_commands_roundtrip(log_module):
    log = log_module
    _seed_session(log)
    log.set_progression("bench", "hit", 102.5, 5, "up")
    assert log.get_progression("bench")[0]["next"] == "102.5x5"
    assert [r["exercise"] for r in log.get_progression()] == ["bench"]
    log.add_flag("bench", "watch this")
    assert log.list_flags()[0]["reason"] == "watch this"
    log.set_priority("chest", "priority", None)
    assert log.list_priorities()[0]["tier"] == "priority"
    log.clear_priority("chest")
    assert log.list_priorities() == []


def test_deload_set_idempotent(log_module):
    log = log_module
    log.set_exercise_mapping("bench", "chest")
    first = log.set_deload("lift", "bench")
    second = log.set_deload("lift", "bench")
    assert second["deload_id"] == first["deload_id"]
    assert second["reused"] is True
    assert len(log.active_deloads(log.conn())) == 1


def test_check_accepts_prospective_note(log_module):
    log = log_module
    _seed_session(log)
    log.set_deload("lift", "bench")
    log.set_progression("bench", "hold", 100, 5, "flat")
    log.set_progression("squat", "hold", 150, 5, "flat")
    _, code = _run(log.check_end_gate, "")
    assert code is False
    out, code = _run(log.check_end_gate, "easy deload day")
    assert code is True
    assert out["ready"]


def test_expired_priority_stops_applying(log_module):
    import datetime as _dt2
    log = log_module
    log.set_priority("chest", "deprioritize", (_dt.date.today() - _dt.timedelta(days=1)).isoformat())
    assert log.read_priorities(log.conn()) == {}
    needs = log.get_plan()["rules"]["needs_confirm"]
    assert [n for n in needs if n.get("muscle") == "chest" and n.get("expired")]


def test_plan_surfaces_priority_and_deload(log_module):
    from conftest import seed_split
    log = log_module
    log.set_exercise_mapping("bench", "chest")
    seed_split(log, "Upper A", ("bench", 2))
    log.set_priority("chest", "priority", None)
    log.set_deload("slot", "Upper A")
    bundle = log.get_plan()
    assert bundle["priority"]["chest"]["tier"] == "priority"
    assert bundle["deload"][0] == {"id": 1, "scope": "slot", "subject": "Upper A",
                                  "set_on": _dt.date.today().isoformat(), "cleared_on": None}


def test_restore_accepts_new_tables(log_module, tmp_path, monkeypatch):
    """restore's expected set derives from SCHEMA, so new tables pass."""
    log = log_module
    _seed_session(log)
    log.set_progression("bench", "baseline", 100, 5, "flat")
    live = str(tmp_path / "live.db")
    monkeypatch.setattr("reps.db.DB", live)
    with open(tmp_path / "workouts.sql", "w") as f:
        for line in log.conn().iterdump():
            f.write(f"{line}\n")
    assert log.restore_sql()["restored"] is True
    tables = {r[0] for r in log.conn().execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert {"progression", "flags", "priority", "deload_state", "rotation",
             "rotation_anchor", "compaction", "lift", "lift_muscle",
             "split_day", "split_slot", "split_slot_lift"} <= tables
    assert "meta" not in tables
