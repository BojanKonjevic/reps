#!/usr/bin/env python3
"""Pydantic boundary tests: constants and snapshot schemas."""

import copy
import io
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reps.models import (ConstantsModel, SnapshotModel, SnapshotValidationError, validate_snapshot)


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _file_constants():
    with open(os.path.join(ROOT, "constants.json")) as f:
        return json.load(f)


def test_file_constants_validate():
    ConstantsModel.model_validate(_file_constants())


def test_constants_rejects_bool_mev():
    raw = _file_constants()
    raw["muscles"]["chest"]["mev"] = True
    with pytest.raises(Exception):
        ConstantsModel.model_validate(raw)


def test_constants_rejects_bad_color():
    raw = _file_constants()
    raw["muscles"]["chest"]["color"] = "red"
    with pytest.raises(Exception):
        ConstantsModel.model_validate(raw)


def test_constants_rejects_embedded_color():
    raw = _file_constants()
    raw["muscles"]["chest"]["color"] = "xx#ffa726yy"
    with pytest.raises(Exception):
        ConstantsModel.model_validate(raw)


def test_constants_rejects_bad_tier():
    raw = _file_constants()
    raw["muscles"]["chest"]["tier"] = "proven"
    with pytest.raises(Exception):
        ConstantsModel.model_validate(raw)


def test_constants_rejects_inverted_mav():
    raw = _file_constants()
    raw["muscles"]["chest"]["mav"] = [20, 14]
    with pytest.raises(Exception):
        ConstantsModel.model_validate(raw)


def test_constants_rejects_empty_muscles():
    raw = _file_constants()
    raw["muscles"] = {}
    with pytest.raises(Exception):
        ConstantsModel.model_validate(raw)


def test_constants_rejects_positive_drop():
    raw = _file_constants()
    raw["thresholds"]["progression_drop_pct"] = 5
    with pytest.raises(Exception):
        ConstantsModel.model_validate(raw)


def test_constants_rejects_unordered_bands():
    raw = _file_constants()
    raw["rep_bands"] = [{"max_reps": 10, "jump_pct": 5.0}, {"max_reps": 6, "jump_pct": 4.0},
                        {"max_reps": None, "jump_pct": None}]
    with pytest.raises(Exception):
        ConstantsModel.model_validate(raw)


def test_constants_rejects_half_band():
    raw = _file_constants()
    raw["rep_bands"] = [{"max_reps": 6, "jump_pct": None}, {"max_reps": None, "jump_pct": None}]
    with pytest.raises(Exception):
        ConstantsModel.model_validate(raw)


def test_constants_allows_terminator_and_null_mav():
    raw = _file_constants()
    assert raw["muscles"]["forearms"]["mav"] is None
    ConstantsModel.model_validate(raw)


def test_validate_constants_exits_loudly():
    from reps.constants import validate_constants
    with pytest.raises(SystemExit, match="constants invalid"):
        validate_constants({"muscles": {}}, "test-source")


def test_snapshot_validates_built_payload(log_module):
    snap = log_module.build_snapshot_validated()
    assert snap["exported"]
    assert isinstance(snap["workouts"], list)


def test_snapshot_rejects_missing_exported():
    with pytest.raises(SnapshotValidationError):
        validate_snapshot({"workouts": [], "sets": []})


def test_snapshot_rejects_string_weight():
    with pytest.raises(SnapshotValidationError):
        validate_snapshot({"exported": "2026-01-01T00:00:00", "workouts": [],
                           "sets": [{"id": 1, "workout_id": 1, "exercise": "bench",
                                     "weight": "heavy", "reps": 5}]})


def test_snapshot_tolerates_unknown_sections():
    snap = {"exported": "2026-01-01T00:00:00", "workouts": [], "sets": [],
            "future_section": {"anything": [1, 2, 3]}}
    model = validate_snapshot(snap)
    assert model.exported == "2026-01-01T00:00:00"


def test_snapshot_tolerates_older_payload():
    snap = {"exported": "2026-01-01T00:00:00", "workouts": [], "sets": [],
            "bodyweight": []}
    model = validate_snapshot(snap)
    assert model.adherence is None
    assert model.autoreg is None
    assert model.volume == {}


def test_snapshot_volume_entry_shape(log_module):
    log = log_module
    log.cmd_retag("bench", "chest")
    log.cmd_split_set("Upper A", 1, "bench", 5)
    snap = log.build_snapshot_validated()
    assert set(snap["volume"]["chest"]) == {"weekly", "mev", "mav", "mrv", "freq", "status"}
    SnapshotModel.model_validate(snap)


def test_snapshot_rejects_bad_workout_status():
    with pytest.raises(SnapshotValidationError):
        validate_snapshot({"exported": "2026-01-01T00:00:00",
                           "workouts": [{"id": 1, "date": "2026-01-01", "status": "archived"}],
                           "sets": []})


def test_snapshot_rejects_bad_adherence_status():
    with pytest.raises(SnapshotValidationError):
        validate_snapshot({"exported": "2026-01-01T00:00:00", "workouts": [], "sets": [],
                           "adherence": {"anchor": None, "days": [
                               {"date": "2026-01-01", "expected": "Upper A",
                                "trained": None, "status": "sometimes"}],
                               "drift": False, "drift_days": 0, "drift_threshold": 3}})


def test_first_error_reports_location():
    from pydantic import ValidationError as _VE
    from reps.models import first_error
    try:
        ConstantsModel.model_validate({"muscles": {}, "rep_bands": [], "thresholds": {}})
    except _VE as e:
        assert first_error(e).startswith("muscles:")
    else:
        raise AssertionError("expected ValidationError")
