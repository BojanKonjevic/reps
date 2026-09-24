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


def test_constants_and_snapshot_through_mcp(log_module):
    assert call("constants_validate", {})["ok"] is True
    chest = call("constants_show", {"key": "muscles.chest"})
    assert chest["ok"] is True and chest["data"]["mev"] == 8
    snap = call("snapshot_export", {})
    assert snap["ok"] is True and "sessions" in snap["data"]
    from reps.models import SnapshotModel
    SnapshotModel.model_validate(snap["data"])
