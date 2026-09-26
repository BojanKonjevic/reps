#!/usr/bin/env python3
"""Scenarios are the shared test dataset: pytest goldens and TS fixtures derive from them."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import scenarios


def test_all_scenarios_build_and_validate(log_module):
    import tempfile
    import reps.db
    live = reps.db.DB
    for name, seed in scenarios.SCENARIOS.items():
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        reps.db.DB = path
        try:
            seed(log_module)
            snap = log_module.export_snapshot()
            assert snap["schema_version"] == 3, name
            assert snap["as_of"], name
        finally:
            reps.db.DB = live
            os.unlink(path)


def test_rich_scenario_shape(log_module, tmp_db):
    import reps.db
    reps.db.DB = tmp_db
    scenarios.seed_rich(log_module)
    snap = log_module.export_snapshot()
    assert {l["exercise"] for l in snap["lifts"]} >= {"bench", "row"}
    assert snap["next_up"]["day"] == "Upper A"
    assert len(snap["autoreg"]["holds"]) == 1
    assert snap["goals"] and snap["goals"][0]["percent"] is not None
    assert snap["adherence"] is not None


def test_break_scenario_status(log_module, tmp_db):
    import reps.db
    reps.db.DB = tmp_db
    scenarios.seed_break(log_module)
    snap = log_module.export_snapshot()
    assert snap["status"]["on_break"] is True
    assert any(s["status"] == "rest" for s in snap["sessions"])
