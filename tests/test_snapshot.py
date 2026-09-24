#!/usr/bin/env python3
"""Snapshot v2: views, not raw tables. Golden tests with literal oracles."""

import pytest
from conftest import close_session, seed_lift, seed_split

from reps.errors import RepsError


def _seeded(log):
    log.set_exercise_mapping("bench", "chest")
    log.set_exercise_mapping("row", "back")
    log.set_split("Upper A", 1, "bench", 3)
    log.set_split("Lower A", 1, "row", 3)
    log.set_rotation(["Upper A", "Lower A", "rest"])
    return log


def test_export_v2_shape(log_module):
    """Every v2 top-level view exists and validates (extra=forbid)."""
    snap = log_module.export_snapshot()
    assert snap["schema_version"] == 2
    for key in ["as_of", "constants", "lifts", "muscles", "sessions", "calendar",
                "volume_history", "bodyweight", "program", "next_up", "goals",
                "adherence", "signals", "recent_notes", "rules", "flags",
                "deload", "priority", "autoreg", "autoreg_changes"]:
        assert key in snap, f"snapshot missing '{key}'"
    assert "workouts" not in snap and "sets" not in snap


def test_export_v2_survives_empty_db(log_module, tmp_path, monkeypatch):
    """A fresh DB still exports the full schema with empty views."""
    import sqlite3
    fresh = str(tmp_path / "fresh.db")
    monkeypatch.setattr("reps.db.DB", fresh)
    c = sqlite3.connect(fresh)
    c.executescript(log_module.SCHEMA)
    c.execute("INSERT INTO schema_version (version) VALUES (?)", (log_module.SCHEMA_VERSION,))
    c.commit()
    c.close()
    snap = log_module.export_snapshot()
    assert snap["lifts"] == [] and snap["sessions"] == []
    assert snap["next_up"]["empty"] == "log a session and the next slot appears here"
    assert snap["adherence"] is None and snap["autoreg"]["permitted"] is False


def test_pr_flags_first_set_baseline(log_module):
    """PR definition: first set per lift is baseline, later sets need strictly greater e1RM."""
    log = log_module
    _seeded(log)
    log.start_workout("d1")
    log.log_set("bench", 100, 5, "", "chest")  # e1RM 116.7 baseline
    log.log_set("bench", 100, 5, "", "chest")  # tie, not a PR
    log.log_set("bench", 100, 6, "", "chest")  # 120.0, PR
    close_session(log, "d1")
    prs = log.session_prs(1)["prs"]
    assert [p["is_pr"] for p in prs] == [False, False, True]
    lift = next(l for l in log.export_snapshot()["lifts"] if l["exercise"] == "bench")
    assert lift["sessions"][0]["is_pr"] is True  # session top set was the PR
    assert lift["sessions"][0]["e1rm"] == 120.0
    assert lift["last_pr_date"] == lift["sessions"][0]["date"]
    assert lift["best"]["e1rm"] == 120.0


def test_lift_view_numbers(log_module):
    log = log_module
    _seeded(log)
    log.start_workout("d1")
    log.log_set("bench", 100, 5, "", "chest")
    close_session(log, "d1")
    lift = next(l for l in log.export_snapshot()["lifts"] if l["exercise"] == "bench")
    assert lift["muscles"] == ["chest"]
    assert lift["best"] == {"weight": 100, "reps": 5, "e1rm": 116.7,
                            "date": lift["best"]["date"]}
    assert lift["last"]["weight"] == 100 and lift["last"]["reps"] == 5
    assert lift["days_since_pr"] is None  # no PR yet, only baseline
    assert lift["progression"]["verdict"] == "baseline"


def test_stall_and_slip_tags(log_module):
    """Stall: window within 1% with no progress; slip: two drops at deload_watch_pct."""
    log = log_module
    assert log.is_stalling([100, 100.5, 100.2, 100.4],
                            {"stall_window_sessions": 3, "stall_decline_pct": 1.0,
                             "stall_flat_sessions": 6, "stall_min_sessions": 4}) is True
    assert log.is_stalling([100, 105, 110, 115],
                            {"stall_window_sessions": 3, "stall_decline_pct": 1.0,
                             "stall_flat_sessions": 6, "stall_min_sessions": 4}) is False
    assert log.is_slipping([100, 94, 88], {"deload_watch_pct": -5}) == {
        "drops_pct": [-6.0, -6.4]}
    assert log.is_slipping([100, 98, 97], {"deload_watch_pct": -5}) is None


def test_week_bucketing_monday_start(log_module):
    from datetime import date
    assert log_module.week_start_of("2026-09-24") == "2026-09-21"  # Thursday -> Monday
    assert log_module.week_start_of("2026-09-21") == "2026-09-21"
    assert log_module.week_starts(1)[-1] == log_module.monday_of(date.today()).isoformat()
    assert log_module.weekly_counts(["2026-09-22", "2026-09-23", "2026-09-14"],
                                    ["2026-09-14", "2026-09-21"]) == [1, 2]


