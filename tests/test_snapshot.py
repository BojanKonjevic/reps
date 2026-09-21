#!/usr/bin/env python3
"""pytest suite for the dashboard snapshot schema (export/sync forward state)."""

import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FORWARD_KEYS = ["split_active", "rotation", "constants", "progression",
                "goals", "priority", "deload", "rules", "flags",
                "mapping", "movement_notes"]


def capture(fn, *args):
    old = sys.stdout
    sys.stdout = io.StringIO()
    try:
        fn(*args)
        return sys.stdout.getvalue()
    finally:
        sys.stdout = old


def test_export_includes_forward_state(log_module):
    """Export carries program plus forward sections, not just history."""
    out = capture(log_module.cmd_export)
    snap = json.loads(out)
    for key in ["workouts", "sets", "bodyweight"] + FORWARD_KEYS:
        assert key in snap, f"snapshot missing '{key}'"
    assert isinstance(snap["split_active"], list)
    assert isinstance(snap["rotation"], list)
    assert isinstance(snap["progression"], dict)
    assert isinstance(snap["goals"], list)
    assert isinstance(snap["priority"], dict)


def test_export_forward_state_survives_empty_db(log_module, tmp_path, monkeypatch):
    """A fresh DB still exports the full schema with empty forward sections."""
    import sqlite3
    fresh = str(tmp_path / "fresh.db")
    monkeypatch.setattr(log_module, "DB", fresh)
    c = sqlite3.connect(fresh)
    c.executescript(log_module.SCHEMA)
    c.commit()
    c.close()
    out = capture(log_module.cmd_export)
    snap = json.loads(out)
    for key in FORWARD_KEYS:
        assert key in snap, f"snapshot missing '{key}' on fresh DB"
