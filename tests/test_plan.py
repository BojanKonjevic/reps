#!/usr/bin/env python3
"""Phase 1: plan command computes ledger, volume, staleness, slot guess."""

from datetime import date, timedelta


def _plan(log, *args):
    if args:
        return log.get_plan(*args)
    return log.get_plan()


def test_plan_empty_db_shape(log_module):
    log = log_module
    bundle = _plan(log)
    assert set(bundle) == {"today", "slot_guess", "split", "goals", "rules", "volume", "ledger", "lifts",
                           "progression", "flags", "priority", "deload", "autoreg", "adherence", "compaction"}
    assert bundle["today"] == {"open": False, "workout": None, "stale": None,
                                 "last_session": None, "gap_days": None, "break": False}
    assert bundle["slot_guess"]["confidence"] == "low"
    assert len(bundle["volume"]["muscles"]) == 13
    assert bundle["volume"]["muscles"]["chest"]["mev"] == 8
    assert bundle["ledger"]["chest"] == {"sessions": 0, "sets": 0, "last_hit": None}
    assert bundle["lifts"] == []


def test_plan_ledger_and_lifts(log_module):
    log = log_module
    log.start_workout("test")
    log.log_set("bench", 100, 5, "", "chest,front delts")
    log.log_set("bench", 100, 6, "", "chest,front delts")
    bundle = _plan(log)
    assert bundle["ledger"]["chest"]["sets"] == 2
    assert bundle["ledger"]["chest"]["sessions"] == 1
    assert bundle["ledger"]["chest"]["last_hit"] == date.today().isoformat()
    assert bundle["ledger"]["back"]["sets"] == 0
    assert bundle["lifts"][0]["exercise"] == "bench"
    assert bundle["lifts"][0]["best_e1rm"] == round(100 * (1 + 6 / 30.0), 1)
    assert bundle["today"]["open"] is True
    assert bundle["today"]["workout"]["status"] == "open"


def test_plan_volume_uses_complete_rotation_windows(log_module):
    log = log_module
    c = log.conn()
    from conftest import seed_lift as _seed
    _seed(c, "bench", "chest")
    log.set_split("Upper A", 1, "bench", 10)
    log.set_rotation(["Upper A", *([None] * 7)])
    end = date.today()
    for days_ago, nsets in {0: 3, 7: 6, 8: 10}.items():
        d = (end - timedelta(days=days_ago)).isoformat()
        cur = c.execute("INSERT INTO workouts (date, status, notes) VALUES (?, 'done', '')", (d,))
        c.commit()
        for _ in range(nsets):
            cur2 = c.execute(
                "INSERT INTO sets (workout_id, exercise, weight, reps, note, created) VALUES (?, 'bench', 100, 5, '', datetime('now'))",
                (cur.lastrowid,))
        c.commit()
    bundle = _plan(log)
    volume = bundle["volume"]
    chest = volume["muscles"]["chest"]
    assert volume["rotation_days"] == 8
    assert volume["starts"] == [
        (end - timedelta(days=15)).isoformat(),
        (end - timedelta(days=7)).isoformat(),
    ]
    assert chest["rotation_sets"] == [10, 9]
    assert 9 < chest["mev"] < 10
    assert chest["planned_sets"] == 10
    assert chest["low_rotations"] == 1
    assert chest["status"] == "in_range"


def test_classify_volume_meeting_mev_is_in_range():
    """8 sets at MEV 8 after pre-history zeros is in range, not below."""
    from reps.program import classify_volume
    assert classify_volume([0, 0, 0, 0, 0, 0, 0, 8], 8, 25, 4)["status"] == "in_range"


def test_classify_volume_never_trained_is_below():
    """An all-zero window keeps the whole span and flags below MEV."""
    from reps.program import classify_volume
    assert classify_volume([0, 0, 0, 0, 0, 0, 0, 0], 8, 25, 4)["status"] == "below_mev"


def test_classify_volume_idle_after_first_session_is_below():
    """Zeros after the first logged week count: 4 idle weeks flag."""
    from reps.program import classify_volume
    assert classify_volume([0, 0, 0, 8, 0, 0, 0, 0], 8, 25, 4)["status"] == "below_mev"


def test_recent_average_ignores_pre_history():
    """The MRV average runs over the trained span, not the whole window."""
    from reps.program import recent_average
    assert recent_average([0, 0, 0, 0, 0, 0, 0, 30], 4) == 30


def test_plan_stale_open_workout(log_module):
    log = log_module
    c = log.conn()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    c.execute("INSERT INTO workouts (date, status, notes) VALUES (?, 'open', 'stale')", (yesterday,))
    c.commit()
    bundle = _plan(log)
    assert bundle["today"]["stale"]["is_stale"] is True
    assert bundle["today"]["stale"]["age_days"] == 1


def test_plan_break_flag(log_module):
    log = log_module
    c = log.conn()
    five_ago = (date.today() - timedelta(days=5)).isoformat()
    cur = c.execute("INSERT INTO workouts (date, status, notes) VALUES (?, 'done', '')", (five_ago,))
    c.commit()
    from conftest import seed_lift as _seed2
    _seed2(c, "bench", "chest")
    cur2 = c.execute(
        "INSERT INTO sets (workout_id, exercise, weight, reps, note, created) VALUES (?, 'bench', 100, 5, '', datetime('now'))",
        (cur.lastrowid,))
    c.commit()
    bundle = _plan(log)
    assert bundle["today"]["gap_days"] == 5
    assert bundle["today"]["break"] is True


def test_plan_slot_guess_follows_rotation(log_module):
    import json as _json
    from conftest import seed_split
    log = log_module
    c = log.conn()
    from conftest import seed_lift as _seed3
    for ex in ["incline barbell bench press", "hammer strength row", "pec deck", "hack squat"]:
        _seed3(c, ex, "chest")
    c.commit()
    seed_split(log, "Upper A", ("incline barbell bench press", 3), ("hammer strength row", 2), ("pec deck", 2))
    seed_split(log, "Lower A", ("hack squat", 2))
    log.set_rotation(["Upper A", "Lower A"])
    d = (date.today() - timedelta(days=1)).isoformat()
    cur = c.execute("INSERT INTO workouts (date, status, notes) VALUES (?, 'done', '')", (d,))
    c.commit()
    for ex in ["incline barbell bench press", "hammer strength row", "pec deck"]:
        cur2 = c.execute(
            "INSERT INTO sets (workout_id, exercise, weight, reps, note, created) VALUES (?, ?, 80, 6, '', datetime('now'))",
            (cur.lastrowid, ex))
    c.commit()
    bundle = _plan(log)
    assert bundle["slot_guess"]["day"] == "Lower A"
    assert "Upper A" in bundle["slot_guess"]["basis"]
    assert bundle["split"]["day"] == "Lower A"
    assert bundle["split"]["slots"][0]["movements"] == ["hack squat"]


def test_plan_explicit_slot_and_verbose(log_module):
    import datetime as _dt
    log = log_module
    log.set_compaction(postponed_until=(_dt.date.today() + _dt.timedelta(days=30)).isoformat())
    out = "\n".join(_plan(log, "Upper B", True)["lines"])
    assert "slot guess: Upper B" in out
    assert "compaction due" not in out
    bundle = _plan(log, "Upper B", False)
    assert bundle["slot_guess"] == {"day": "Upper B", "basis": "explicit slot", "confidence": "high"}
