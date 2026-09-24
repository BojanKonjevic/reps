#!/usr/bin/env python3
"""log.py is maintenance only: four ops, JSON out, nonzero exit on refusal.

Guards the process boundary: the domain never prints or exits, so this
module is the only place where results become process output.
"""

import json
import sys

import pytest

import log as maintenance
from reps.errors import RepsError


def run(argv):
    old = sys.argv
    sys.argv = ["log.py", *argv]
    try:
        maintenance.main()
    finally:
        sys.argv = old


def test_maintenance_ops_emit_json(log_module, tmp_path, monkeypatch, capsys):
    """Each op prints its structured result as JSON."""
    import sqlite3
    fresh = str(tmp_path / "isolated.db")
    monkeypatch.setattr("reps.db.DB", fresh)
    c = sqlite3.connect(fresh)
    c.executescript(log_module.SCHEMA)
    c.execute("INSERT INTO meta (key, value) VALUES ('rotation', '[\"Test\"]')")
    c.execute(
        "INSERT INTO splits (variant, day, slot, movements, sets) VALUES ('active', 'Test', 1, 'bench', 2)")
    c.execute(
        "INSERT INTO lift_muscle_map (exercise, muscles, is_bodyweight_only) VALUES ('bench', 'chest', 0)")
    c.commit()
    c.close()
    run(["doctor"])
    assert json.loads(capsys.readouterr().out)["ok"] is True
    run(["dump"])
    assert "dumped" in json.loads(capsys.readouterr().out)
    run(["export"])
    assert "workouts" in json.loads(capsys.readouterr().out)


def test_maintenance_rejects_unknown_ops(capsys):
    with pytest.raises(SystemExit):
        run(["start"])
    with pytest.raises(SystemExit):
        run([])
    with pytest.raises(SystemExit):
        run(["sync"])


def test_maintenance_reports_domain_refusals(log_module, tmp_path, monkeypatch, capsys):
    """Refusals surface on stderr with a nonzero exit, never a traceback."""
    import sqlite3
    fresh = str(tmp_path / "fresh.db")
    monkeypatch.setattr("reps.db.DB", fresh)
    c = sqlite3.connect(fresh)
    c.executescript(log_module.SCHEMA)
    c.commit()
    c.close()
    c = log_module.conn()
    log_module.start_workout("open")
    with pytest.raises(SystemExit) as e:
        run(["restore"])
    assert e.value.code == 1
    assert "still open" in capsys.readouterr().err


def test_domain_refusal_is_not_a_process_exit():
    """RepsError carries the message; only log.py assigns exit codes."""
    err = RepsError("no open workout")
    assert str(err) == "no open workout"
    assert not isinstance(err, SystemExit)
