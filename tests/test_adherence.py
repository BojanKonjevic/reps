#!/usr/bin/env python3
"""Rotation adherence: anchor, expected schedule, status classification, drift."""

import json
from datetime import date, timedelta

import pytest
from conftest import close_session
from reps.errors import RepsError


def _plan(log, *args):
    if args:
        return log.get_plan(*args)
    return log.get_plan()


def _done(c, day, *exercises):
    cur = c.execute("INSERT INTO workouts (date, status, notes) VALUES (?, 'done', '')", (day,))
    for ex in exercises:
        c.execute("INSERT INTO sets (workout_id, exercise, weight, reps, note, created) "
                  "VALUES (?, ?, 100, 5, '', datetime('now'))", (cur.lastrowid, ex))
    c.commit()


def _rest(c, day):
    c.execute("INSERT INTO workouts (date, status, notes) VALUES (?, 'rest', '')", (day,))
    c.commit()


def _seed_3day(log):
    log.set_exercise_mapping("bench", "chest")
    log.set_exercise_mapping("squat", "quads")
    log.set_split("Upper A", 1, "bench", 3)
    log.set_split("Lower A", 1, "squat", 3)
    log.set_rotation(["Upper A", "Lower A", "rest"])


def test_expected_wraparound_and_multi_cycle(log_module):
    log = log_module
    rot = ["U1", "L1", "U2", "rest"]
    anchor = {"date": "2026-09-01", "index": 0}
    assert log.expected_day(rot, anchor, "2026-09-01") == "U1"
    assert log.expected_day(rot, anchor, "2026-09-04") == "rest"
    assert log.expected_day(rot, anchor, "2026-09-05") == "U1"
    assert log.expected_day(rot, anchor, "2026-09-10") == "L1"
    assert log.expected_day(rot, anchor, "2025-01-01") == rot[(0 + (date(2025, 1, 1) - date(2026, 9, 1)).days) % 4]


def test_anchor_resolves_first_rotation_index(log_module):
    log = log_module
    log.set_exercise_mapping("bench", "chest")
    log.set_split("Upper A", 1, "bench", 3)
    log.set_split("Lower A", 1, "bench", 3)
    log.set_rotation(["Upper A", "Lower A", "rest"])
    out = log.anchor_rotation("2026-09-01", "lower a")
    assert out == {"anchor": {"date": "2026-09-01", "index": 1}, "day": "Lower A"}
    with pytest.raises(RepsError, match="no rotation entry"):
        log.anchor_rotation("2026-09-01", "Upper Z")
    with pytest.raises(RepsError, match="cannot be in the future"):
        log.anchor_rotation("2999-01-01", "Upper A")
    with pytest.raises(RepsError, match="YYYY-MM-DD"):
        log.anchor_rotation("yesterday", "Upper A")
    c = log.conn()
    for bad in ({"date": "2026-09-01", "index": 1.5}, {"date": "2026-09-01", "index": True},
                {"date": "2026-09-01", "index": "1"}):
        assert log.parse_anchor(bad, ["Upper A", "Lower A", "rest"])[0] is None


def test_status_classifications(log_module):
    log = log_module
    c = log.conn()
    _seed_3day(log)
    log.anchor_rotation("2026-08-10", "Upper A")
    # 08-10 U expected, bench trained -> done
    _done(c, "2026-08-10", "bench")
    # 08-11 L expected, bench trained -> swapped
    _done(c, "2026-08-11", "bench")
    # 08-12 rest expected, bench trained -> extra
    _done(c, "2026-08-12", "bench")
    # 08-13 U expected, nothing -> missed
    # 08-14 L expected, rest row, no sets -> rest_logged
    _rest(c, "2026-08-14")
    # 08-15 rest expected, nothing -> rest_ok
    # 08-16 U expected (6 % 3 == 0), nothing -> missed
    # 08-17 L expected, bench+squat tie -> swapped
    _done(c, "2026-08-17", "bench", "squat")
    # 08-18 rest expected, rest row -> rest_ok
    _rest(c, "2026-08-18")
    out = log.get_rotation_status("2026-08-10", "2026-08-18")
    by_date = {e["date"]: e for e in out}
    assert by_date["2026-08-10"] == {"date": "2026-08-10", "expected": "Upper A",
                                     "trained": "Upper A", "status": "done"}
    assert by_date["2026-08-11"]["status"] == "swapped"
    assert by_date["2026-08-11"]["trained"] == "Upper A"
    assert by_date["2026-08-12"] == {"date": "2026-08-12", "expected": "rest",
                                     "trained": "Upper A", "status": "extra"}
    assert by_date["2026-08-13"] == {"date": "2026-08-13", "expected": "Upper A",
                                     "trained": None, "status": "missed"}
    assert by_date["2026-08-14"] == {"date": "2026-08-14", "expected": "Lower A",
                                     "trained": None, "status": "rest_logged"}
    assert by_date["2026-08-15"]["status"] == "rest_ok"
    assert by_date["2026-08-17"]["status"] == "swapped"
    assert by_date["2026-08-17"]["trained"] is None
    assert by_date["2026-08-18"]["status"] == "rest_ok"


