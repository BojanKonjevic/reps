#!/usr/bin/env python3
"""Phase 5: doctor validates constants, DB, and dashboard consistency."""

import json

import pytest
from conftest import seed_split
from reps.errors import RepsError


def test_doctor_healthy(log_module):
    log = log_module
    log.start_workout("test")
    log.log_set("bench", 100, 5, "", "chest")
    seed_split(log, "Test", ("bench", 2))
    c = log.conn()
    c.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('rotation', ?)", (json.dumps(["Test"]),))
    c.commit()
    assert log.run_doctor() == {"ok": True, "muscles": len(log.load_constants().muscles)}


def test_doctor_fails_on_bad_constants(log_module, tmp_path, monkeypatch):
    log = log_module
    p = tmp_path / "constants.json"
    p.write_text("{broken")
    monkeypatch.setattr("reps.constants.CONSTANTS_FILE", str(p))
    with pytest.raises(RepsError, match="constants_parse"):
        log.run_doctor()


def test_doctor_flags_unmapped_split_exercise(log_module):
    log = log_module
    c = log.conn()
    c.execute("INSERT INTO splits (variant, day, slot, movements, sets) VALUES ('active', 'Test', 1, 'mystery press', 2)")
    c.commit()
    problems = log.run_doctor()["problems"]
    assert [p for p in problems if p["check"] == "split_mapping" and "mystery press" in p["fix"]]


def test_doctor_flags_stray_muscle(log_module):
    log = log_module
    log.start_workout("test")
    log.log_set("bench", 100, 5, "", "chest")
    c = log.conn()
    set_id = c.execute("SELECT id FROM sets").fetchone()["id"]
    c.execute("INSERT INTO set_muscles (set_id, muscle) VALUES (?, 'wings')", (set_id,))
    c.commit()
    assert [p for p in log.run_doctor()["problems"] if p["check"] == "muscle_coverage"]


def test_doctor_flags_bad_rotation(log_module):
    log = log_module
    c = log.conn()
    c.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('rotation', ?)",
              (json.dumps(["Upper A", "Nope C"]),))
    c.commit()
    assert [p for p in log.run_doctor()["problems"] if p["check"] == "rotation"]


def test_doctor_rotation_edge_cases(log_module):
    log = log_module
    log.set_exercise_mapping("bench", "chest")
    seed_split(log, "Upper A", ("bench", 2))
    c = log.conn()
    # rest entries exempt, case-insensitive day match
    c.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('rotation', ?)",
              (json.dumps(["upper a", "rest"]),))
    c.commit()
    assert log.run_doctor()["ok"] is True
    for bad in ("[]", "{bad json", json.dumps(["Upper A", 3])):
        c.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('rotation', ?)", (bad,))
        c.commit()
        problems = log.run_doctor()["problems"]
        assert [p for p in problems if p["check"] == "rotation"]


def test_doctor_flags_dump_drift(log_module, tmp_path, monkeypatch):
    log = log_module
    live = str(tmp_path / "live.db")
    monkeypatch.setattr("reps.db.DB", live)
    log.conn().execute("SELECT 1")
    with open(tmp_path / "workouts.sql", "w") as f:
        f.write("CREATE TABLE workouts (id INTEGER PRIMARY KEY);\n")
    assert [p for p in log.run_doctor()["problems"] if p["check"] == "dump_drift"]
