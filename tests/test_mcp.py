#!/usr/bin/env python3
"""MCP tools tested through the MCP interface (list + call on the server)."""

import asyncio
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

pytestmark = pytest.mark.skipif(
    os.environ.get("REPS_NO_MCP") == "1", reason="mcp dependency unavailable")


def call(name, args=None):
    from reps.mcp.server import call_tool
    return asyncio.run(call_tool(name, args or {}))


def test_tool_surface_is_domain_shaped(log_module):
    from reps.mcp.server import list_tool_names
    names = set(asyncio.run(list_tool_names()))
    for expected in ("session_start", "session_log_set", "session_end", "session_today",
                     "session_history", "plan", "progression_set", "goal_add",
                     "program_split_show", "program_rotation_status", "autoreg_apply",
                     "constants_show", "snapshot_export", "sync_push", "audit_data",
                     "muscle_map_set"):
        assert expected in names, f"missing tool {expected}"
    assert not any("cmd_" in n or n in ("main", "usage") for n in names), \
        "tools are domain operations, not CLI command wrappers"


def test_session_lifecycle_through_mcp(log_module):
    log = log_module
    assert call("session_start", {"note": "mcp test"})["ok"] is True
    logged = call("session_log_set", {"exercise": "bench", "weight": 80, "reps": 5,
                                      "muscles": "chest"})
    assert logged["ok"] is True
    assert logged["data"]["set_id"] >= 1
    today = call("session_today", {})
    assert today["ok"] is True and today["data"]["open"] is True
    hist = call("session_history", {"exercise": "bench"})
    assert hist["ok"] is True and hist["data"][0]["exercise"] == "bench"
    assert call("progression_set", {"exercise": "bench", "verdict": "baseline",
                                   "next_weight": 82.5, "next_reps": 5, "direction": "flat"})["ok"] is True
    log.set_split("Upper A", 1, "bench", 5)
    assert call("program_split_reconcile", {"day": "Upper A"})["ok"] is True
    ended = call("session_end", {"note": "mcp done"})
    assert ended["ok"] is True


def test_refusals_surface_as_errors(log_module):
    log = log_module
    bad = call("session_log_set", {"exercise": "bench", "weight": 80, "reps": 5})
    assert bad["ok"] is False, "log with no open workout must refuse, not invent one"
    assert "no open workout" in bad["error"]
    assert call("session_delete_set", {"set_id": 999999})["ok"] is False
    missing = call("progression_set", {"exercise": "bench", "verdict": "hit",
                                       "next_weight": 82.5, "next_reps": 5, "direction": "up"})
    assert missing["ok"] is False
    assert "no open workout" in missing["error"]


def test_closed_vocabularies_reject_at_the_schema(log_module):
    """Finite domain vocabularies are enforced by tool schemas, before domain logic runs."""
    import pytest
    with pytest.raises(Exception, match="verdict"):
        call("progression_set", {"exercise": "bench", "verdict": "smashed",
                                 "next_weight": 82.5, "next_reps": 5, "direction": "up"})
    with pytest.raises(Exception, match="direction"):
        call("progression_set", {"exercise": "bench", "verdict": "hit",
                                 "next_weight": 82.5, "next_reps": 5, "direction": "sideways"})
    with pytest.raises(Exception, match="tier"):
        call("program_priority_set", {"muscle": "chest", "tier": "urgent"})
    with pytest.raises(Exception, match="scope"):
        call("program_deload_set", {"scope": "planet", "subject": "bench"})


def test_read_tools_share_domain_logic(log_module):
    log = log_module
    log.start_workout("read check")
    log.log_set("bench", 80, 5, "", "chest", False)
    assert call("session_exercises", {})["data"] == ["bench"]
    assert call("muscle_map_show", {"exercise": "bench"})["ok"] is True
    assert call("program_split_show", {})["ok"] is True
    plan = call("plan", {})
    assert plan["ok"] is True and "lifts" in json.dumps(plan["data"])
    assert call("session_stats", {})["ok"] is True
    assert call("session_calendar", {})["ok"] is True


def test_program_tools_through_mcp(log_module):
    log = log_module
    assert call("program_priority_set", {"muscle": "chest", "tier": "priority"})["ok"] is True
    assert call("program_priority_list", {})["ok"] is True
    assert call("program_priority_clear", {"muscle": "chest"})["ok"] is True
    assert call("program_rule_add", {"text": "mcp rule", "subject": "test"})["ok"] is True
    rules = call("program_rule_list", {})
    assert rules["ok"] is True
    rid = rules["data"]["rules"][-1]["id"] if isinstance(rules["data"], dict) else rules["data"][-1]["id"]
    assert call("program_rule_confirm", {"rule_id": rid, "archive": True})["ok"] is True
    assert call("program_flag_add", {"subject": "bench", "reason": "mcp"})["ok"] is True
    assert call("program_flag_list", {})["ok"] is True
    log.set_exercise_mapping("bench", "chest")
    log.set_split("Upper A", 1, "bench", 3)
    assert call("program_rotation_set", {"days": ["Upper A", "rest"]})["ok"] is True
    assert call("program_rotation_show", {})["ok"] is True
    assert call("program_compaction_set", {"postponed_until": "2026-12-01"})["ok"] is True
    assert call("program_compaction_show", {})["ok"] is True
    assert call("program_rotation_anchor", {"date": "2026-09-01", "day": "Upper A"})["ok"] is True
    assert call("program_rotation_status", {})["ok"] is True


