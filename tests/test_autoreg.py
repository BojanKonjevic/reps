#!/usr/bin/env python3
"""Autoreg code enforcement: plan signals, MEV floor, apply/log/revert."""

import io
import json
from contextlib import redirect_stdout
from datetime import date, timedelta

import pytest


def _out(fn, *args):
    buf = io.StringIO()
    with redirect_stdout(buf):
        fn(*args)
    return buf.getvalue()


def _plan(log, *args):
    buf = io.StringIO()
    with redirect_stdout(buf):
        if args:
            log.cmd_plan(*args)
        else:
            log.cmd_plan()
    return buf.getvalue()


def _done_workout(c, day, sets):
    """Insert a done workout plus sets directly. sets: [(exercise, weight, reps)]."""
    cur = c.execute("INSERT INTO workouts (date, status, notes) VALUES (?, 'done', '')", (day,))
    wid = cur.lastrowid
    for ex, w, r in sets:
        c.execute("INSERT INTO sets (workout_id, exercise, weight, reps, note, created) "
                  "VALUES (?, ?, ?, ?, '', datetime('now'))", (wid, ex, w, r))
    c.commit()
    return wid


def _judge(c, wid, exercise, verdict):
    c.execute("INSERT INTO progression (workout_id, exercise, verdict, next_target, direction, note, created) "
              "VALUES (?, ?, ?, '80x5', 'flat', '', datetime('now'))", (wid, exercise, verdict))
    c.commit()


def test_plan_autoreg_block_and_permission_flip(log_module):
    log = log_module
    bundle = json.loads(_plan(log))
    assert set(bundle["autoreg"]) == {"permitted", "holds", "miss_streaks", "drop_watch",
                                      "grouped", "program_volume"}
    assert bundle["autoreg"]["permitted"] is False
    assert bundle["autoreg"]["holds"] == []
    assert bundle["autoreg"]["miss_streaks"] == []
    assert bundle["autoreg"]["drop_watch"] == []
    assert bundle["autoreg"]["grouped"] == {}
    assert len(bundle["autoreg"]["program_volume"]) == 13
    log.cmd_rule_add("autoreg: manage volume within MEV..MRV", "autoreg", None)
    assert json.loads(_plan(log))["autoreg"]["permitted"] is True


def test_programmed_volume_scales_rotation_to_week(log_module):
    log = log_module
    log.cmd_retag("bench", "chest")
    log.cmd_retag("squat", "quads")
    log.cmd_split_set("Upper A", 1, "bench", 3)
    log.cmd_split_set("Lower A", 1, "squat", 2)
    log.cmd_meta_set("rotation", json.dumps(["Upper A", "Lower A", "rest"]))
    vol = json.loads(_plan(log))["autoreg"]["program_volume"]
    assert vol["chest"] == round(3 * 7.0 / 3, 1)
    assert vol["quads"] == round(2 * 7.0 / 3, 1)
    assert vol["back"] == 0
    assert len(vol) == 13


def test_split_set_mev_warnings_scoped_to_edited_muscles(log_module):
    log = log_module
    log.cmd_retag("bench", "chest")
    out = json.loads(_out(log.cmd_split_set, "Upper A", 1, "bench", 3))
    assert "warnings" in out
    assert any("chest" in w for w in out["warnings"])
    assert not any("quad" in w or "back" in w for w in out["warnings"])
    # MEV 0 muscles never warn.
    log.cmd_retag("ohp", "front delts")
    out = json.loads(_out(log.cmd_split_set, "Upper A", 2, "ohp", 1))
    assert "warnings" not in out


def test_miss_streaks_drop_watch_and_grouped(log_module):
    log = log_module
    c = log.conn()
    log.cmd_retag("bench", "chest")
    log.cmd_retag("incline", "chest")
    days = [(date.today() - timedelta(days=d)).isoformat() for d in (30, 20, 10)]
    wids = [
        _done_workout(c, days[0], [("bench", 100, 5), ("incline", 80, 5)]),
        _done_workout(c, days[1], [("bench", 90, 5), ("incline", 70, 5)]),
        _done_workout(c, days[2], [("bench", 80, 5), ("incline", 60, 5)]),
    ]
    _judge(c, wids[0], "bench", "hit")
    _judge(c, wids[1], "bench", "miss")
    _judge(c, wids[2], "bench", "miss")
    _judge(c, wids[0], "incline", "hit")
    _judge(c, wids[1], "incline", "miss")
    _judge(c, wids[2], "incline", "miss")
    bundle = json.loads(_plan(log))
    auto = bundle["autoreg"]
    assert {m["exercise"]: m["streak"] for m in auto["miss_streaks"]} == {"bench": 2, "incline": 2}
    assert sorted(d["exercise"] for d in auto["drop_watch"]) == ["bench", "incline"]
    assert auto["grouped"] == {"chest": ["bench", "incline"]}
    log.cmd_rule_add("autoreg: manage volume", "autoreg", None)
    verbose = _plan(log, None, True)
    assert "autoreg signals:" in verbose
    assert "2xmiss" in verbose and "dropping" in verbose


