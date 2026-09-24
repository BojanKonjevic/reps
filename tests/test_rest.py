#!/usr/bin/env python3
"""pytest suite for rest days: special sessions without movements."""

from datetime import date, timedelta

from conftest import close_session
from reps.errors import RepsError


def test_rest_creates_rest_row(log_module):
    """rest creates a rest-status workout with the note."""
    c = log_module.conn()
    out = log_module.mark_rest(date.today().isoformat(), "sore")
    assert out["appended"] is False
    row = c.execute("SELECT * FROM workouts WHERE id = ?", (out["rest_id"],)).fetchone()
    assert row["status"] == "rest"
    assert row["notes"] == "sore"


def test_rest_repeat_without_note_reports_noop(log_module):
    """Repeating rest with no new note changes nothing and says so."""
    c = log_module.conn()
    today = date.today().isoformat()
    log_module.mark_rest(today, "sore")
    out = log_module.mark_rest(today, "")
    assert out["appended"] is False
    row = c.execute("SELECT notes FROM workouts").fetchone()
    assert row["notes"] == "sore"


def test_rest_rejects_bad_date_cleanly(log_module):
    """Direct calls with garbage dates exit cleanly, no traceback."""
    try:
        log_module.mark_rest("not-a-date", "sore")
        assert False, "should have exited"
    except RepsError as e:
        assert "date must be yyyy-mm-dd" in str(e).lower()


def test_rest_second_call_appends_note(log_module):
    """Marking rest twice appends the note instead of duplicating the row."""
    c = log_module.conn()
    today = date.today().isoformat()
    first = log_module.mark_rest(today, "sore")
    second = log_module.mark_rest(today, "tired")
    assert second["appended"] is True
    assert second["rest_id"] == first["rest_id"]
    row = c.execute("SELECT * FROM workouts WHERE id = ?", (first["rest_id"],)).fetchone()
    assert row["notes"] == "sore tired"
    assert c.execute("SELECT COUNT(*) n FROM workouts").fetchone()["n"] == 1


def test_rest_refused_with_open_workout(log_module):
    """Cannot mark rest mid-session."""
    log_module.start_workout("test")
    try:
        log_module.mark_rest(date.today().isoformat(), "tired")
        assert False, "should have exited"
    except RepsError as e:
        assert "open workout" in str(e).lower()


def test_rest_refused_when_trained_today(log_module):
    """A trained day cannot be rewritten as rest."""
    log_module.start_workout("test")
    log_module.log_set("bench", 100, 5, "", "chest")
    close_session(log_module, "done")
    try:
        log_module.mark_rest(date.today().isoformat(), "tired")
        assert False, "should have exited"
    except RepsError as e:
        assert "already trained" in str(e).lower()


def test_rest_refused_for_future_date(log_module):
    """Rest is a record, not a plan."""
    future = (date.today() + timedelta(days=1)).isoformat()
    try:
        log_module.mark_rest(future, "planned")
        assert False, "should have exited"
    except RepsError as e:
        assert "future" in str(e).lower()


def test_rest_accepts_past_date(log_module):
    """Backfilling rest days (travel, sick) works."""
    c = log_module.conn()
    past = (date.today() - timedelta(days=3)).isoformat()
    out = log_module.mark_rest(past, "travel")
    assert out["date"] == past
    row = c.execute("SELECT * FROM workouts WHERE id = ?", (out["rest_id"],)).fetchone()
    assert row["status"] == "rest"


def test_start_still_works_on_rest_day(log_module):
    """Plans change: training on a marked rest day is allowed."""
    c = log_module.conn()
    log_module.mark_rest(date.today().isoformat(), "was going to rest")
    out = log_module.start_workout("changed mind")
    assert out["reused"] is False
    log_module.log_set("bench", 100, 5, "", "chest")
    assert c.execute("SELECT COUNT(*) n FROM sets").fetchone()["n"] == 1


def test_update_workout_to_rest_guards(log_module):
    """Empty workouts can become rest, workouts with sets cannot."""
    c = log_module.conn()
    log_module.start_workout("empty")
    close_session(log_module, "done")
    wid = c.execute("SELECT id FROM workouts").fetchone()["id"]
    log_module.update_workout(str(wid), "status", "rest")
    assert c.execute("SELECT status FROM workouts WHERE id = ?", (wid,)).fetchone()["status"] == "rest"

    log_module.start_workout("full")
    log_module.log_set("bench", 100, 5, "", "chest")
    close_session(log_module, "done")
    wid2 = c.execute("SELECT id FROM workouts WHERE status = 'done'").fetchone()["id"]
    try:
        log_module.update_workout(str(wid2), "status", "rest")
        assert False, "should have exited"
    except RepsError as e:
        assert "has sets" in str(e).lower()


def test_stats_and_context_exclude_rest(log_module):
    """Rest days are not counted as sessions."""
    log_module.mark_rest(date.today().isoformat(), "sore")
    log_module.start_workout("test")
    log_module.log_set("bench", 100, 5, "", "chest")
    close_session(log_module, "done")
    stats = log_module.get_stats()
    assert stats["workouts"] == 1
    ctx = log_module.get_context("5")
    assert ctx["workouts_total"] == 1


def test_calendar_marks_rest_days(log_module):
    """Calendar flags all-rest dates distinctly from absence and sessions."""
    c = log_module.conn()
    log_module.mark_rest(date.today().isoformat(), "sore")
    out = log_module.get_calendar()
    today_entry = next(d for d in out["dates"] if d["date"] == date.today().isoformat())
    assert today_entry["rest"] is True
    assert today_entry["sets"] == 0


def test_today_reports_rest_entry(log_module):
    """today surfaces the rest note so the agent knows the day is spoken for."""
    log_module.mark_rest(date.today().isoformat(), "sore legs")
    out = log_module.get_today()
    assert out["open"] is False
    assert out["rest"]["notes"] == "sore legs"


def test_delete_workout_removes_rest_row(log_module):
    """Rest rows are removed explicitly like any workout."""
    c = log_module.conn()
    out = log_module.mark_rest(date.today().isoformat(), "sore")
    log_module.delete_workout(str(out["rest_id"]))
    assert c.execute("SELECT COUNT(*) n FROM workouts").fetchone()["n"] == 0


def test_update_workout_to_rest_refuses_duplicate_rest_row(log_module):
    """The update path cannot double up a rest row created via rest."""
    c = log_module.conn()
    log_module.mark_rest(date.today().isoformat(), "sore")
    log_module.start_workout("empty")
    close_session(log_module, "done")
    wid = c.execute("SELECT id FROM workouts WHERE status = 'done'").fetchone()["id"]
    try:
        log_module.update_workout(str(wid), "status", "rest")
        assert False, "should have exited"
    except RepsError as e:
        assert "already has a rest row" in str(e).lower()
    assert c.execute("SELECT COUNT(*) n FROM workouts WHERE status = 'rest'").fetchone()["n"] == 1
