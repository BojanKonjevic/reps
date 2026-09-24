#!/usr/bin/env python3
"""Phase 3: splits, movement notes, and rules live in SQLite with domain writers."""

import pytest
from conftest import close_session, seed_split
from reps.errors import RepsError


def _seeded(log):
    log.start_workout("test")
    log.log_set("bench", 100, 5, "", "chest")
    log.log_set("row", 90, 8, "", "back")
    log.set_exercise_mapping("squat", "quads,glutes")
    seed_split(log, "Upper A", ("bench", 3), ("row", 2))
    seed_split(log, "Lower A", ("squat", 3))


def test_split_show_and_set(log_module):
    log = log_module
    _seeded(log)
    shown = log.get_split("Upper A", "active")
    assert shown["variant"] == "active"
    assert [(r["slot"], r["movements"], r["sets"]) for r in shown["days"][0]["slots"]] == [
        (1, "bench", 3), (2, "row", 2)]
    rows = log.read_split("active", "Upper A")
    assert [(r["slot"], r["movements"], r["sets"]) for r in rows] == [(1, "bench", 3), (2, "row", 2)]
    log.set_exercise_mapping("pulldown", "back")
    log.set_split("Upper A", 2, "row / pulldown", 3)
    assert log.read_split("active", "Upper A")[1] == {"day": "Upper A", "slot": 2,
                                                     "movements": "row / pulldown", "sets": 3}


def test_split_set_rejects_unmapped(log_module):
    log = log_module
    with pytest.raises(RepsError, match="not a known lift"):
        log.set_split("Upper A", 1, "mystery press", 3)


def test_split_move_reorders(log_module):
    log = log_module
    _seeded(log)
    log.set_exercise_mapping("fly", "chest")
    log.set_split("Upper A", 3, "fly", 2)
    log.move_split("Upper A", "fly", 1)
    rows = log.read_split("active", "Upper A")
    assert [(r["slot"], r["movements"]) for r in rows] == [(1, "fly"), (2, "bench"), (3, "row")]


def test_split_reconcile_appends_new(log_module):
    log = log_module
    _seeded(log)
    log.log_set("fly", 20, 10, "", "chest")
    log.reconcile_split("Upper A")
    rows = log.read_split("active", "Upper A")
    assert rows[-1] == {"day": "Upper A", "slot": 3, "movements": "fly", "sets": 2}


def test_split_diff_and_revert(log_module):
    log = log_module
    _seeded(log)
    c = log.conn()
    for r in log.read_split("active"):
        log.set_split(r["day"], r["slot"], r["movements"], r["sets"], variant="baseline")
    c.commit()
    log.set_split("Upper A", 1, "bench", 5)
    diff = log.diff_split()
    assert diff["matches"] is False
    assert any("Upper A" in line and "baseline" in line for line in diff["lines"])
    log.revert_split("Upper A")
    assert log.read_split("active", "Upper A")[0]["sets"] == 3


def test_map_show_set_note(log_module):
    log = log_module
    log.set_exercise_mapping("bench", "chest,front delts")
    shown = log.get_mapping("bench")
    assert shown["muscles"] == "chest,front delts"
    log.set_movement_note("bench", "paused reps")
    assert log.get_mapping("bench")["notes"] == ["paused reps"]
    log.set_exercise_mapping("dip", "triceps", True)
    assert log.get_mapping("dip")["is_bodyweight_only"] == 1


def test_rule_lifecycle(log_module):
    log = log_module
    assert log.add_rule("straps always", "straps/grip", None)["rule_id"] == 1
    rows = log.list_rules(None)
    assert rows[0]["needs_confirm"] is False
    log.confirm_rule(1, "2026-09-21", False)
    rows = log.list_rules(7)
    assert rows[0]["expiry"] == "2026-09-21" and rows[0]["needs_confirm"] is True
    log.confirm_rule(1, None, True)
    assert log.list_rules(None) == []


def test_gate_blocks_unreconciled(log_module):
    log = log_module
    _seeded(log)
    log.log_set("fly", 20, 10, "", "chest")
    for ex in ("bench", "row", "fly"):
        log.set_progression(ex, "hold", 80, 5, "flat")
    try:
        log.end_workout("done")
        assert False, "should have refused"
    except RepsError as e:
        assert "unreconciled slot: fly" in str(e)
        assert "program_split_reconcile" in str(e)
    log.reconcile_split("Upper A")
    assert log.end_workout("done")["sets"] == 3


def test_plan_split_section(log_module):
    log = log_module
    _seeded(log)
    log.set_movement_note("bench", "paused reps")
    log.set_progression("bench", "hit", 102.5, 5, "up")
    split = log.get_plan("Upper A", False)["split"]
    assert split["day"] == "Upper A"
    bench = split["slots"][0]
    assert bench["movements"] == ["bench"] and bench["sets"] == 3
    assert bench["progression"]["bench"]["next"] == "102.5x5"
    assert bench["notes"] == ["paused reps"]
    assert bench["muscles"] == ["chest"]
    assert bench["goal"] is None


def test_compaction_never_clears(log_module):
    log = log_module
    log.set_compaction(last_compacted="Oct 1 2026")
    assert log.get_compaction()["last_compacted"] == "Oct 1 2026"
    log.set_compaction(last_compacted="never")
    assert log.get_compaction()["last_compacted"] is None


def test_reconcile_two_new_lifts_after_middle_slot(log_module):
    log = log_module
    log.set_exercise_mapping("bench", "chest")
    log.set_exercise_mapping("row", "back")
    log.set_exercise_mapping("press", "chest")
    log.set_exercise_mapping("curl", "biceps")
    log.set_split("Upper A", 1, "bench", 3)
    log.set_split("Upper A", 2, "row", 3)
    log.start_workout("test")
    log.log_set("bench", 100, 5, "", "chest")
    log.log_set("press", 60, 8, "", "chest")
    log.log_set("curl", 30, 10, "", "biceps")
    out = log.reconcile_split("Upper A", after="bench")
    assert out["added"] == ["press", "curl"]
    rows = log.read_split("active", "Upper A")
    assert [(r["slot"], r["movements"]) for r in rows] == [
        (1, "bench"), (2, "press"), (3, "curl"), (4, "row")]


def test_progression_zero_target_bodyweight_only(log_module):
    log = log_module
    log.start_workout("test")
    log.log_set("pullup", 0, 8, "", "back,biceps", True)
    out = log.set_progression("pullup", "baseline", 0, 10, "flat")
    assert out["next"] == "0x10"
    log.log_set("bench", 100, 5, "", "chest")
    import pytest
    with pytest.raises(Exception, match="cannot be zero"):
        log.set_progression("bench", "baseline", 0, 5, "flat")
