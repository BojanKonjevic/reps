#!/usr/bin/env python3
"""Phase 0: constants.json is the single source of truth for taxonomy."""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONSTANTS = os.path.join(ROOT, "constants.json")
CHARTS = os.path.join(ROOT, "dashboard", "src", "charts.ts")
VOLUME_TEST = os.path.join(ROOT, "dashboard", "src", "__tests__", "volume.test.ts")

EXPECTED_MUSCLES = [
    "chest", "back", "front delt", "side delt", "rear delt",
    "biceps", "triceps", "quads", "hamstrings", "glutes",
    "adductors", "abs", "forearms",
]


def test_constants_muscles_complete():
    with open(CONSTANTS) as f:
        raw = json.load(f)
    assert list(raw["muscles"].keys()) == EXPECTED_MUSCLES
    for muscle, entry in raw["muscles"].items():
        assert isinstance(entry["mev"], int), muscle
        assert isinstance(entry["color"], str), muscle
        assert isinstance(entry["freq"], list), muscle


def test_constants_thresholds_complete():
    with open(CONSTANTS) as f:
        raw = json.load(f)
    for key in ("stale_workout_hours", "stale_workout_days", "break_days",
                "progression_drop_pct", "e1rm_warn_ratio",
                "duplicate_name_distance", "volume_window_weeks", "volume_bad_weeks"):
        assert key in raw["thresholds"], key


def test_dashboard_derives_from_constants():
    with open(CHARTS) as f:
        text = f.read()
    assert "constants.json" in text
    assert "#ffa726" not in text, "MC literals must be derived, not hardcoded"


def test_dashboard_volume_test_derives_blank():
    with open(VOLUME_TEST) as f:
        text = f.read()
    assert "GROUPS" in text
    assert "forearms: 0" not in text, "blank() must derive from GROUPS, not a literal"


def test_science_has_no_numeric_tables():
    with open(os.path.join(ROOT, "SCIENCE.md")) as f:
        text = f.read()
    assert "mev-bounds" not in text
    assert "| Chest" not in text
