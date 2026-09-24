#!/usr/bin/env python3
"""Phase 4: goals and e1RM trajectories live in SQLite."""

from datetime import date, timedelta

import pytest

from reps.errors import RepsError
from conftest import close_session, seed_split


def _out(fn, *args):
    return fn(*args)


def _seeded(log, days_ago=0):
    log.start_workout("test")
    log.log_set("bench", 100, 5, "", "chest")
    seed_split(log, "Upper A", ("bench", 3))
    close_session(log, "baseline")
    if days_ago:
        c = log.conn()
        w = c.execute("SELECT id FROM workouts ORDER BY id DESC LIMIT 1").fetchone()
        back = (date.today() - timedelta(days=days_ago)).isoformat()
        c.execute("UPDATE workouts SET date = ? WHERE id = ?", (back, w["id"]))
        c.commit()


def _deadline(days=60):
    return (date.today() + timedelta(days=days)).isoformat()


def test_goal_add_builds_linear_trajectory(log_module):
    log = log_module
    _seeded(log)
    out = _out(log.add_goal, "bench", 130, _deadline(), "test goal", None)
    assert out["sessions"] >= 8
    rows = _out(log.get_goal, 1)
    assert len(rows) == 1
    cps = rows[0]["checkpoints"]
    assert cps[0] == 116.7 and cps[-1] == 130.0
    assert all(b >= a for a, b in zip(cps, cps[1:]))
    assert rows[0]["on_track"] is True
    assert rows[0]["slippage"] is False


def test_goal_add_rejects_past_deadline_and_unknown_lift(log_module):
    log = log_module
    _seeded(log)
    with pytest.raises(RepsError, match="future"):
        log.add_goal("bench", 130, "2020-01-01", "", None)
    with pytest.raises(RepsError, match="no mapping"):
        log.add_goal("mystery press", 130, _deadline(), "", 100)


def test_goal_rewrite_anchors_on_latest_actual(log_module):
    log = log_module
    _seeded(log, days_ago=6)
    log.add_goal("bench", 130, _deadline(), "", None)
    before = _out(log.get_goal, 1)[0]["checkpoints"]
    log.start_workout("session 2")
    log.log_set("bench", 110, 5, "", "chest")
    close_session(log, "big jump")
    out = _out(log.rewrite_goal, 1)
    assert out["rewritten_from_session"] == 3
    after = _out(log.get_goal, 1)[0]["checkpoints"]
    assert after[2] > before[2]
    assert after[-1] == 130.0


def test_goal_divergence_flags_in_audit(log_module):
    log = log_module
    _seeded(log, days_ago=9)
    log.add_goal("bench", 200, _deadline(), "", None)
    c0 = log.conn()
    back = (date.today() - timedelta(days=9)).isoformat()
    c0.execute("UPDATE goals SET created = ? WHERE id = 1", (back,))
    c0.commit()
    for ago, weight in [(6, 80), (3, 80)]:
        d = (date.today() - timedelta(days=ago)).isoformat()
        c = log.conn()
        cur = c.execute("INSERT INTO workouts (date, status, notes) VALUES (?, 'done', '')", (d,))
        c.commit()
        cur2 = c.execute(
            "INSERT INTO sets (workout_id, exercise, weight, reps, note, created) VALUES (?, 'bench', ?, 5, '', datetime('now'))",
            (cur.lastrowid, weight))
        c.execute("INSERT INTO set_muscles (set_id, muscle) VALUES (?, 'chest')", (cur2.lastrowid,))
        c.commit()
    flags = log.run_audit()["flags"]
    assert [f for f in flags if f["check"] == "goal_divergence"]


def test_goal_slippage_when_frequency_too_low(log_module):
    log = log_module
    _seeded(log)
    log.add_goal("bench", 130, _deadline(60), "", None)
    c = log.conn()
    c.execute("DELETE FROM splits WHERE variant = 'active' AND day = 'Upper A'")
    c.commit()
    rows = _out(log.get_goal, 1)
    assert rows[0]["slippage"] is True


def test_goal_drop(log_module):
    log = log_module
    _seeded(log)
    log.add_goal("bench", 130, _deadline(), "", None)
    log.drop_goal(1)
    assert _out(log.get_goal, None) == []


def test_plan_surfaces_goal(log_module):
    log = log_module
    _seeded(log)
    log.add_goal("bench", 130, _deadline(), "", None)
    bundle = log.get_plan("Upper A", False)
    assert bundle["goals"][0]["exercise"] == "bench"
    assert bundle["split"]["slots"][0]["goal"]["id"] == bundle["goals"][0]["id"]