def _seed_5day(log):
    for ex, mu in [("ex_u1", "chest"), ("ex_l1", "back"), ("ex_u2", "chest"),
                   ("ex_l2", "back"), ("ex_u3", "chest")]:
        log.set_exercise_mapping(ex, mu)
    log.set_split("U1", 1, "ex_u1", 3)
    log.set_split("L1", 1, "ex_l1", 3)
    log.set_split("U2", 1, "ex_u2", 3)
    log.set_split("L2", 1, "ex_l2", 3)
    log.set_split("U3", 1, "ex_u3", 3)
    log.set_rotation(["U1", "L1", "U2", "L2", "U3"])


def test_wednesday_skip_expected_vs_guess(log_module):
    """Skipped U2/L2: Friday expects U3 while the slot guess still offers U2."""
    log = log_module
    c = log.conn()
    _seed_5day(log)
    today = date.today()
    log.anchor_rotation((today - timedelta(days=4)).isoformat(), "U1")
    _done(c, (today - timedelta(days=4)).isoformat(), "ex_u1")
    _done(c, (today - timedelta(days=3)).isoformat(), "ex_l1")
    bundle = _plan(log)
    assert bundle["slot_guess"]["day"] == "U2"
    assert bundle["slot_guess"]["expected"]["day"] == "U3"
    assert "expected today: U3" in bundle["slot_guess"]["basis"]
    assert "missed U2" in bundle["slot_guess"]["basis"]
    missed = [m["day"] for m in bundle["slot_guess"]["expected"]["missed"]]
    assert missed == ["U2", "L2", "U3"]
    assert bundle["slot_guess"]["expected"]["last_done"] == {
        "date": (today - timedelta(days=3)).isoformat(), "day": "L1"}
    assert bundle["adherence"]["drift"] is True
    assert bundle["adherence"]["drift_days"] == 3


def test_drift_clears_on_reanchor(log_module):
    log = log_module
    c = log.conn()
    _seed_5day(log)
    today = date.today()
    log.anchor_rotation((today - timedelta(days=4)).isoformat(), "U1")
    _done(c, (today - timedelta(days=4)).isoformat(), "ex_u1")
    _done(c, (today - timedelta(days=3)).isoformat(), "ex_l1")
    assert _plan(log)["adherence"]["drift"] is True
    # Train today off-schedule, then re-anchor to what was actually trained:
    # today flips to done and the drift flag clears.
    log.start_workout("test")
    log.log_set("ex_l2", 100, 5, "", "back")
    close_session(log, "done")
    assert _plan(log)["adherence"]["drift"] is True
    log.anchor_rotation(today.isoformat(), "L2")
    bundle = _plan(log)
    assert bundle["adherence"]["drift"] is False
    assert bundle["adherence"]["drift_days"] == 0
    assert not any("adherence drift" in line for line in _plan(log, None, True)["lines"])


def test_drift_verbose_line(log_module):
    log = log_module
    c = log.conn()
    _seed_5day(log)
    today = date.today()
    log.anchor_rotation((today - timedelta(days=4)).isoformat(), "U1")
    _done(c, (today - timedelta(days=4)).isoformat(), "ex_u1")
    _done(c, (today - timedelta(days=3)).isoformat(), "ex_l1")
    verbose = _plan(log, None, True)["lines"]
    assert "adherence drift: 3 non-done days" in "\n".join(verbose)


def test_no_anchor_disables_adherence(log_module):
    log = log_module
    c = log.conn()
    _seed_5day(log)
    today = date.today()
    _done(c, (today - timedelta(days=1)).isoformat(), "ex_u1")
    bundle = _plan(log)
    assert bundle["adherence"] is None
    assert "expected" not in bundle["slot_guess"]
    assert "expected today" not in bundle["slot_guess"]["basis"]
    with pytest.raises(RepsError, match="needs a rotation and an anchor"):
        log.get_rotation_status()


