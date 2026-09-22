#!/usr/bin/env python3
"""Rotation adherence: anchor, expected schedule, status classification, drift."""

import io
import json
from contextlib import redirect_stdout
from datetime import date, timedelta

import pytest
from conftest import close_session


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
    log.cmd_retag("bench", "chest")
    log.cmd_retag("squat", "quads")
    log.cmd_split_set("Upper A", 1, "bench", 3)
    log.cmd_split_set("Lower A", 1, "squat", 3)
    log.cmd_meta_set("rotation", json.dumps(["Upper A", "Lower A", "rest"]))


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
    log.cmd_meta_set("rotation", json.dumps(["Upper A", "Lower A", "rest"]))
    out = json.loads(_out(log.cmd_rotation_anchor, "2026-09-01", "lower a"))
    assert out == {"anchor": {"date": "2026-09-01", "index": 1}, "day": "Lower A"}
    with pytest.raises(SystemExit, match="no rotation entry"):
        log.cmd_rotation_anchor("2026-09-01", "Upper Z")
    with pytest.raises(SystemExit, match="cannot be in the future"):
        log.cmd_rotation_anchor("2999-01-01", "Upper A")
    with pytest.raises(SystemExit, match="YYYY-MM-DD"):
        log.cmd_rotation_anchor("yesterday", "Upper A")


def test_status_classifications(log_module):
    log = log_module
    c = log.conn()
    _seed_3day(log)
    log.cmd_rotation_anchor("2026-08-10", "Upper A")
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
    out = json.loads(_out(log.cmd_rotation_status, "2026-08-10", "2026-08-18"))
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
        log.cmd_retag(ex, mu)
    log.cmd_split_set("U1", 1, "ex_u1", 3)
    log.cmd_split_set("L1", 1, "ex_l1", 3)
    log.cmd_split_set("U2", 1, "ex_u2", 3)
    log.cmd_split_set("L2", 1, "ex_l2", 3)
    log.cmd_split_set("U3", 1, "ex_u3", 3)
    log.cmd_meta_set("rotation", json.dumps(["U1", "L1", "U2", "L2", "U3"]))


def test_wednesday_skip_expected_vs_guess(log_module):
    """Skipped U2/L2: Friday expects U3 while the slot guess still offers U2."""
    log = log_module
    c = log.conn()
    _seed_5day(log)
    today = date.today()
    log.cmd_rotation_anchor((today - timedelta(days=4)).isoformat(), "U1")
    _done(c, (today - timedelta(days=4)).isoformat(), "ex_u1")
    _done(c, (today - timedelta(days=3)).isoformat(), "ex_l1")
    bundle = json.loads(_plan(log))
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
    log.cmd_rotation_anchor((today - timedelta(days=4)).isoformat(), "U1")
    _done(c, (today - timedelta(days=4)).isoformat(), "ex_u1")
    _done(c, (today - timedelta(days=3)).isoformat(), "ex_l1")
    assert json.loads(_plan(log))["adherence"]["drift"] is True
    # Train today off-schedule, then re-anchor to what was actually trained:
    # today flips to done and the drift flag clears.
    log.cmd_start("test")
    log.cmd_log("ex_l2", 100, 5, "", "back")
    close_session(log, "done")
    assert json.loads(_plan(log))["adherence"]["drift"] is True
    log.cmd_rotation_anchor(today.isoformat(), "L2")
    bundle = json.loads(_plan(log))
    assert bundle["adherence"]["drift"] is False
    assert bundle["adherence"]["drift_days"] == 0
    assert "adherence drift" not in _plan(log, None, True)


def test_drift_verbose_line(log_module):
    log = log_module
    c = log.conn()
    _seed_5day(log)
    today = date.today()
    log.cmd_rotation_anchor((today - timedelta(days=4)).isoformat(), "U1")
    _done(c, (today - timedelta(days=4)).isoformat(), "ex_u1")
    _done(c, (today - timedelta(days=3)).isoformat(), "ex_l1")
    verbose = _plan(log, None, True)
    assert "adherence drift: 3 non-done days" in verbose


def test_no_anchor_disables_adherence(log_module):
    log = log_module
    c = log.conn()
    _seed_5day(log)
    today = date.today()
    _done(c, (today - timedelta(days=1)).isoformat(), "ex_u1")
    bundle = json.loads(_plan(log))
    assert bundle["adherence"] is None
    assert "expected" not in bundle["slot_guess"]
    assert "expected today" not in bundle["slot_guess"]["basis"]
    with pytest.raises(SystemExit, match="needs a rotation and an anchor"):
        log.cmd_rotation_status()


def test_doctor_anchor_checks(log_module):
    log = log_module
    c = log.conn()
    log.cmd_meta_set("rotation", json.dumps(["Upper A", "Lower A", "rest"]))
    log.cmd_retag("bench", "chest")
    log.cmd_retag("row", "back")
    log.cmd_split_set("Upper A", 1, "bench", 3)
    log.cmd_split_set("Lower A", 1, "row", 3)
    log.cmd_rotation_anchor("2026-09-01", "Upper A")
    buf = io.StringIO()
    with redirect_stdout(buf):
        log.cmd_doctor()
    assert json.loads(buf.getvalue())["ok"] is True
    c.execute("UPDATE meta SET value = ? WHERE key = 'rotation_anchor'",
              (json.dumps({"date": "2026-09-01", "index": 9}),))
    c.commit()
    with pytest.raises(SystemExit):
        with redirect_stdout(io.StringIO()):
            log.cmd_doctor()
    c.execute("UPDATE meta SET value = ? WHERE key = 'rotation_anchor'",
              (json.dumps({"date": "2999-01-01", "index": 0}),))
    c.commit()
    try:
        with redirect_stdout(io.StringIO()):
            log.cmd_doctor()
        assert False, "should have exited"
    except SystemExit as e:
        assert e.code == 1
    c.execute("UPDATE meta SET value = 'not json' WHERE key = 'rotation_anchor'")
    c.commit()
    try:
        with redirect_stdout(io.StringIO()):
            log.cmd_doctor()
        assert False, "should have exited"
    except SystemExit as e:
        assert e.code == 1
