"""Rotation adherence: what the rotation prescribed per date vs what happened.

One rotation slot equals one calendar day, the same pricing
sessions_possible_before already uses for cycle length. Pure derivation from
the rotation array plus one stored anchor, no new tables.
"""

import json
from datetime import date, timedelta

from .errors import RepsError

from .constants import load_constants
from .db import conn
from .program import get_rotation, parse_rotation, split_day_order
from .slots import slot_of_session


def is_rest_day(name):
    return name.strip().lower() == "rest"


def parse_anchor(raw, rotation):
    """Validate a stored anchor. Returns (anchor, problem): anchor is None
    when missing or invalid, problem is None when valid. Missing (no row)
    is not a problem, it just disables adherence.

    Accepts the {"date", "index"} dict from the rotation_anchor table or a
    raw JSON string (input-boundary tolerance)."""
    if not raw:
        return None, None
    malformed = (None, "rotation_anchor must be {\"date\": \"YYYY-MM-DD\", \"index\": <int>} "
                       "(anchor the rotation again)")
    try:
        anchor = json.loads(raw) if isinstance(raw, str) else raw
    except ValueError:
        return malformed
    if not isinstance(anchor, dict) or not isinstance(anchor.get("date"), str):
        return malformed
    try:
        day = date.fromisoformat(anchor["date"]).isoformat()
    except ValueError:
        return malformed
    index = anchor.get("index")
    if not isinstance(index, int) or isinstance(index, bool) or index < 0:
        return malformed
    if date.fromisoformat(day) > date.today():
        return None, f"rotation_anchor date {day} is in the future"
    if not rotation or index >= len(rotation):
        return None, (f"rotation_anchor index {index} is out of range "
                        f"for the current rotation (anchor the rotation again)")
    return {"date": day, "index": index}, None


def get_anchor(c):
    """Parsed rotation_anchor or None when missing, corrupt, or out of range."""
    row = c.execute("SELECT anchor_date, position FROM rotation_anchor WHERE id = 1").fetchone()
    raw = {"date": row["anchor_date"], "index": row["position"]} if row else None
    anchor, _ = parse_anchor(raw, parse_rotation(c))
    return anchor


def expected_day(rotation, anchor, day_iso):
    """Rotation entry prescribed for a date. Pure function of the anchor."""
    delta = (date.fromisoformat(day_iso) - date.fromisoformat(anchor["date"])).days
    return rotation[(anchor["index"] + delta) % len(rotation)]


def trained_exercises(c, day_iso):
    """Distinct exercises in done sessions on a date.

    Done only: an open in-progress workout must not flip the day to done
    before `end`, and rest rows carry no sets. Matches the slot guess, which
    also reads the last done session.
    """
    return {r["exercise"] for r in c.execute(
        "SELECT DISTINCT s.exercise FROM sets s JOIN workouts w ON w.id = s.workout_id "
        "WHERE w.date = ? AND w.status = 'done'", (day_iso,)).fetchall()}


def match_day(c, trained):
    """Best-matching split day for a trained set. Ties and no-overlap give None.

    A tie means the session is ambiguous, so it resolves to swapped downstream
    instead of crediting one of the tied days as done. One tie rule, owned
    by reps/slots.py.
    """
    from .program import parse_active_split_days
    if not trained:
        return None
    match = slot_of_session(list(trained), parse_active_split_days(c))
    return match["day"]


def classify_date(c, rotation, anchor, day_iso):
    """One adherence verdict for a date (see rotation status)."""
    exp = expected_day(rotation, anchor, day_iso)
    trained = trained_exercises(c, day_iso)
    rest_row = c.execute("SELECT id FROM workouts WHERE date = ? AND status = 'rest'",
                         (day_iso,)).fetchone() is not None
    if trained:
        matched = match_day(c, trained)
        if is_rest_day(exp):
            status = "extra"
        elif matched is not None and matched.lower() == exp.lower():
            status = "done"
        else:
            status = "swapped"
    elif rest_row:
        status = "rest_ok" if is_rest_day(exp) else "rest_logged"
    else:
        status = "rest_ok" if is_rest_day(exp) else "missed"
    return {"date": day_iso, "expected": exp,
            "trained": match_day(c, trained) if trained else None, "status": status}


def status_range(c, rotation, anchor, from_iso, to_iso):
    """Classify every date in [from, to] inclusive."""
    out = []
    day = date.fromisoformat(from_iso)
    end = date.fromisoformat(to_iso)
    while day <= end:
        out.append(classify_date(c, rotation, anchor, day.isoformat()))
        day += timedelta(days=1)
    return out


def drift_days(statuses):
    """Trailing run of non-done days. Rest days count as non-done literally:
    in a sane rotation they break runs on their own, so a long run means
    real deviation, not scheduled rest."""
    run = 0
    for entry in reversed(statuses):
        if entry["status"] == "done":
            break
        run += 1
    return run


