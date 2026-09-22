"""Rotation adherence: what the rotation prescribed per date vs what happened.

One rotation slot equals one calendar day, the same pricing
sessions_possible_before already uses for cycle length. Pure derivation from
the rotation array plus one stored anchor, no new tables.
"""

import json
import sys
from datetime import date, timedelta

from .constants import load_constants
from .db import conn
from .program import day_movements, meta_get, parse_rotation, split_day_order


def is_rest_day(name):
    return name.strip().lower() == "rest"


def get_anchor(c):
    """Parsed rotation_anchor or None when missing, corrupt, or out of range."""
    raw = meta_get(c, "rotation_anchor")
    if not raw:
        return None
    try:
        anchor = json.loads(raw)
    except ValueError:
        return None
    if not isinstance(anchor, dict):
        return None
    try:
        day = date.fromisoformat(anchor["date"]).isoformat()
        index = anchor["index"]
    except (KeyError, TypeError, ValueError):
        return None
    if not isinstance(index, int) or isinstance(index, bool) or index < 0:
        return None
    rotation = parse_rotation(c)
    if not rotation or index >= len(rotation):
        return None
    return {"date": day, "index": index}


def expected_day(rotation, anchor, day_iso):
    """Rotation entry prescribed for a date. Pure function of the anchor."""
    delta = (date.fromisoformat(day_iso) - date.fromisoformat(anchor["date"])).days
    return rotation[(anchor["index"] + delta) % len(rotation)]


def trained_exercises(c, day_iso):
    """Distinct exercises logged on a date (rest rows carry no sets)."""
    return {r["exercise"] for r in c.execute(
        "SELECT DISTINCT s.exercise FROM sets s JOIN workouts w ON w.id = s.workout_id "
        "WHERE w.date = ? AND w.status != 'rest'", (day_iso,)).fetchall()}


def match_day(c, trained):
    """Best-matching split day for a trained set. Ties and no-overlap give None.

    A tie means the session is ambiguous, so it resolves to swapped downstream
    instead of crediting one of the tied days as done.
    """
    if not trained:
        return None
    scored = [(len(trained & set(day_movements(d, c=c))), d) for d in split_day_order("active", c=c)]
    scored.sort(key=lambda s: s[0], reverse=True)
    if not scored or scored[0][0] == 0:
        return None
    if len(scored) > 1 and scored[1][0] == scored[0][0]:
        return None
    return scored[0][1]


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
    """Plan's adherence section, or None when anchor or rotation is missing."""
    rotation = parse_rotation(c)
    anchor = get_anchor(c)
    if not rotation or anchor is None:
        return None
    today = date.today()
    days = status_range(c, rotation, anchor,
                        (today - timedelta(days=window_days - 1)).isoformat(), today.isoformat())
    vol_weeks = load_constants()["thresholds"]["volume_window_weeks"]
    freq_start = (today - timedelta(days=vol_weeks * 7 - 1)).isoformat()
    window = status_range(c, rotation, anchor, freq_start, today.isoformat())
    frequency = {}
    for day in split_day_order("active", c=c):
        expected = [e for e in window if e["expected"].lower() == day.lower()]
        frequency[day] = {"expected": len(expected),
                          "done": sum(1 for e in expected if e["status"] == "done")}
    threshold = load_constants()["thresholds"].get("adherence_drift_days", 3)
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
    span = load_constants()["thresholds"]["volume_window_weeks"] * 7
    days = status_range(c, rotation, anchor,
                        (today - timedelta(days=span - 1)).isoformat(), today.isoformat())
    return {"anchor": anchor, "days": days}


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
    missed = [e for e in hist if e["status"] == "missed" and e["date"] >= recent_from
              and (last is None or e["date"] > last["date"])]
    return {"day": exp,
            "last_done": {"date": last["date"], "day": last["expected"]} if last else None,
            "missed": [{"date": e["date"], "day": e["expected"]} for e in missed]}


def cmd_rotation_anchor(date_str, day):
    """Pin the rotation schedule: on <date> the rotation was at <day>.

    Day resolves to the first matching rotation index (case-insensitive).
    """
    c = conn()
    try:
        on = date.fromisoformat((date_str or "").strip()).isoformat()
    except ValueError:
        sys.exit("anchor date must be YYYY-MM-DD")
    if date.fromisoformat(on) > date.today():
        sys.exit("anchor date cannot be in the future")
    rotation = parse_rotation(c)
    if not rotation:
        sys.exit("no rotation to anchor (meta set rotation '<json array>' first)")
    match = next((i for i, d in enumerate(rotation) if d.lower() == (day or "").strip().lower()), None)
    if match is None:
        sys.exit(f"'{day}' matches no rotation entry (see meta show rotation)")
    anchor = {"date": on, "index": match}
    c.execute("INSERT INTO meta (key, value) VALUES ('rotation_anchor', ?) "
              "ON CONFLICT (key) DO UPDATE SET value = excluded.value", (json.dumps(anchor),))
    c.commit()
    print(json.dumps({"anchor": anchor, "day": rotation[match]}))


def cmd_rotation_status(from_iso=None, to_iso=None):
    """Adherence verdicts per date over a range (default: last 14 days)."""
    c = conn()
    rotation = parse_rotation(c)
    anchor = get_anchor(c)
    if not rotation or anchor is None:
        sys.exit("rotation adherence needs a rotation and an anchor (rotation anchor <date> <day>)")
    today = date.today().isoformat()
    try:
        to_iso = date.fromisoformat(to_iso).isoformat() if to_iso else today
        from_iso = date.fromisoformat(from_iso).isoformat() if from_iso else \
            (date.fromisoformat(to_iso) - timedelta(days=13)).isoformat()
    except ValueError:
        sys.exit("status dates must be YYYY-MM-DD")
    if from_iso > to_iso:
        sys.exit("status --from cannot be after --to")
    print(json.dumps(status_range(c, rotation, anchor, from_iso, to_iso), indent=2))
