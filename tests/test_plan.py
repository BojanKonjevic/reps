#!/usr/bin/env python3
"""Phase 1: plan command computes ledger, volume, staleness, slot guess."""

import io
import json
import sys
from contextlib import redirect_stdout
from datetime import date, timedelta


def _plan(log, *args):
    buf = io.StringIO()
    with redirect_stdout(buf):
        if args:
            log.cmd_plan(*args)
        else:
            log.cmd_plan()
    return buf.getvalue()


def test_plan_empty_db_shape(log_module):
    log = log_module
    bundle = json.loads(_plan(log))
    assert set(bundle) == {"today", "slot_guess", "volume", "ledger", "lifts", "compaction"}
    assert bundle["today"]["open"] is False
    assert bundle["slot_guess"]["confidence"] == "low"
    assert len(bundle["volume"]) == 13
    assert bundle["volume"]["chest"]["mev"] == 8
    assert bundle["ledger"]["chest"] == {"sessions": 0, "sets": 0, "last_hit": None}
    assert bundle["lifts"] == []


def test_plan_ledger_and_lifts(log_module):
    log = log_module
    log.cmd_start("test")
    log.cmd_log("bench", 100, 5, "", "chest,front delt")
    log.cmd_log("bench", 100, 6, "", "chest,front delt")
    bundle = json.loads(_plan(log))
    assert bundle["ledger"]["chest"]["sets"] == 2
    assert bundle["ledger"]["chest"]["sessions"] == 1
    assert bundle["ledger"]["chest"]["last_hit"] == date.today().isoformat()
    assert bundle["ledger"]["back"]["sets"] == 0
    assert bundle["lifts"][0]["exercise"] == "bench"
    assert bundle["lifts"][0]["best_e1rm"] == round(100 * (1 + 6 / 30.0), 1)
    assert bundle["today"]["open"] is not False


def test_plan_volume_weekly_counts(log_module):
    log = log_module
    c = log.conn()
    monday = date.today() - timedelta(days=date.today().weekday())
    for ago, nsets in {0: 3, 1: 5}.items():
        d = (monday - timedelta(weeks=ago) + timedelta(days=2)).isoformat()
        cur = c.execute("INSERT INTO workouts (date, status, notes) VALUES (?, 'done', '')", (d,))
        c.commit()
        for _ in range(nsets):
            cur2 = c.execute(
                "INSERT INTO sets (workout_id, exercise, weight, reps, note, created) VALUES (?, 'bench', 100, 5, '', datetime('now'))",
                (cur.lastrowid,))
            c.execute("INSERT INTO set_muscles (set_id, muscle) VALUES (?, 'chest')", (cur2.lastrowid,))
        c.commit()
    bundle = json.loads(_plan(log))
    weekly = bundle["volume"]["chest"]["weekly"]
    assert len(weekly) == 8
    assert weekly[-1] == 3
    assert weekly[-2] == 5
    assert bundle["volume"]["chest"]["status"] == "below_mev"


def test_plan_stale_open_workout(log_module):
    log = log_module
    c = log.conn()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    c.execute("INSERT INTO workouts (date, status, notes) VALUES (?, 'open', 'stale')", (yesterday,))
    c.commit()
    bundle = json.loads(_plan(log))
    assert bundle["today"]["stale"]["is_stale"] is True
    assert bundle["today"]["stale"]["age_days"] == 1


def test_plan_break_flag(log_module):
    log = log_module
    c = log.conn()
    five_ago = (date.today() - timedelta(days=5)).isoformat()
    cur = c.execute("INSERT INTO workouts (date, status, notes) VALUES (?, 'done', '')", (five_ago,))
    c.commit()
    cur2 = c.execute(
        "INSERT INTO sets (workout_id, exercise, weight, reps, note, created) VALUES (?, 'bench', 100, 5, '', datetime('now'))",
        (cur.lastrowid,))
    c.execute("INSERT INTO set_muscles (set_id, muscle) VALUES (?, 'chest')", (cur2.lastrowid,))
    c.commit()
    bundle = json.loads(_plan(log))
    assert bundle["today"]["gap_days"] == 5
    assert bundle["today"]["break"] is True


def test_plan_slot_guess_follows_rotation(log_module):
    log = log_module
    c = log.conn()
    d = (date.today() - timedelta(days=1)).isoformat()
    cur = c.execute("INSERT INTO workouts (date, status, notes) VALUES (?, 'done', '')", (d,))
    c.commit()
    for ex in ["incline barbell bench press", "hammer strength row", "pec deck"]:
        cur2 = c.execute(
            "INSERT INTO sets (workout_id, exercise, weight, reps, note, created) VALUES (?, ?, 80, 6, '', datetime('now'))",
            (cur.lastrowid, ex))
        c.execute("INSERT INTO set_muscles (set_id, muscle) VALUES (?, 'chest')", (cur2.lastrowid,))
    c.commit()
    bundle = json.loads(_plan(log))
    assert bundle["slot_guess"]["day"] == "Lower A"
    assert "Upper A" in bundle["slot_guess"]["basis"]


def test_plan_explicit_slot_and_verbose(log_module):
    log = log_module
    out = _plan(log, "Upper B", True)
    assert "slot guess: Upper B" in out
    assert "compaction due" not in out
    bundle = json.loads(_plan(log, "Upper B", False))
    assert bundle["slot_guess"] == {"day": "Upper B", "basis": "explicit --slot", "confidence": "high"}
