#!/usr/bin/env python3
"""Dashboard temporal read model: described history events, folded training
states per event date, coverage dates, and backend-owned observation defs."""

from datetime import date, timedelta

import pytest

from reps.errors import RepsError
from conftest import close_session


def _seeded(log):
    log.set_exercise_mapping("squat", "quads")
    log.set_split("Lower A", 1, "squat", 3)
    log.start_workout("legs")
    log.log_set("squat", 100, 5, "", "quads")
    log.set_progression("squat", "baseline", 102.5, 5, "flat", "")
    close_session(log, "leg day")
    return log


def test_observation_defs_match_observe_provenance(log_module):
    """The embedded defs are the exact strings observe() reports: one owner."""
    log = _seeded(log_module)
    defs = {d["metric"]: d for d in log.observation_defs()}
    assert sorted(defs) == ["adherence_summary", "bodyweight_trend", "goal_trajectory",
                            "lift_trend", "muscle_volume", "program_activity"]
    today = date.today().isoformat()
    since = (date.today() - timedelta(days=90)).isoformat()
    for metric, subject in [("lift_trend", "squat"), ("muscle_volume", "quads"),
                            ("program_activity", ""), ("bodyweight_trend", ""),
                            ("adherence_summary", "")]:
        try:
            out = log.observe(metric, subject, since, today)
        except RepsError:
            continue  # adherence needs rotation+anchor; def still embedded
        assert out["provenance"]["sources"] == defs[metric]["sources"]
        assert out["provenance"]["definition"] == defs[metric]["definition"]
    assert defs["lift_trend"]["subject_kind"] == "exercise"


def test_history_events_are_described(log_module):
    """Titles, summaries, and relevance hints with literal oracles."""
    log = _seeded(log_module)
    log.set_split("Lower A", 1, "squat", 2, evidence="repeated performance drop")
    log.set_priority("quads", "priority", evidence="bring up")
    snap = log.export_snapshot()
    by_title = {e["title"]: e for e in snap["history"]}
    assert by_title["Lower A changed"]["summary"] == "squat: 3 sets -> 2 sets"
    assert by_title["Lower A changed"]["affects_exercises"] == ["squat"]
    assert by_title["Lower A changed"]["affects_muscles"] == ["quads"]
    assert by_title["Lower A changed"]["affects_days"] == ["Lower A"]
    assert by_title["Lower A changed"]["evidence"] == "repeated performance drop"
    assert by_title["Quads priority changed"]["summary"] == "unset -> priority"
    assert by_title["Quads priority changed"]["affects_muscles"] == ["quads"]
    assert by_title["Quads priority changed"]["affects_exercises"] == []


def test_goal_event_titles_and_summaries(log_module):
    log = _seeded(log_module)
    deadline = (date.today() + timedelta(days=60)).isoformat()
    gid = log.add_goal("squat", 135, deadline, "", None, evidence="new cycle")["goal_id"]
    log.rewrite_goal(gid, evidence="slipped")
    snap = log.export_snapshot()
    goal_events = [e for e in snap["history"] if e["domain"] == "goal"]
    assert [e["title"] for e in goal_events] == ["Squat goal set", "Squat goal revised"]
    assert goal_events[0]["summary"].startswith("target 135 e1RM by ")
    assert goal_events[0]["affects_exercises"] == ["squat"]
    assert goal_events[1]["evidence"] == "slipped"


def test_history_states_fold_to_event_dates(log_module):
    """The bundle carries backend-folded states, never today's live edits."""
    log = _seeded(log_module)
    log.set_split("Lower A", 1, "squat", 2, evidence="trim")
    log.set_priority("quads", "priority")
    snap = log.export_snapshot()
    assert len(snap["history_states"]) == 1
    st = snap["history_states"][0]
    assert st["date"] == date.today().isoformat()
    assert st["program"] == [{"day": "Lower A",
                              "slots": [{"slot": 1, "movements": "squat", "sets": 2}],
                              "known": True, "first_date": date.today().isoformat()}]
    tiers = {p["muscle"]: p for p in st["priorities"]}
    assert tiers["quads"]["tier"] == "priority" and tiers["quads"]["known"] is True
    assert tiers["chest"] == {"muscle": "chest", "tier": "maintain", "since": None,
                              "until": None, "known": False, "first_date": None}
    assert st["rotation"] is None and st["rotation_known"] is False
    assert st["deloads"] == []


def test_training_state_unknown_before_history(log_module):
    """Pre-history dates report unknown program state, maintain priority."""
    log = _seeded(log_module)
    log.set_split("Lower A", 1, "squat", 2)
    old = (date.today() - timedelta(days=30)).isoformat()
    st = log.training_state_at(old)
    assert st["program"] == [{"day": "Lower A", "slots": [], "known": False,
                              "first_date": date.today().isoformat()}]
    tiers = {p["muscle"]: p for p in st["priorities"]}
    assert tiers["quads"] == {"muscle": "quads", "tier": "maintain", "since": None,
                              "until": None, "known": False, "first_date": None}
    with pytest.raises(RepsError):
        log.training_state_at("not-a-date")
    cov = {(e["domain"], e["subject"]): e["first_date"] for e in log.coverage()}
    assert cov[("program", "active:Lower A")] == date.today().isoformat()


def test_reversal_linkage_survives_snapshot(log_module):
    """Append-only truth in the read model: the inverse is a new row pointing back."""
    log = _seeded(log_module)
    cid = log.set_split("Lower A", 1, "squat", 2)["change_id"]
    log.revert_change(cid, evidence="too aggressive")
    snap = log.export_snapshot()
    by_id = {e["id"]: e for e in snap["history"]}
    assert by_id[cid]["superseded_by"] is not None
    inverse = by_id[by_id[cid]["superseded_by"]]
    assert inverse["reverses"] == cid
    assert inverse["summary"] == "squat: 2 sets -> 3 sets"


def test_empty_db_history_is_honest(log_module, tmp_path, monkeypatch):
    import sqlite3
    fresh = str(tmp_path / "fresh.db")
    monkeypatch.setattr("reps.db.DB", fresh)
    c = sqlite3.connect(fresh)
    c.executescript(log_module.SCHEMA)
    c.execute("INSERT INTO schema_version (version) VALUES (?)", (log_module.SCHEMA_VERSION,))
    c.commit()
    c.close()
    snap = log_module.export_snapshot()
    assert snap["history"] == [] and snap["history_states"] == []
    assert snap["history_coverage"] == []
    assert len(snap["observation_defs"]) == 6


def test_deload_state_folds_to_event_dates(log_module):
    """Deload set/clear transitions describe and fold like other domains."""
    log = _seeded(log_module)
    log.set_deload("lift", "squat", evidence="beat up")
    snap = log.export_snapshot()
    deload_events = [e for e in snap["history"] if e["domain"] == "deload"]
    assert [(e["title"], e["summary"]) for e in deload_events] == [
        ("Squat deload started", "training volume down until cleared")]
    assert deload_events[0]["affects_exercises"] == ["squat"]
    st = snap["history_states"][0]
    assert st["deloads"] == [{"scope": "lift", "subject": "squat", "active": True,
                              "known": True, "first_date": date.today().isoformat()}]
    log.clear_deload(evidence="fresh again")
    snap = log.export_snapshot()
    st = snap["history_states"][0]
    assert st["deloads"] == [{"scope": "lift", "subject": "squat", "active": False,
                              "known": True, "first_date": date.today().isoformat()}]
