#!/usr/bin/env python3
"""Semantic observations: one shared observe() interface over a date range."""

from datetime import date, timedelta

import pytest

from reps.errors import RepsError
from conftest import close_session


def _day(ago):
    return (date.today() - timedelta(days=ago)).isoformat()


def _log_on(log, ago, exercise, weight, reps):
    c = log.conn()
    cur = c.execute("INSERT INTO workouts (date, status, notes) VALUES (?, 'done', '')", (_day(ago),))
    wid = cur.lastrowid
    c.execute("INSERT INTO sets (workout_id, exercise, weight, reps, note, created) "
              "VALUES (?, ?, ?, ?, '', datetime('now'))", (wid, exercise, weight, reps))
    c.commit()


def _seeded(log):
    log.start_workout("test")
    log.log_set("bench", 100, 5, "", "chest")
    log.set_split("Upper A", 1, "bench", 3)
    close_session(log, "baseline")
    c = log.conn()
    w = c.execute("SELECT id FROM workouts ORDER BY id DESC LIMIT 1").fetchone()
    c.execute("UPDATE workouts SET date = ? WHERE id = ?", (_day(6), w["id"]))
    c.commit()
    _log_on(log, 3, "bench", 105, 5)


def test_lift_trend_reports_delta(log_module):
    log = log_module
    _seeded(log)
    out = log.observe("lift_trend", "bench", _day(10), _day(0))
    assert out["metric"] == "lift_trend" and out["subject"] == "bench"
    r = out["result"]
    assert r["sessions_count"] == 2
    assert r["start_e1rm"] == 116.7 and r["end_e1rm"] == 122.5
    assert r["delta_e1rm"] == 5.8 and r["best_e1rm"] == 122.5
    assert [s["date"] for s in r["sessions"]] == [_day(6), _day(3)]
    assert out["provenance"]["sources"] == ["sets", "workouts"]


def test_lift_trend_empty_range(log_module):
    log = log_module
    _seeded(log)
    r = log.observe("lift_trend", "bench", "2020-01-01", "2020-02-01")["result"]
    assert r["sessions_count"] == 0 and r["start_e1rm"] is None


def test_muscle_volume_totals(log_module):
    log = log_module
    _seeded(log)
    r = log.observe("muscle_volume", "chest", _day(10), _day(0))["result"]
    assert r["totals"] == {"chest": 2} and r["total_sets"] == 2
    r_all = log.observe("muscle_volume", "", _day(10), _day(0))["result"]
    assert r_all["totals"]["chest"] == 2


def test_program_activity_counts_changes(log_module):
    log = log_module
    _seeded(log)
    log.set_split("Upper A", 1, "bench", 5)
    r = log.observe("program_activity", "", _day(10), _day(0))["result"]
    assert r["changes"] == 2 and r["subjects"] == ["active:Upper A"]
    assert len(r["change_ids"]) == 2


def test_goal_trajectory_pairs_checkpoints(log_module):
    log = log_module
    _seeded(log)
    deadline = (date.today() + timedelta(days=60)).isoformat()
    gid = log.add_goal("bench", 130, deadline, "", None)["goal_id"]
    r = log.observe("goal_trajectory", str(gid), _day(10), _day(0))["result"]
    assert r["goal_id"] == gid and r["exercise"] == "bench"
    assert r["on_track"] is True
    assert r["checkpoints_vs_actuals"][0]["target"] == 122.5
    assert r["checkpoints_vs_actuals"][0]["actual"] == 122.5


def test_adherence_summary_groups_verdicts(log_module):
    log = log_module
    _seeded(log)
    log.set_rotation(["Upper A", "rest"])
    log.anchor_rotation(_day(6), "Upper A")
    r = log.observe("adherence_summary", "", _day(6), _day(6))["result"]
    assert r["days"] == 1
    assert sum(r["by_status"].values()) == 1
    assert r["verdicts"][0]["date"] == _day(6)


def test_bodyweight_trend_delta(log_module):
    log = log_module
    _seeded(log)
    log.record_bodyweight(80, "")
    c = log.conn()
    c.execute("UPDATE bodyweight SET date = ? WHERE kg = 80", (_day(4),))
    c.execute("INSERT INTO bodyweight (date, kg, note) VALUES (?, 81, '')", (_day(1),))
    c.commit()
    r = log.observe("bodyweight_trend", "", _day(10), _day(0))["result"]
    assert r["n"] == 2 and r["delta_kg"] == 1.0


def test_observe_refusals(log_module):
    log = log_module
    _seeded(log)
    with pytest.raises(RepsError, match="metric must be"):
        log.observe("vibes", "", _day(10), _day(0))
    with pytest.raises(RepsError, match="not a known lift"):
        log.observe("lift_trend", "mystery press", _day(10), _day(0))
    with pytest.raises(RepsError, match="needs a subject"):
        log.observe("lift_trend", "", _day(10), _day(0))
    with pytest.raises(RepsError, match="not a tracked muscle"):
        log.observe("muscle_volume", "neck", _day(10), _day(0))
    with pytest.raises(RepsError, match="since must not be after until"):
        log.observe("lift_trend", "bench", _day(0), _day(10))
    with pytest.raises(RepsError, match="no goal"):
        log.observe("goal_trajectory", "999", _day(10), _day(0))