def _trim_setup(log):
    log.cmd_rule_add("autoreg: manage volume within MEV..MRV", "autoreg", None)
    log.cmd_retag("bench", "chest")
    log.cmd_retag("incline", "chest")
    log.cmd_split_set("Upper A", 1, "bench", 5)
    log.cmd_split_set("Upper A", 2, "incline", 5)


def test_apply_refuses_without_permission(log_module):
    log = log_module
    log.cmd_retag("bench", "chest")
    log.cmd_split_set("Upper A", 1, "bench", 5)
    with pytest.raises(SystemExit, match="no standing permission"):
        log.cmd_autoreg_apply("Upper A", 1, "bench", 4, "two misses")


def test_apply_trim_records_hold_and_change_then_blocks_held_slot(log_module):
    log = log_module
    _trim_setup(log)
    with pytest.raises(SystemExit, match="--from mismatch"):
        log.cmd_autoreg_apply("Upper A", 1, "bench", 4, "two misses", "incline")
    with pytest.raises(SystemExit, match="no active split slot"):
        log.cmd_autoreg_apply("Upper A", 9, "bench", 4, "two misses")
    out = json.loads(_out(log.cmd_autoreg_apply, "Upper A", 1, "bench", 4, "two misses", "bench"))
    assert out["autoreg"] == "trim"
    assert out["before"] == {"movements": "bench", "sets": 5}
    assert out["after"] == {"movements": "bench", "sets": 4}
    assert out["hold_until"] == (date.today() + timedelta(days=8)).isoformat()
    c = log.conn()
    holds = c.execute("SELECT * FROM autoreg_holds").fetchall()
    assert len(holds) == 1 and holds[0]["hold_until"] == out["hold_until"]
    changes = json.loads(_out(log.cmd_autoreg_log))
    assert len(changes) == 1 and changes[0]["reverted"] is False
    with pytest.raises(SystemExit, match="revert first"):
        log.cmd_autoreg_apply("Upper A", 1, "bench", 3, "still bad")
    reverted = json.loads(_out(log.cmd_autoreg_revert, 1))
    assert reverted["restored"] == {"movements": "bench", "sets": 5}
    assert reverted["holds_cleared"] == 1
    assert c.execute("SELECT COUNT(*) n FROM autoreg_holds").fetchone()["n"] == 0
    assert log.read_split("active", "Upper A")[0] == {"day": "Upper A", "slot": 1,
                                                     "movements": "bench", "sets": 5}
    with pytest.raises(SystemExit, match="already reverted"):
        log.cmd_autoreg_revert(1)


def test_apply_refuses_below_mev_and_unmapped(log_module):
    log = log_module
    _trim_setup(log)
    with pytest.raises(SystemExit, match="no mapping"):
        log.cmd_autoreg_apply("Upper A", 1, "mystery press", 2, "trying a swap")
    with pytest.raises(SystemExit, match="below MEV"):
        log.cmd_autoreg_apply("Upper A", 1, "bench", 1, "deep cut")
    assert log.read_split("active", "Upper A")[0]["sets"] == 5
    assert json.loads(_out(log.cmd_autoreg_log)) == []


def test_revert_of_manually_moved_slot_refuses(log_module):
    log = log_module
    _trim_setup(log)
    json.loads(_out(log.cmd_autoreg_apply, "Upper A", 1, "bench", 4, "two misses"))
    log.cmd_split_set("Upper A", 1, "incline", 4)
    with pytest.raises(SystemExit, match="reconcile manually"):
        log.cmd_autoreg_revert(1)


def test_apply_swap_and_add_classification(log_module):
    log = log_module
    _trim_setup(log)
    swap = json.loads(_out(log.cmd_autoreg_apply, "Upper A", 1, "incline", 5, "strong evidence", "bench"))
    assert swap["autoreg"] == "swap"
    assert swap["hold_until"] is not None
    log.cmd_autoreg_revert(swap["change_id"])
    add = json.loads(_out(log.cmd_autoreg_apply, "Upper A", 1, "bench", 6, "clear recovery", "bench"))
    assert add["autoreg"] == "add"
    assert add["hold_until"] is None
    c = log.conn()
    assert c.execute("SELECT COUNT(*) n FROM autoreg_holds").fetchone()["n"] == 0


def test_autoreg_apply_cli_unquoted(log_module):
    import sys
    log = log_module
    log.cmd_rule_add("autoreg: manage volume", "autoreg", None)
    log.cmd_retag("incline barbell bench press", "chest,front delts")
    log.cmd_retag("flat barbell bench press", "chest,front delts")
    log.cmd_split_set("Upper A", 1, "incline barbell bench press", 5)
    log.cmd_split_set("Upper A", 2, "flat barbell bench press", 5)
    buf = io.StringIO()
    old = sys.argv
    sys.argv = ["log.py", "autoreg", "apply", "--day", "Upper", "A", "--slot", "1",
                "--to", "incline", "barbell", "bench", "press", "4",
                "--evidence", "two", "misses", "--from", "incline", "barbell", "bench", "press"]
    try:
        with redirect_stdout(buf):
            log.main()
    finally:
        sys.argv = old
    out = json.loads(buf.getvalue())
    assert out["autoreg"] == "trim"
    assert out["day"] == "Upper A"
    assert out["after"] == {"movements": "incline barbell bench press", "sets": 4}
