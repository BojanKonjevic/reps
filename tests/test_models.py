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


def test_load_constants_returns_canonical_model():
    from reps.constants import load_constants
    model = load_constants()
    assert isinstance(model, ConstantsModel)
    assert model.muscles["chest"].mev == 8
    assert model.thresholds.volume_window_weeks == 8
    assert model.rep_bands[0].max_reps == 6
    assert model.explained_keywords[:2] == ["deload", "return"]


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


def test_validate_constants_fails_loudly():
    from reps.constants import validate_constants
    from reps.errors import RepsError
    with pytest.raises(RepsError, match="constants invalid"):
        validate_constants({"muscles": {}}, "test-source")


def test_snapshot_validates_built_payload(log_module):
    snap = log_module.build_snapshot_validated()
    assert snap["schema_version"] == 2
    assert isinstance(snap["sessions"], list)
    assert isinstance(snap["lifts"], list)


def test_snapshot_rejects_missing_exported():
    with pytest.raises(SnapshotValidationError):
        validate_snapshot({"schema_version": 2})


def test_snapshot_rejects_string_weight(log_module):
    from conftest import close_session
    log_module.set_exercise_mapping("bench", "chest")
    log_module.start_workout("test")
    log_module.log_set("bench", 100, 5, "", "chest")
    close_session(log_module, "done")
    snap = log_module.build_snapshot_validated()
    assert snap["lifts"], "seeded lift must exist for the string-weight probe"
    bad = json.loads(json.dumps(snap))
    bad["lifts"][0]["sessions"][0]["weight"] = "heavy"
    with pytest.raises(SnapshotValidationError):
        validate_snapshot(bad)


def test_snapshot_rejects_unknown_sections(log_module):
    """No silent tolerance: unknown sections fail loudly (extra=forbid)."""
    snap = log_module.build_snapshot_validated()
    snap["future_section"] = {"anything": [1, 2, 3]}
    with pytest.raises(SnapshotValidationError):
        validate_snapshot(snap)


def test_snapshot_rejects_partial_payload():
    with pytest.raises(SnapshotValidationError):
        validate_snapshot({"schema_version": 2, "exported": "2026-01-01T00:00:00"})


def test_snapshot_muscle_entry_shape(log_module):
    log = log_module
    log.set_exercise_mapping("bench", "chest")
    log.set_split("Upper A", 1, "bench", 5)
    snap = log.build_snapshot_validated()
    chest = next(m for m in snap["muscles"] if m["muscle"] == "chest")
    assert set(chest) == {"muscle", "bands", "weekly", "status", "tier",
                          "grouped", "lift_share", "trained_weeks", "avg_recent"}
    assert set(chest["bands"]) == {"mev", "mav", "mrv"}
    SnapshotModel.model_validate(snap)


def test_snapshot_rejects_bad_calendar_kind(log_module):
    snap = log_module.build_snapshot_validated()
    snap["calendar"] = [dict(d, kind="whenever") for d in snap["calendar"]] or [
        {"date": "2026-01-01", "kind": "whenever", "slot_label": None, "has_pr": False,
         "break_after_gap": False, "adherence_status": None, "expected": None,
         "hover": {"lines": []}}]
    with pytest.raises(SnapshotValidationError):
        validate_snapshot(snap)


def test_snapshot_rejects_bad_adherence_status(log_module):
    snap = log_module.build_snapshot_validated()
    snap["adherence"] = {"anchor": None, "days": [
        {"date": "2026-01-01", "expected": "Upper A",
         "trained": None, "status": "sometimes"}],
        "drift": False, "drift_days": 0, "drift_threshold": 3, "weeks": []}
    with pytest.raises(SnapshotValidationError):
        validate_snapshot(snap)


def test_first_error_reports_location():
    from pydantic import ValidationError as _VE
    from reps.models import first_error
    try:
        ConstantsModel.model_validate({"muscles": {}, "rep_bands": [], "thresholds": {}})
    except _VE as e:
        assert first_error(e).startswith("muscles:")
    else:
        raise AssertionError("expected ValidationError")


def test_snapshot_models_goal_and_rule_sections(log_module):
    log = log_module
    log.set_exercise_mapping("bench", "chest")
    log.set_split("Upper A", 1, "bench", 3)
    log.start_workout("test")
    log.log_set("bench", 100, 5, "", "chest")
    from datetime import date, timedelta
    from conftest import close_session
    close_session(log, "done")
    deadline = (date.today() + timedelta(days=60)).isoformat()
    log.add_goal("bench", 130, deadline, "", 116.7)
    log.add_rule("test rule", "test", None)
    log.add_flag("bench", "watch")
    snap = log.build_snapshot_validated()
    model = SnapshotModel.model_validate(snap)
    assert model.goals[0].exercise == "bench"
    assert model.goals[0].checkpoints
    assert model.goals[0].percent == 0.0
    assert model.rules[0].text == "test rule"
    assert model.flags[0].subject == "bench"
    assert next(l for l in model.lifts if l.exercise == "bench").goal_id == model.goals[0].id


def test_snapshot_rejects_bad_lift_tag(log_module):
    snap = log_module.build_snapshot_validated()
    if not snap["lifts"]:
        log_module.set_exercise_mapping("bench", "chest")
        log_module.start_workout("t")
        log_module.log_set("bench", 100, 5, "", "chest")
        from conftest import close_session
        close_session(log_module, "done")
        snap = log_module.build_snapshot_validated()
    snap["lifts"][0]["tags"] = ["flying"]
    snap["lifts"][0]["marks"] = [{"kind": "flying", "payload": {}}]
    with pytest.raises(SnapshotValidationError):
        validate_snapshot(snap)
