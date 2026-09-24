#!/usr/bin/env python3
"""pytest suite for the dashboard snapshot schema (export/sync forward state)."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FORWARD_KEYS = ["split_active", "rotation", "constants", "progression",
                "goals", "priority", "deload", "rules", "flags",
                "mapping", "movement_notes", "adherence", "signals",
                "autoreg", "autoreg_changes", "volume"]


def test_export_includes_forward_state(log_module):
    """Export carries program plus forward sections, not just history."""
    snap = log_module.export_snapshot()
    for key in ["workouts", "sets", "bodyweight"] + FORWARD_KEYS:
        assert key in snap, f"snapshot missing '{key}'"
    assert isinstance(snap["split_active"], list)
    assert isinstance(snap["rotation"], list)
    assert isinstance(snap["progression"], dict)
    assert isinstance(snap["goals"], list)
    assert isinstance(snap["priority"], dict)


def test_export_list_pages_shape(log_module):
    """List pages get autoreg, recent changes, adherence drift, and volume."""
    log = log_module
    c = log.conn()
    log.set_exercise_mapping("bench", "chest")
    log.set_exercise_mapping("incline", "chest")
    log.set_split("Upper A", 1, "bench", 5)
    log.set_split("Upper A", 2, "incline", 5)
    log.set_meta("rotation", json.dumps(["Upper A", "rest"]))
    log.anchor_rotation("2026-09-01", "Upper A")
    log.add_rule("autoreg: manage volume", "autoreg", None)
    log.apply_autoreg("Upper A", 1, "bench", 4, "testing")
    snap = log.export_snapshot()
    assert set(snap["autoreg"]) == {"permitted", "holds", "miss_streaks", "drop_watch",
                                    "grouped", "program_volume"}
    assert snap["autoreg"]["permitted"] is True
    assert len(snap["autoreg"]["holds"]) == 1
    assert len(snap["autoreg_changes"]) == 1
    assert snap["autoreg_changes"][0]["evidence"] == "testing"
    assert set(snap["adherence"]) == {"anchor", "days", "drift", "drift_days", "drift_threshold"}
    assert snap["volume"]["chest"]["status"] in ("below_mev", "in_range", "above_mrv")
    assert set(snap["volume"]["chest"]) == {"weekly", "mev", "mav", "mrv", "freq", "status"}
    assert isinstance(snap["signals"], list)


def test_export_forward_state_survives_empty_db(log_module, tmp_path, monkeypatch):
    """A fresh DB still exports the full schema with empty forward sections."""
    import sqlite3
    fresh = str(tmp_path / "fresh.db")
    monkeypatch.setattr("reps.db.DB", fresh)
    c = sqlite3.connect(fresh)
    c.executescript(log_module.SCHEMA)
    c.commit()
    c.close()
    snap = log_module.export_snapshot()
    for key in FORWARD_KEYS:
        assert key in snap, f"snapshot missing '{key}' on fresh DB"