def test_slot_tie_is_ambiguous(log_module):
    m = log_module.slot_of_session(["bench", "row"],
                                    {"Upper A": ["bench"], "Lower A": ["row"]})
    assert m == {"day": None, "candidates": ["Lower A", "Upper A"], "score": 1}
    assert log_module.next_slot("Upper A", ["Upper A", "rest", "Lower A"]) == {
        "day": "Lower A",
        "basis": "last trained Upper A, rotation Upper A->Lower A (rest day sits between)"}


def test_e1rm_formula_and_udf(log_module):
    """Independent oracle: hand-computed Epley values, plus UDF wiring."""
    assert log_module.e1rm(100, 1) == 100
    assert log_module.e1rm(100, 5) == 116.66666666666667
    assert log_module.e1rm(80, 10) == 106.66666666666666
    c = log_module.conn()
    row = c.execute("SELECT e1rm(100, 5) AS v").fetchone()
    assert abs(row["v"] - log_module.e1rm(100, 5)) < 1e-9


def test_next_up_and_program_view(log_module):
    log = log_module
    _seeded(log)
    log.start_workout("d1")
    log.log_set("bench", 100, 5, "", "chest")
    log.set_progression("bench", "baseline", 102.5, 5, "flat")
    close_session(log, "d1")
    snap = log.export_snapshot()
    assert snap["next_up"]["day"] == "Lower A"
    assert snap["next_up"]["rows"][0]["movement"] == "row"
    assert snap["next_up"]["rows"][0]["last"] is None
    assert [d["day"] for d in snap["program"]["days"]] == ["Upper A", "Lower A"]
    assert snap["program"]["rotation"] == ["Upper A", "Lower A", "rest"]
    upper = next(d for d in snap["program"]["days"] if d["day"] == "Upper A")
    assert upper["slots"][0]["moves"] == ["bench"]
    assert upper["muscles"] == ["chest"]


def test_goal_percent_and_top_by_date(log_module):
    from datetime import date, timedelta
    log = log_module
    _seeded(log)
    log.start_workout("d1")
    log.log_set("bench", 100, 5, "", "chest")  # 116.7
    close_session(log, "d1")
    deadline = (date.today() + timedelta(days=60)).isoformat()
    log.add_goal("bench", 130, deadline, "", 116.7)
    goal = next(g for g in log.export_snapshot()["goals"] if g["exercise"] == "bench")
    assert goal["percent"] == 0.0  # first actual is the trajectory anchor
    assert set(goal["top_by_date"]) == {goal["actuals"][0]["date"]}
    top = goal["top_by_date"][goal["actuals"][0]["date"]]
    assert top == {"weight": 100, "reps": 5}


def test_bodyweight_avg_and_gap(log_module):
    from datetime import date, timedelta
    log = log_module
    c = log.conn()
    d0 = (date.today() - timedelta(days=10)).isoformat()
    d1 = (date.today() - timedelta(days=9)).isoformat()
    c.execute("INSERT INTO bodyweight (date, kg, note) VALUES (?, 80, '')", (d0,))
    c.execute("INSERT INTO bodyweight (date, kg, note) VALUES (?, 82, '')", (d1,))
    c.commit()
    bw = log.export_snapshot()["bodyweight"]
    assert bw[0] == {"date": d0, "kg": 80, "avg7": 80.0, "gap_before": None, "gap": False}
    assert bw[1] == {"date": d1, "kg": 82, "avg7": 81.0, "gap_before": 1, "gap": False}


def test_adherence_weeks_and_calendar(log_module):
    from datetime import date, timedelta
    log = log_module
    _seeded(log)
    log.anchor_rotation((date.today() - timedelta(days=3)).isoformat(), "Upper A")
    snap = log.export_snapshot()
    assert snap["adherence"]["weeks"][-1]["expected"] >= 1
    kinds = {d["kind"] for d in snap["calendar"]}
    assert kinds <= {"trained", "rest", "missed", "empty"}
    assert all("hover" in d and isinstance(d["hover"]["lines"], list)
               for d in snap["calendar"])


def test_payload_budget(log_module):
    """3 years of daily training must stay under 1.5 MB of JSON.

    6 sessions a week, 10 sets each, with rest days exercising the
    rest/missed calendar paths like a real program."""
    import json
    from datetime import date, timedelta
    log = log_module
    c = log.conn()
    seed_lift(c, "bench", "chest")
    base = date.today() - timedelta(days=3 * 365)
    for i in range(3 * 365):
        d = base + timedelta(days=i)
        if d.weekday() == 6:
            c.execute("INSERT INTO workouts (date, status, notes) VALUES (?, 'rest', '')",
                      (d.isoformat(),))
            continue
        iso = d.isoformat()
        wid = c.execute("INSERT INTO workouts (date, status, notes) VALUES (?, 'done', '')",
                        (iso,)).lastrowid
        for n in range(10):
            c.execute("INSERT INTO sets (workout_id, exercise, weight, reps, note, created) "
                      "VALUES (?, 'bench', ?, 5, '', ?)", (wid, 60 + (i % 40), iso + "T10:00:00"))
    c.commit()
    snap = log.export_snapshot()
    size = len(json.dumps(snap))
    assert size < 1_500_000, f"snapshot payload {size} exceeds 1.5 MB budget"
