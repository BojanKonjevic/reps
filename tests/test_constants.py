#!/usr/bin/env python3
"""Phase 0: constants.json is the single source of truth for taxonomy."""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONSTANTS = os.path.join(ROOT, "constants.json")
CHARTS = os.path.join(ROOT, "dashboard", "src", "charts.ts")
VOLUME_TEST = os.path.join(ROOT, "dashboard", "src", "__tests__", "volume.test.ts")

def test_constants_muscles_complete():
    # Expected list is derived from the file itself: this test pins shape
    # (every muscle has mev/color/freq), while doctor pins the tracked set
    # against live DB references. No second hardcoded copy.
    with open(CONSTANTS) as f:
        raw = json.load(f)
    assert len(raw["muscles"]) >= 1
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
    import subprocess
    out = subprocess.run(["rg", "-l", "constants.json", "dashboard/src",
                                  "--glob", "!**/__tests__/**", "--glob", "!**/fixtures/**",
                                  "--glob", "!**/generated/**"],
                         capture_output=True, text=True).stdout.strip()
    assert out == "", f"dashboard reads constants via snapshot only, found: {out}"


def test_generated_snapshot_types_are_the_only_ones():
    import subprocess
    out = subprocess.run(["rg", "-n", "(interface Snap\\w*|type Snap\\w*\\s*=)",
                                      "dashboard/src", "--glob", "!**/generated/**",
                                      "--glob", "!**/__tests__/**"],
                         capture_output=True, text=True).stdout.strip()
    lines = [ln for ln in out.splitlines() if "import " not in ln]
    assert lines == [], f"hand-written snapshot types found: {lines}"


def test_science_has_no_numeric_tables():
    with open(os.path.join(ROOT, "docs", "SCIENCE.md")) as f:
        text = f.read()
    assert "mev-bounds" not in text
    assert "| Chest" not in text
