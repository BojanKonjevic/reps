#!/usr/bin/env python3
"""Shared state-change history: record, list, reconstruct, revert (append-only)."""

from datetime import date

import pytest

from reps.errors import RepsError
from conftest import close_session


def _seeded(log):
    log.start_workout("test")
    log.log_set("bench", 100, 5, "", "chest")
    log.set_split("Upper A", 1, "bench", 3)
    close_session(log, "baseline")


def test_program_edit_records_before_after(log_module):
    log = log_module
    _seeded(log)
    out = log.set_split("Upper A", 1, "bench", 5, evidence="elbow nudge")
    rows = log.list_changes("program", "active:Upper A")
    assert len(rows) == 2
    first, second = rows
    assert first["before"] == {"variant": "active", "day": "Upper A", "slots": []}
    assert first["after"] == {"variant": "active", "day": "Upper A", "slots": [
        {"slot": 1, "movements": "bench", "sets": 3}]}
    assert second["before"]["slots"] == [{"slot": 1, "movements": "bench", "sets": 3}]
    assert second["after"]["slots"] == [{"slot": 1, "movements": "bench", "sets": 5}]
    assert second["evidence"] == "elbow nudge"
    assert second["id"] == out["change_id"]
    assert second["reverses"] is None and second["superseded_by"] is None


def test_history_get_round_trips_payload(log_module):
    log = log_module
    _seeded(log)
    cid = log.set_priority("chest", "priority", evidence="bring up")["change_id"]
    entry = log.get_change(cid)
    assert entry["domain"] == "priority" and entry["subject"] == "chest"
    assert entry["before"] == {"tier": None, "since": None, "until": None}
    assert entry["after"]["tier"] == "priority"
    assert entry["evidence"] == "bring up"


def test_goal_rewrite_records_trajectory(log_module):
    from datetime import timedelta

    log = log_module
    _seeded(log)
    deadline = (date.today() + timedelta(days=60)).isoformat()
    log.add_goal("bench", 130, deadline, "", None)
    rows = log.list_changes("goal", "bench")
    assert len(rows) == 1
    assert rows[0]["before"]["checkpoints"] is None
    assert rows[0]["after"]["checkpoints"][0] == 116.7
    assert rows[0]["after"]["checkpoints"][-1] == 130.0
    assert rows[0]["after"]["status"] == "active"


def test_revert_restores_program_and_preserves_original(log_module):
    log = log_module
    _seeded(log)
    second = log.set_split("Upper A", 1, "bench", 5)["change_id"]
    original = log.get_change(second)
    out = log.revert_change(second, "too much")
    assert out["reverses"] == second
    day = log.get_split("Upper A")["days"][0]["slots"]
    assert day[0]["sets"] == 3
    assert log.get_change(second)["before"] == original["before"]
    assert log.get_change(second)["after"] == original["after"]
    assert log.get_change(second)["superseded_by"] == out["change_id"]
    tip = log.get_change(out["change_id"])
    assert tip["reverses"] == second and tip["evidence"] == "too much"
    assert tip["after"]["slots"] == [{"slot": 1, "movements": "bench", "sets": 3}]


def test_revert_refuses_superseded_change(log_module):
    log = log_module
    _seeded(log)
    second = log.set_split("Upper A", 1, "bench", 5)["change_id"]
    log.revert_change(second)
    with pytest.raises(RepsError, match="already superseded"):
        log.revert_change(second)


def test_revert_priority_restores_tier(log_module):
    log = log_module
    _seeded(log)
    cid = log.set_priority("chest", "priority")["change_id"]
    log.revert_change(cid)
    assert log.list_priorities() == []
    tip = log.list_changes("priority", "chest")[-1]
    assert tip["after"] == {"tier": None, "since": None, "until": None}


def test_same_day_changes_order_by_sequence(log_module):
    log = log_module
    _seeded(log)
    first = log.set_priority("chest", "priority")["change_id"]
    second = log.set_priority("chest", "deprioritize")["change_id"]
    rows = log.list_changes("priority", "chest")
    assert [r["id"] for r in rows] == [first, second]
    assert [r["sequence"] for r in rows] == [0, 1]


def test_state_at_scopes_successive_goals(log_module):
    from datetime import timedelta

    log = log_module
    _seeded(log)
    deadline = (date.today() + timedelta(days=60)).isoformat()
    gid1 = log.add_goal("bench", 130, deadline, "", None)["goal_id"]
    drop_cid = log.drop_goal(gid1)["change_id"]
    add_cid = log.list_changes("goal", "bench")[0]["id"]
    gid2 = log.add_goal("bench", 140, deadline, "", None)["goal_id"]
    c = log.conn()
    back = (date.today() - timedelta(days=10)).isoformat()
    c.execute("UPDATE state_change SET date = ? WHERE id IN (?, ?)", (back, add_cid, drop_cid))
    c.commit()
    mid = (date.today() - timedelta(days=5)).isoformat()
    assert log.state_at("goal", "bench", mid)["state"]["goal_id"] == gid1
    assert log.state_at("goal", "bench", mid)["state"]["status"] == "dropped"
    tip = log.state_at("goal", "bench", date.today().isoformat())
    assert tip["state"]["goal_id"] == gid2
    assert tip["state"]["status"] == "active"


