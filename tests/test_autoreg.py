#!/usr/bin/env python3
"""Autoreg code enforcement: plan signals, MEV floor, apply/log/revert."""

import json
from datetime import date, timedelta

import pytest

from reps.errors import RepsError


def _out(fn, *args):
    return fn(*args)


def _plan(log, *args):
    if args:
        return log.get_plan(*args)
    return log.get_plan()


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
    bundle = _plan(log)
    assert set(bundle["autoreg"]) == {"permitted", "holds", "miss_streaks", "drop_watch",
                                      "grouped", "program_volume"}
    assert bundle["autoreg"]["permitted"] is False
    assert bundle["autoreg"]["holds"] == []
    assert bundle["autoreg"]["miss_streaks"] == []
    assert bundle["autoreg"]["drop_watch"] == []
    assert bundle["autoreg"]["grouped"] == {}
    assert len(bundle["autoreg"]["program_volume"]) == 13
    log.add_rule("autoreg: manage volume within MEV..MRV", "autoreg", None)
    assert _plan(log)["autoreg"]["permitted"] is True


def test_programmed_volume_scales_rotation_to_week(log_module):
    log = log_module
    log.set_exercise_mapping("bench", "chest")
    log.set_exercise_mapping("squat", "quads")
    log.set_split("Upper A", 1, "bench", 3)
    log.set_split("Lower A", 1, "squat", 2)
    log.set_meta("rotation", json.dumps(["Upper A", "Lower A", "rest"]))
    vol = _plan(log)["autoreg"]["program_volume"]
    assert vol["chest"] == round(3 * 7.0 / 3, 1)
    assert vol["quads"] == round(2 * 7.0 / 3, 1)
    assert vol["back"] == 0
    assert len(vol) == 13


def test_split_set_mev_warnings_scoped_to_edited_muscles(log_module):
    log = log_module
    log.set_exercise_mapping("bench", "chest")
    out = _out(log.set_split, "Upper A", 1, "bench", 3)
    assert "warnings" in out
    assert any("chest" in w for w in out["warnings"])
    assert not any("quad" in w or "back" in w for w in out["warnings"])
    # MEV 0 muscles never warn.
    log.set_exercise_mapping("ohp", "front delts")
    out = _out(log.set_split, "Upper A", 2, "ohp", 1)
    assert "warnings" not in out


def test_miss_streaks_drop_watch_and_grouped(log_module):
    log = log_module
    c = log.conn()
    log.set_exercise_mapping("bench", "chest")
    log.set_exercise_mapping("incline", "chest")
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
    bundle = _plan(log)
    auto = bundle["autoreg"]
    assert {m["exercise"]: m["streak"] for m in auto["miss_streaks"]} == {"bench": 2, "incline": 2}
    assert sorted(d["exercise"] for d in auto["drop_watch"]) == ["bench", "incline"]
    assert auto["grouped"] == {"chest": ["bench", "incline"]}
    log.add_rule("autoreg: manage volume", "autoreg", None)
    verbose = "\n".join(_plan(log, None, True)["lines"])
    assert "autoreg signals:" in verbose
    assert "2xmiss" in verbose and "dropping" in verbose


def _trim_setup(log):
    log.add_rule("autoreg: manage volume within MEV..MRV", "autoreg", None)
    log.set_exercise_mapping("bench", "chest")
    log.set_exercise_mapping("incline", "chest")
    log.set_split("Upper A", 1, "bench", 5)
    log.set_split("Upper A", 2, "incline", 5)


def test_apply_refuses_without_permission(log_module):
    log = log_module
    log.set_exercise_mapping("bench", "chest")
    log.set_split("Upper A", 1, "bench", 5)
    with pytest.raises(RepsError, match="no standing permission"):
        log.apply_autoreg("Upper A", 1, "bench", 4, "two misses")


