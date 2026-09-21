#!/usr/bin/env python3
"""Phase 3: splits, movement notes, and rules live in SQLite with CLI writers."""

import io
import json
from contextlib import redirect_stdout

import pytest
from conftest import close_session, seed_split


def _out(fn, *args):
    buf = io.StringIO()
    with redirect_stdout(buf):
        fn(*args)
    return buf.getvalue()


def _seeded(log):
    log.cmd_start("test")
    log.cmd_log("bench", 100, 5, "", "chest")
    log.cmd_log("row", 90, 8, "", "back")
    log.cmd_retag("squat", "quads,glutes")
    seed_split(log, "Upper A", ("bench", 3), ("row", 2))
    seed_split(log, "Lower A", ("squat", 3))


def test_split_show_and_set(log_module):
    log = log_module
    _seeded(log)
    out = _out(log.cmd_split_show, "Upper A", "active")
    assert "1. bench x3" in out and "2. row x2" in out
    rows = log.read_split("active", "Upper A")
    assert [(r["slot"], r["movements"], r["sets"]) for r in rows] == [(1, "bench", 3), (2, "row", 2)]
    log.cmd_retag("pulldown", "back")
    log.cmd_split_set("Upper A", 2, "row / pulldown", 3)
    assert log.read_split("active", "Upper A")[1] == {"day": "Upper A", "slot": 2,
                                                     "movements": "row / pulldown", "sets": 3}


def test_split_set_rejects_unmapped(log_module):
    log = log_module
    with pytest.raises(SystemExit, match="no mapping"):
        log.cmd_split_set("Upper A", 1, "mystery press", 3)


def test_split_move_reorders(log_module):
    log = log_module
    _seeded(log)
    log.cmd_retag("fly", "chest")
    log.cmd_split_set("Upper A", 3, "fly", 2)
    log.cmd_split_move("Upper A", "fly", 1)
    rows = log.read_split("active", "Upper A")
    assert [(r["slot"], r["movements"]) for r in rows] == [(1, "fly"), (2, "bench"), (3, "row")]


def test_split_reconcile_appends_new(log_module):
    log = log_module
    _seeded(log)
    log.cmd_log("fly", 20, 10, "", "chest")
    log.cmd_split_reconcile("Upper A")
    rows = log.read_split("active", "Upper A")
    assert rows[-1] == {"day": "Upper A", "slot": 3, "movements": "fly", "sets": 2}


def test_split_diff_and_revert(log_module):
    log = log_module
    _seeded(log)
    c = log.conn()
    for r in log.read_split("active"):
        c.execute("INSERT INTO splits (variant, day, slot, movements, sets) VALUES ('baseline', ?, ?, ?, ?)",
                  (r["day"], r["slot"], r["movements"], r["sets"]))
    c.commit()
    log.cmd_split_set("Upper A", 1, "bench", 5)
    diff = _out(log.cmd_split_diff)
    assert "Upper A" in diff and "baseline" in diff
    log.cmd_split_revert("Upper A")
    assert log.read_split("active", "Upper A")[0]["sets"] == 3


def test_map_show_set_note(log_module):
    log = log_module
    log.cmd_retag("bench", "chest,front delts")
    shown = json.loads(_out(log.cmd_map_show, "bench"))
    assert shown["muscles"] == "chest,front delts"
    log.cmd_map_note("bench", "paused reps")
    assert json.loads(_out(log.cmd_map_show, "bench"))["notes"] == ["paused reps"]
    log.cmd_retag("dip", "triceps", True)
    assert json.loads(_out(log.cmd_map_show, "dip"))["is_bodyweight_only"] == 1


def test_rule_lifecycle(log_module):
    log = log_module
    buf = io.StringIO()
    with redirect_stdout(buf):
        log.cmd_rule_add("straps always", "straps/grip", None)
    assert json.loads(buf.getvalue())["rule_id"] == 1
    rows = json.loads(_out(log.cmd_rule_list, None))
    assert rows[0]["needs_confirm"] is False
    log.cmd_rule_confirm(1, "2026-09-21", False)
    rows = json.loads(_out(log.cmd_rule_list, 7))
    assert rows[0]["expiry"] == "2026-09-21" and rows[0]["needs_confirm"] is True
    log.cmd_rule_confirm(1, None, True)
    assert json.loads(_out(log.cmd_rule_list, None)) == []


def test_gate_blocks_unreconciled(log_module):
    log = log_module
    _seeded(log)
    log.cmd_log("fly", 20, 10, "", "chest")
    for ex in ("bench", "row", "fly"):
        log.cmd_progression_set(ex, "hold", "test", "flat")
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            log.cmd_end("done")
        assert False, "should have exited"
    except SystemExit as e:
        assert e.code == 1
    assert "unreconciled slot: fly" in buf.getvalue()
    assert "split reconcile" in buf.getvalue()
    log.cmd_split_reconcile("Upper A")
    buf = io.StringIO()
    with redirect_stdout(buf):
        log.cmd_end("done")
    assert json.loads(buf.getvalue())["sets"] == 3


def test_plan_split_section(log_module):
    log = log_module
    _seeded(log)
    log.cmd_map_note("bench", "paused reps")
    log.cmd_progression_set("bench", "hit", "102.5x5", "up")
    buf = io.StringIO()
    with redirect_stdout(buf):
        log.cmd_plan("Upper A", False)
    split = json.loads(buf.getvalue())["split"]
    assert split["day"] == "Upper A"
    bench = split["slots"][0]
    assert bench["movements"] == ["bench"] and bench["sets"] == 3
    assert bench["progression"]["bench"]["next"] == "102.5x5"
    assert bench["notes"] == ["paused reps"]
    assert bench["muscles"] == ["chest"]
    assert bench["goal"] is None