def test_doctor_anchor_checks(log_module):
    log = log_module
    c = log.conn()
    log.set_exercise_mapping("bench", "chest")
    log.set_exercise_mapping("row", "back")
    log.set_split("Upper A", 1, "bench", 3)
    log.set_split("Lower A", 1, "row", 3)
    log.set_rotation(["Upper A", "Lower A", "rest"])
    log.anchor_rotation("2026-09-01", "Upper A")
    assert log.run_doctor()["ok"] is True
    with pytest.raises(RepsError, match="matches no rotation entry"):
        log.anchor_rotation("2026-09-01", "Nope C")
    c.execute("UPDATE rotation_anchor SET anchor_date = '2999-01-01', position = 0")
    c.commit()
    result = log.run_doctor()
    assert result["ok"] is False
    c.execute("UPDATE rotation_anchor SET anchor_date = 'not json', position = 0")
    c.commit()
    result = log.run_doctor()
    assert result["ok"] is False


def test_status_stops_at_today(log_module):
    log = log_module
    c = log.conn()
    _seed_3day(log)
    log.anchor_rotation("2026-08-10", "Upper A")
    future = (date.today() + timedelta(days=5)).isoformat()
    out = log.get_rotation_status(date.today().isoformat(), future)
    assert out and all(e["date"] <= date.today().isoformat() for e in out)
    out = log.get_rotation_status(future, future)
    assert out == []


def test_open_session_does_not_count_as_trained(log_module):
    log = log_module
    c = log.conn()
    _seed_3day(log)
    today = date.today()
    log.anchor_rotation((today - timedelta(days=3)).isoformat(), "Upper A")
    log.start_workout("test")
    log.log_set("bench", 100, 5, "", "chest")
    entry = log.get_rotation_status(today.isoformat(), today.isoformat())[0]
    assert entry["status"] == "missed"


def test_invalid_anchor_says_so(log_module):
    log = log_module
    c = log.conn()
    log.set_exercise_mapping("bench", "chest")
    log.set_split("Upper A", 1, "bench", 3)
    log.set_split("Lower A", 1, "bench", 3)
    log.set_rotation(["Upper A", "Lower A", "rest"])
    c.execute("INSERT INTO rotation_anchor (id, anchor_date, position) VALUES (1, 'not json', 0)")
    c.commit()
    with pytest.raises(RepsError, match="invalid"):
        log.get_rotation_status()
    assert _plan(log)["adherence"] is None


def test_rotation_replace_preserves_or_clears_anchor(log_module):
    log = log_module
    log.set_exercise_mapping("bench", "chest")
    log.set_split("Upper A", 1, "bench", 3)
    log.set_split("Lower A", 1, "bench", 3)
    log.set_rotation(["Upper A", "Lower A", "rest"])
    log.anchor_rotation("2026-09-01", "Lower A")
    out = log.set_rotation(["Upper A", "Lower A"])
    assert out["anchor_cleared"] is False
    assert log.get_anchor(log.conn()) == {"date": "2026-09-01", "index": 1}
    out = log.set_rotation(["Upper A"])
    assert out["anchor_cleared"] is True
    assert log.get_anchor(log.conn()) is None
    log.anchor_rotation("2026-09-01", "Upper A")
    out = log.set_rotation(["Lower A", "Upper A", "rest"])
    assert out["anchor_cleared"] is True
    assert log.get_anchor(log.conn()) is None


def test_adherence_windows_start_at_anchor(log_module):
    """Dates before the program existed are unscored, never missed."""
    log = log_module
    _seed_3day(log)
    log.anchor_rotation((date.today() - timedelta(days=2)).isoformat(), "Upper A")
    snap = log.export_snapshot()["adherence"]
    assert snap["days"]
    assert all(d["date"] >= snap["anchor"]["date"] for d in snap["days"])


def test_slot_guess_lists_no_missed_before_first_session(log_module):
    """Never trained means nothing was skipped: missed list stays empty."""
    log = log_module
    _seed_3day(log)
    log.anchor_rotation((date.today() - timedelta(days=2)).isoformat(), "Upper A")
    expected = _plan(log)["slot_guess"]["expected"]
    assert expected["last_done"] is None
    assert expected["missed"] == []