def test_history_and_observe_through_mcp(log_module):
    log = log_module
    log.start_workout("history mcp")
    log.log_set("bench", 80, 5, "", "chest", False)
    assert call("program_split_set", {"day": "Upper A", "slot": 1, "movements": "bench",
                                      "sets": 3, "evidence": "mcp"})["ok"] is True
    listed = call("history_list", {"domain": "program", "subject": "active:Upper A"})
    assert listed["ok"] is True and len(listed["data"]) == 1
    cid = listed["data"][0]["id"]
    assert listed["data"][0]["evidence"] == "mcp"
    assert call("history_get", {"change_id": cid})["ok"] is True
    state = call("history_state", {"domain": "program", "subject": "active:Upper A"})
    assert state["ok"] is True and state["data"]["reconstructible"] is True
    assert call("history_revert", {"change_id": cid, "evidence": "mcp undo"})["ok"] is True
    assert call("history_revert", {"change_id": cid})["ok"] is False
    obs = call("observe", {"metric": "muscle_volume", "subject": "chest"})
    assert obs["ok"] is True and "provenance" in obs["data"]
    assert call("observe", {"metric": "lift_trend"})["ok"] is False


def test_history_vocabularies_reject_at_the_schema(log_module):
    import pytest
    with pytest.raises(Exception, match="domain"):
        call("history_list", {"domain": "autoreg"})
    with pytest.raises(Exception, match="metric"):
        call("observe", {"metric": "vibes"})


def test_constants_and_snapshot_through_mcp(log_module):
    assert call("constants_validate", {})["ok"] is True
    chest = call("constants_show", {"key": "muscles.chest"})
    assert chest["ok"] is True and chest["data"]["mev"] == 8
    snap = call("snapshot_export", {})
    assert snap["ok"] is True and "sessions" in snap["data"]
    from reps.models import SnapshotModel
    SnapshotModel.model_validate(snap["data"])


def test_destructive_paths_through_mcp(log_module):
    """Every destructive tool is reachable via call_tool and refuses cleanly."""
    log = log_module
    log.start_workout("destructive mcp")
    logged = call("session_log_set", {"exercise": "bench", "weight": 80, "reps": 5,
                                      "muscles": "chest"})
    assert logged["ok"] is True
    sid = logged["data"]["set_id"]
    # Update + delete set round-trip through MCP.
    assert call("session_update_set", {"set_id": sid, "field": "note",
                                       "value": "mcp note"})["ok"] is True
    assert call("session_update_set", {"set_id": sid, "field": "weight",
                                       "value": "nan"})["ok"] is False
    assert call("session_delete_set", {"set_id": sid})["ok"] is True
    assert call("session_delete_set", {"set_id": sid})["ok"] is False
    assert call("session_update_set", {"set_id": 999999, "field": "note",
                                       "value": "x"})["ok"] is False
    # Rest/weigh/get/range/notes/prs/context read paths through MCP.
    assert call("session_weigh", {"kg": 80})["ok"] is True
    assert call("session_get", {"day": "2026-09-27"})["ok"] is True
    assert call("session_range", {"from_date": "2026-09-01",
                                  "to_date": "2026-09-27"})["ok"] is True
    assert call("session_notes", {})["ok"] is True
    assert call("session_context", {})["ok"] is True
    assert call("muscle_map_note", {"exercise": "bench",
                                    "text": "mcp note"})["ok"] is True
    assert call("muscle_rename", {"old": "bench", "new": "bench"})["ok"] is False
    log.set_exercise_mapping("press", "chest,triceps")
    assert call("muscle_merge", {"old": "press", "new": "bench"})["ok"] is False
    assert call("program_split_move", {"day": "Upper A", "exercise": "bench",
                                       "to_slot": 1})["ok"] is False
    assert call("program_split_diff", {})["ok"] is True
    assert call("program_split_revert", {"day": "Nope"})["ok"] is False
    assert call("program_deload_clear", {})["ok"] is True
    assert call("program_flag_consume", {"flag_id": 999999})["ok"] is False
    assert call("progression_show", {})["ok"] is True
    assert call("goal_show", {})["ok"] is True
    assert call("goal_show", {"goal_id": 999999})["ok"] is False
    log.set_exercise_mapping("squat", "quads,glutes")
    log.set_split("Lower A", 1, "squat", 3)
    g = call("goal_add", {"exercise": "squat", "target_e1rm": 150,
                          "deadline": "2027-06-01", "desc": "mcp",
                          "start_e1rm": 100.0})
    assert g["ok"] is True
    gid = g["data"]["goal_id"]
    assert call("goal_show", {"goal_id": gid})["ok"] is True
    assert call("goal_rewrite", {"goal_id": gid})["ok"] is True
    assert call("goal_drop", {"goal_id": gid})["ok"] is True
    assert call("goal_drop", {"goal_id": gid})["ok"] is False
    assert call("autoreg_log", {})["ok"] is True
    assert call("autoreg_revert", {"change_id": 999999})["ok"] is False
    assert call("doctor", {})["ok"] is True
    assert call("constants_set", {"key": "thresholds.trend_top_lifts",
                                  "value": "8"})["ok"] is True
    assert call("constants_set", {"key": "thresholds.trend_top_lifts",
                                  "value": '"eight"'})["ok"] is False
    assert call("maintenance_dump", {})["ok"] is True
    assert call("maintenance_restore", {})["ok"] is False  # open workout refuses


def test_mcp_result_contract_has_no_output_branch(log_module):
    """Handlers return data/error only; the output shape is legacy transport text."""
    log = log_module
    log.start_workout("contract")
    ok = call("session_today", {})
    assert ok["ok"] is True and "data" in ok and "output" not in ok
    bad = call("session_log_set", {"exercise": "bench", "weight": 80, "reps": 5})
    # No open-workout mapping yet in this path? bench is unmapped without muscles.
    assert bad["ok"] is False and "error" in bad