def adherence_block(c, window_days=14):
    """Plan's adherence section, or None when anchor or rotation is missing.

    Windows start at the anchor at the earliest: dates before the program
    existed are unscored, never missed.
    """
    rotation = parse_rotation(c)
    anchor = get_anchor(c)
    if not rotation or anchor is None:
        return None
    today = date.today()
    start = max((today - timedelta(days=window_days - 1)).isoformat(), anchor["date"])
    days = status_range(c, rotation, anchor, start, today.isoformat())
    vol_weeks = load_constants().thresholds.volume_window_weeks
    freq_start = max((today - timedelta(days=vol_weeks * 7 - 1)).isoformat(), anchor["date"])
    window = status_range(c, rotation, anchor, freq_start, today.isoformat())
    frequency = {}
    for day in split_day_order("active", c=c):
        expected = [e for e in window if e["expected"].lower() == day.lower()]
        frequency[day] = {"expected": len(expected),
                          "done": sum(1 for e in expected if e["status"] == "done")}
    threshold = load_constants().thresholds.adherence_drift_days
    run = drift_days(days)
    return {"anchor": anchor, "days": days, "frequency": frequency,
            "drift": run >= threshold, "drift_days": run, "drift_threshold": threshold}


def adherence_snapshot(c):
    """Dashboard slice: anchor plus per-date verdicts over the volume window.

    None when anchor or rotation is missing; the worker ignores it either way.
    """
    rotation = parse_rotation(c)
    anchor = get_anchor(c)
    if not rotation or anchor is None:
        return None
    today = date.today()
    span = load_constants().thresholds.volume_window_weeks * 7
    start = max((today - timedelta(days=span - 1)).isoformat(), anchor["date"])
    days = status_range(c, rotation, anchor, start, today.isoformat())
    threshold = load_constants().thresholds.adherence_drift_days
    run = drift_days(days)
    return {"anchor": anchor, "days": days, "drift": run >= threshold,
            "drift_days": run, "drift_threshold": threshold}


def expectation_context(c, rotation, anchor, today_iso, lookback=90):
    """Expected today plus the last done day and missed days since, for the slot guess.

    The done search reaches back up to lookback days, but the missed list is
    capped at the last 14 so the basis line stays readable on stale anchors.
    """
    exp = expected_day(rotation, anchor, today_iso)
    today = date.fromisoformat(today_iso)
    hist = status_range(c, rotation, anchor,
                        (today - timedelta(days=lookback)).isoformat(), today_iso)
    done = [e for e in hist if e["status"] == "done"]
    last = done[-1] if done else None
    recent_from = (today - timedelta(days=13)).isoformat()
    if last is None:
        # Never trained: nothing was skipped, so nothing is missed.
        missed = []
    else:
        missed = [e for e in hist if e["status"] == "missed" and e["date"] >= recent_from
                  and e["date"] > last["date"]]
    return {"day": exp,
            "last_done": {"date": last["date"], "day": last["expected"]} if last else None,
            "missed": [{"date": e["date"], "day": e["expected"]} for e in missed]}


def anchor_rotation(date_str, day):
    """Pin the rotation schedule: on <date> the rotation was at <day>.

    Day resolves to the first matching rotation index (case-insensitive).
    """
    c = conn()
    try:
        on = date.fromisoformat((date_str or "").strip()).isoformat()
    except ValueError:
        raise RepsError("anchor date must be YYYY-MM-DD")
    if date.fromisoformat(on) > date.today():
        raise RepsError("anchor date cannot be in the future")
    rotation = parse_rotation(c)
    if not rotation:
        raise RepsError("no rotation to anchor (set the rotation first)")
    match = next((i for i, d in enumerate(rotation) if d.lower() == (day or "").strip().lower()), None)
    if match is None:
        raise RepsError(f"'{day}' matches no rotation entry")
    anchor = {"date": on, "index": match}
    c.execute("INSERT INTO rotation_anchor (id, anchor_date, position) VALUES (1, ?, ?) "
              "ON CONFLICT (id) DO UPDATE SET anchor_date = excluded.anchor_date, "
              "position = excluded.position", (on, match))
    c.commit()
    return {"anchor": anchor, "day": rotation[match]}


def get_rotation_status(from_iso=None, to_iso=None):
    """Adherence verdicts per date over a range (default: last 14 days).

    Entries stop at today: future dates have nothing to classify.
    """
    c = conn()
    rotation = parse_rotation(c)
    anchor = get_anchor(c)
    if not rotation or anchor is None:
        if c.execute("SELECT 1 FROM rotation_anchor WHERE id = 1").fetchone():
            raise RepsError("the rotation schedule anchor is set but invalid")
        raise RepsError("rotation adherence needs a rotation and an anchor")
    today = date.today().isoformat()
    try:
        to_iso = date.fromisoformat(to_iso).isoformat() if to_iso else today
        from_iso = date.fromisoformat(from_iso).isoformat() if from_iso else \
            (date.fromisoformat(to_iso) - timedelta(days=13)).isoformat()
    except ValueError:
        raise RepsError("status dates must be YYYY-MM-DD")
    to_iso = min(to_iso, today)
    if from_iso > to_iso:
        return []
    return status_range(c, rotation, anchor, from_iso, to_iso)
