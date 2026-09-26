#!/usr/bin/env python3
"""Temporal contract: a change dated D is active on D and thereafter until
superseded. training_state_at answers for any date; selecting the bundle at
the latest event date at or before D is provably the same fold."""

from datetime import date

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


def _backdate(log, change_id, day):
    c = log.conn()
    c.execute("UPDATE state_change SET date = ? WHERE id = ?", (day, change_id))
    c.commit()


def _program_slots(log, day):
    st = log.training_state_at(day)
    days = {d["day"]: d for d in st["program"]}
    assert days["Lower A"]["known"] is True
    return days["Lower A"]["slots"]


def test_change_active_on_its_date_and_after(log_module):
    """change Sep 01, query Sep 01 -> new; query Sep 05 -> new."""
    log = _seeded(log_module)
    cid = log.set_split("Lower A", 1, "squat", 2)["change_id"]
    _backdate(log, cid, "2026-09-01")
    assert _program_slots(log, "2026-09-01") == [
        {"slot": 1, "movements": "squat", "sets": 2}]
    assert _program_slots(log, "2026-09-05") == [
        {"slot": 1, "movements": "squat", "sets": 2}]


def test_later_change_does_not_leak_backward(log_module):
    """With Sep 01 then Sep 10 changes: query Sep 05 -> Sep 01 state."""
    log = _seeded(log_module)
    old = log.set_split("Lower A", 1, "squat", 4)["change_id"]
    new = log.set_split("Lower A", 1, "squat", 2)["change_id"]
    _backdate(log, old, "2026-09-01")
    _backdate(log, new, "2026-09-10")
    assert _program_slots(log, "2026-09-05") == [
        {"slot": 1, "movements": "squat", "sets": 4}]
    assert _program_slots(log, "2026-09-10") == [
        {"slot": 1, "movements": "squat", "sets": 2}]


def test_multiple_changes_fold_in_order(log_module):
    """Sep 01 -> A, Sep 05 -> B, Sep 10 -> C across queries."""
    log = _seeded(log_module)
    a = log.set_split("Lower A", 1, "squat", 4)["change_id"]
    b = log.set_split("Lower A", 1, "squat", 5)["change_id"]
    c = log.set_split("Lower A", 1, "squat", 6)["change_id"]
    _backdate(log, a, "2026-09-01")
    _backdate(log, b, "2026-09-05")
    _backdate(log, c, "2026-09-10")
    want = {"2026-09-04": 4, "2026-09-05": 5, "2026-09-09": 5, "2026-09-10": 6}
    for day, sets in want.items():
        assert _program_slots(log, day) == [
            {"slot": 1, "movements": "squat", "sets": sets}], day


def test_pre_history_is_unknown_not_old(log_module):
    log = _seeded(log_module)
    cid = log.set_split("Lower A", 1, "squat", 2)["change_id"]
    _backdate(log, cid, "2026-09-10")
    st = log.training_state_at("2026-09-05")
    days = {d["day"]: d for d in st["program"]}
    assert days["Lower A"] == {"day": "Lower A", "slots": [], "known": False,
                               "first_date": "2026-09-10"}
    with pytest.raises(RepsError):
        log.training_state_at("Sep 05")


def test_bundle_selection_matches_direct_fold(log_module):
    """For any date D past the first event, training_state_at(D) equals the
    bundle folded at the latest event date at or before D. The dashboard's
    date-to-bundle selection is transport over this equivalence."""
    from datetime import timedelta
    log = _seeded(log_module)
    a = log.set_split("Lower A", 1, "squat", 4)["change_id"]
    b = log.set_priority("quads", "priority")["change_id"]
    c = log.set_split("Lower A", 1, "squat", 6)["change_id"]
    _backdate(log, a, "2026-09-01")
    _backdate(log, b, "2026-09-05")
    _backdate(log, c, "2026-09-10")
    events = sorted({d for d in ("2026-09-01", "2026-09-05", "2026-09-10")})
    day = date(2026, 8, 31)
    while day <= date(2026, 9, 11):
        iso = day.isoformat()
        past = [e for e in events if e <= iso]
        if not past:
            st = log.training_state_at(iso)
            assert {d["day"]: d["known"] for d in st["program"]} == {"Lower A": False}
        else:
            direct, folded = log.training_state_at(iso), log.training_state_at(past[-1])
            assert direct.pop("date") == iso and folded.pop("date") == past[-1]
            assert direct == folded, iso
        day += timedelta(days=1)