def test_goal_drop_refuses_double_drop(log_module):
    from datetime import timedelta

    log = log_module
    _seeded(log)
    deadline = (date.today() + timedelta(days=60)).isoformat()
    gid = log.add_goal("bench", 130, deadline, "", None)["goal_id"]
    log.drop_goal(gid)
    with pytest.raises(RepsError, match="already dropped"):
        log.drop_goal(gid)
    assert len(log.list_changes("goal", "bench")) == 2


def test_rotation_revert_round_trip(log_module):
    log = log_module
    _seeded(log)
    log.set_rotation(["Upper A", "rest"])
    cid = log.list_changes("rotation", "rotation")[-1]["id"]
    log.set_rotation(["Upper A"])
    with pytest.raises(RepsError, match="moved since this change"):
        log.revert_change(cid)
    tip = log.list_changes("rotation", "rotation")[-1]["id"]
    log.revert_change(tip)
    assert log.show_rotation()["rotation"] == ["Upper A", "rest"]


def test_stale_revert_refuses_priority_and_rule(log_module):
    log = log_module
    _seeded(log)
    cid = log.set_priority("chest", "priority")["change_id"]
    log.set_priority("chest", "deprioritize")
    with pytest.raises(RepsError, match="moved since this change"):
        log.revert_change(cid)
    rid = log.add_rule("no grind", "bench")["rule_id"]
    rcid = log.list_changes("rule", str(rid))[-1]["id"]
    log.confirm_rule(rid, archive=True)
    with pytest.raises(RepsError, match="moved since this change"):
        log.revert_change(rcid)


def test_deload_revert_guards(log_module):
    log = log_module
    _seeded(log)
    set_cid = log.set_deload("lift", "bench")["change_id"]
    log.clear_deload()
    with pytest.raises(RepsError, match="no longer active"):
        log.revert_change(set_cid)
    log.set_deload("lift", "bench")
    clear_cid = [ch for ch in log.list_changes("deload", "lift:bench")
                 if ch["after"]["action"] == "clear"][-1]["id"]
    with pytest.raises(RepsError, match="already active"):
        log.revert_change(clear_cid)


def test_state_at_unknown_before_first_record(log_module):
    log = log_module
    _seeded(log)
    ans = log.state_at("program", "active:Upper A", "2020-01-01")
    assert ans["reconstructible"] is False
    assert "reason" in ans


def test_state_at_reconstructs_tip(log_module):
    log = log_module
    _seeded(log)
    log.set_split("Upper A", 1, "bench", 5)
    ans = log.state_at("program", "active:Upper A", date.today().isoformat())
    assert ans["reconstructible"] is True
    assert ans["state"]["slots"] == [{"slot": 1, "movements": "bench", "sets": 5}]


def test_priority_pre_history_is_maintain(log_module):
    log = log_module
    _seeded(log)
    ans = log.state_at("priority", "side_delts", "2020-01-01")
    assert ans["reconstructible"] is True
    assert ans["state"] == {"tier": "maintain", "since": None, "until": None}


def test_history_list_range_and_subject_filter(log_module):
    log = log_module
    _seeded(log)
    log.set_split("Upper A", 1, "bench", 5)
    today = date.today().isoformat()
    assert len(log.list_changes("program", "", "2020-01-01", "2020-06-01")) == 0
    assert len(log.list_changes("program", "", "2020-01-01", today)) == 2
    assert log.list_changes("program", "active:Elsewhere") == []


def test_history_rejects_unknown_domain_and_bad_id(log_module):
    log = log_module
    _seeded(log)
    with pytest.raises(RepsError, match="domain must be"):
        log.list_changes("autoreg")
    with pytest.raises(RepsError, match="no such change"):
        log.get_change(999999)
    with pytest.raises(RepsError, match="no such change"):
        log.revert_change("nope")


def test_rotation_and_rule_recorded(log_module):
    log = log_module
    _seeded(log)
    log.set_rotation(["Upper A", "rest"])
    rid = log.add_rule("no grind", "bench")["rule_id"]
    assert log.list_changes("rotation", "rotation")[0]["after"] == {
        "rotation": ["Upper A", None]}
    rule_rows = log.list_changes("rule", str(rid))
    assert rule_rows[0]["after"]["status"] == "active"
    log.confirm_rule(rid, archive=True)
    assert log.list_changes("rule", str(rid))[-1]["after"]["status"] == "archived"
