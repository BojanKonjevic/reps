#!/usr/bin/env python3
"""Doctor validates constants, DB, and dump consistency.

Referential facts are FKs now: each deleted doctor check has a test below
that attempts the violation and expects a Refusal.
"""

import pytest
from conftest import seed_split
from reps.errors import RepsError


def test_doctor_healthy(log_module):
    log = log_module
    log.start_workout("test")
    log.log_set("bench", 100, 5, "", "chest")
    seed_split(log, "Test", ("bench", 2))
    log.set_rotation(["Test"])
    assert log.run_doctor() == {"ok": True, "muscles": len(log.load_constants().muscles)}


def test_doctor_fails_on_bad_constants(log_module, tmp_path, monkeypatch):
    log = log_module
    p = tmp_path / "constants.json"
    p.write_text("{broken")
    monkeypatch.setattr("reps.constants.CONSTANTS_FILE", str(p))
    with pytest.raises(RepsError, match="constants_parse"):
        log.run_doctor()


def test_fk_sets_exercise(log_module):
    """Unmapped set insert is refused by the FK (was: sets_mapping doctor check)."""
    import sqlite3
    log = log_module
    c = log.conn()
    wid = c.execute("INSERT INTO workouts (date, status, notes) VALUES ('2026-09-01', 'done', '')").lastrowid
    with pytest.raises(sqlite3.IntegrityError):
        c.execute("INSERT INTO sets (workout_id, exercise, weight, reps, note, created) "
                  "VALUES (?, 'ghost press', 100, 5, '', datetime('now'))", (wid,))


def test_fk_split_slot_lift(log_module):
    """Split slot with unknown lift is refused (was: split_mapping doctor check)."""
    log = log_module
    with pytest.raises(RepsError, match="not a known lift"):
        log.set_split("Test", 1, "mystery press", 2)


def test_fk_progression_workout(log_module):
    """Progression for a missing workout is refused (was: progression_workout check)."""
    log = log_module
    log.start_workout("test")
    log.log_set("bench", 100, 5, "", "chest")
    with pytest.raises(RepsError, match="no such workout"):
        log.set_progression("bench", "hit", 100, 5, "up", workout_id=9999)


def test_fk_rotation_day(log_module):
    """Rotation day outside splits is refused (was: rotation doctor check)."""
    log = log_module
    log.set_exercise_mapping("bench", "chest")
    seed_split(log, "Upper A", ("bench", 2))
    with pytest.raises(RepsError, match="must exist in splits"):
        log.set_rotation(["Upper A", "Nope C"])


def test_doctor_flags_stray_muscle(log_module):
    log = log_module
    log.start_workout("test")
    log.log_set("bench", 100, 5, "", "chest")
    c = log.conn()
    c.execute("INSERT INTO lift_muscle (exercise, muscle) VALUES ('bench', 'wings')")
    c.commit()
    assert [p for p in log.run_doctor()["problems"] if p["check"] == "muscle_coverage"]
    c.execute("DELETE FROM lift_muscle WHERE exercise = 'bench' AND muscle = 'wings'")
    c.commit()
    assert log.run_doctor()["ok"] is True


def test_doctor_rotation_rest_and_case(log_module):
    log = log_module
    log.set_exercise_mapping("bench", "chest")
    seed_split(log, "Upper A", ("bench", 2))
    log.set_rotation(["upper a", "rest"])
    assert log.run_doctor()["ok"] is True


def test_doctor_flags_dump_drift(log_module, tmp_path, monkeypatch):
    log = log_module
    live = str(tmp_path / "live.db")
    monkeypatch.setattr("reps.db.DB", live)
    log.conn().execute("SELECT 1")
    with open(tmp_path / "workouts.sql", "w") as f:
        f.write("CREATE TABLE workouts (id INTEGER PRIMARY KEY);\n")
    assert [p for p in log.run_doctor()["problems"] if p["check"] == "dump_drift"]