def test_apply_trim_records_hold_and_change_then_blocks_held_slot(log_module):
    log = log_module
    _trim_setup(log)
    with pytest.raises(RepsError, match="from-guard mismatch"):
        log.apply_autoreg("Upper A", 1, "bench", 4, "two misses", "incline")
    with pytest.raises(RepsError, match="no active split slot"):
        log.apply_autoreg("Upper A", 9, "bench", 4, "two misses")
    out = _out(log.apply_autoreg, "Upper A", 1, "bench", 4, "two misses", "bench")
    assert out["autoreg"] == "trim"
    assert out["before"] == {"movements": "bench", "sets": 5}
    assert out["after"] == {"movements": "bench", "sets": 4}
    assert out["hold_until"] == (date.today() + timedelta(days=8)).isoformat()
    c = log.conn()
    holds = c.execute("SELECT * FROM autoreg_holds").fetchall()
    assert len(holds) == 1 and holds[0]["hold_until"] == out["hold_until"]
    changes = _out(log.list_autoreg_changes)
    assert len(changes) == 1 and changes[0]["reverted"] is False
    with pytest.raises(RepsError, match="revert first"):
        log.apply_autoreg("Upper A", 1, "bench", 3, "still bad")
    reverted = _out(log.revert_autoreg_change, 1)
    assert reverted["restored"] == {"movements": "bench", "sets": 5}
    assert reverted["holds_cleared"] == 1
    assert c.execute("SELECT COUNT(*) n FROM autoreg_holds").fetchone()["n"] == 0
    assert log.read_split("active", "Upper A")[0] == {"day": "Upper A", "slot": 1,
                                                     "movements": "bench", "sets": 5}
    with pytest.raises(RepsError, match="already reverted"):
        log.revert_autoreg_change(1)


def test_apply_refuses_below_mev_and_unmapped(log_module):
    log = log_module
    _trim_setup(log)
    with pytest.raises(RepsError, match="no mapping"):
        log.apply_autoreg("Upper A", 1, "mystery press", 2, "trying a swap")
    with pytest.raises(RepsError, match="below MEV"):
        log.apply_autoreg("Upper A", 1, "bench", 1, "deep cut")
    assert log.read_split("active", "Upper A")[0]["sets"] == 5
    assert _out(log.list_autoreg_changes) == []


def test_revert_of_manually_moved_slot_refuses(log_module):
    log = log_module
    _trim_setup(log)
    _out(log.apply_autoreg, "Upper A", 1, "bench", 4, "two misses")
    log.set_split("Upper A", 1, "incline", 4)
    with pytest.raises(RepsError, match="reconcile manually"):
        log.revert_autoreg_change(1)


def test_apply_swap_and_add_classification(log_module):
    log = log_module
    _trim_setup(log)
    swap = _out(log.apply_autoreg, "Upper A", 1, "incline", 5, "strong evidence", "bench")
    assert swap["autoreg"] == "swap"
    assert swap["hold_until"] is not None
    log.revert_autoreg_change(swap["change_id"])
    add = _out(log.apply_autoreg, "Upper A", 1, "bench", 6, "clear recovery", "bench")
    assert add["autoreg"] == "add"
    assert add["hold_until"] is None
    c = log.conn()
    assert c.execute("SELECT COUNT(*) n FROM autoreg_holds").fetchone()["n"] == 0


def test_autoreg_apply_structured_args(log_module):
    """Multi-word names travel as plain strings (no quoting layer); the
    from-guard still refuses concurrent edits."""
    log = log_module
    log.add_rule("autoreg: manage volume", "autoreg", None)
    log.set_exercise_mapping("incline barbell bench press", "chest,front delts")
    log.set_exercise_mapping("flat barbell bench press", "chest,front delts")
    log.set_split("Upper A", 1, "incline barbell bench press", 5)
    log.set_split("Upper A", 2, "flat barbell bench press", 5)
    out = _out(log.apply_autoreg, "Upper A", 1,
                 "incline barbell bench press", 4,
                 "two misses", "incline barbell bench press")
    assert out["autoreg"] == "trim"
    assert out["day"] == "Upper A"
    assert out["after"] == {"movements": "incline barbell bench press", "sets": 4}
