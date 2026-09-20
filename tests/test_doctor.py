#!/usr/bin/env python3
"""Phase 5: doctor validates constants, DB, and dashboard consistency."""

import io
import json
from contextlib import redirect_stdout

import pytest
from conftest import seed_split


def _run(fn, *args):
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            fn(*args)
    except SystemExit as e:
        return buf.getvalue(), e.code
    return buf.getvalue(), 0


def test_doctor_healthy(log_module):
    log = log_module
    log.cmd_start("test")
    log.cmd_log("bench", 100, 5, "", "chest")
    seed_split(log, "Test", ("bench", 2))
    out, code = _run(log.cmd_doctor)
    assert code == 0
    assert json.loads(out) == {"ok": True, "muscles": 13}


def test_doctor_fails_on_bad_constants(log_module, tmp_path, monkeypatch):
    log = log_module
    p = tmp_path / "constants.json"
    p.write_text("{broken")
    monkeypatch.setattr(log, "CONSTANTS_FILE", str(p))
    out, code = _run(log.cmd_doctor)
    assert code == 1
    assert json.loads(out)["ok"] is False


def test_doctor_flags_unmapped_split_exercise(log_module):
    log = log_module
    c = log.conn()
    c.execute("INSERT INTO splits (variant, day, slot, movements, sets) VALUES ('active', 'Test', 1, 'mystery press', 2)")
    c.commit()
    out, code = _run(log.cmd_doctor)
    assert code == 1
    problems = json.loads(out)["problems"]
    assert [p for p in problems if p["check"] == "split_mapping" and "mystery press" in p["fix"]]


def test_doctor_flags_stray_muscle(log_module):
    log = log_module
    log.cmd_start("test")
    log.cmd_log("bench", 100, 5, "", "chest")
    c = log.conn()
    set_id = c.execute("SELECT id FROM sets").fetchone()["id"]
    c.execute("INSERT INTO set_muscles (set_id, muscle) VALUES (?, 'wings')", (set_id,))
    c.commit()
    out, code = _run(log.cmd_doctor)
    assert code == 1
    assert [p for p in json.loads(out)["problems"] if p["check"] == "muscle_coverage"]


def test_doctor_flags_dump_drift(log_module, tmp_path, monkeypatch):
    log = log_module
    live = str(tmp_path / "live.db")
    monkeypatch.setattr(log, "DB", live)
    log.conn().execute("SELECT 1")
    with open(tmp_path / "workouts.sql", "w") as f:
        f.write("CREATE TABLE workouts (id INTEGER PRIMARY KEY);\n")
    out, code = _run(log.cmd_doctor)
    assert code == 1
    assert [p for p in json.loads(out)["problems"] if p["check"] == "dump_drift"]
