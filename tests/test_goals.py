#!/usr/bin/env python3
"""Phase 4: goals and e1RM trajectories live in SQLite."""

import io
import json
from contextlib import redirect_stdout
from datetime import date, timedelta

import pytest
from conftest import close_session, seed_split


def _out(fn, *args):
    buf = io.StringIO()
    with redirect_stdout(buf):
        fn(*args)
    return buf.getvalue()


def _seeded(log, days_ago=0):
    log.start("test")
    log.log("bench", 100, 5, "", "chest")
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
    out = json.loads(_out(log.goal_add, "bench", 130, _deadline(), "test goal", None))
    assert out["sessions"] >= 8
    rows = json.loads(_out(log.goal_show, 1))
    assert len(rows) == 1
    cps = rows[0]["checkpoints"]
    assert cps[0] == 116.7 and cps[-1] == 130.0
    assert all(b >= a for a, b in zip(cps, cps[1:]))
    assert rows[0]["on_track"] is True
    assert rows[0]["slippage"] is False


def test_goal_add_rejects_past_deadline_and_unknown_lift(log_module):
    log = log_module
    _seeded(log)
    with pytest.raises(SystemExit, match="future"):
        log.goal_add("bench", 130, "2020-01-01", "", None)
    with pytest.raises(SystemExit, match="no mapping"):
        log.goal_add("mystery press", 130, _deadline(), "", 100)


def test_goal_rewrite_anchors_on_latest_actual(log_module):
    log = log_module
    _seeded(log, days_ago=6)
    log.goal_add("bench", 130, _deadline(), "", None)
    before = json.loads(_out(log.goal_show, 1))[0]["checkpoints"]
    log.start("session 2")
    log.log("bench", 110, 5, "", "chest")
    close_session(log, "big jump")
    out = json.loads(_out(log.goal_rewrite, 1))
    assert out["rewritten_from_session"] == 3
    after = json.loads(_out(log.goal_show, 1))[0]["checkpoints"]
    assert after[2] > before[2]
    assert after[-1] == 130.0


def test_goal_divergence_flags_in_audit(log_module):
    log = log_module
    _seeded(log, days_ago=9)
    log.goal_add("bench", 200, _deadline(), "", None)
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
    buf = io.StringIO()
    with redirect_stdout(buf):
        log.audit()
    flags = json.loads(buf.getvalue().strip().splitlines()[-1])["flags"]
    assert [f for f in flags if f["check"] == "goal_divergence"]


def test_goal_slippage_when_frequency_too_low(log_module):
    log = log_module
    _seeded(log)
    log.goal_add("bench", 130, _deadline(60), "", None)
    c = log.conn()
    c.execute("DELETE FROM splits WHERE variant = 'active' AND day = 'Upper A'")
    c.commit()
    rows = json.loads(_out(log.goal_show, 1))
    assert rows[0]["slippage"] is True


def test_goal_drop(log_module):
    log = log_module
    _seeded(log)
    log.goal_add("bench", 130, _deadline(), "", None)
    log.goal_drop(1)
    assert json.loads(_out(log.goal_show, None)) == []


def test_plan_surfaces_goal(log_module):
    log = log_module
    _seeded(log)
    log.goal_add("bench", 130, _deadline(), "", None)
    buf = io.StringIO()
    with redirect_stdout(buf):
        log.plan("Upper A", False)
    bundle = json.loads(buf.getvalue())
    assert bundle["goals"][0]["exercise"] == "bench"
    assert bundle["split"]["slots"][0]["goal"]["id"] == bundle["goals"][0]["id"]
