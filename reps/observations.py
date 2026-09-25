# SSOT owner: deterministic observations (semantic, temporal reads derived from
# durable facts and state-change history). Consumers: MCP observe tool, agent
# reasoning. Interpretations stay at the agent layer; everything here is
# reproducible from underlying state.

"""Semantic observations over a time range.

One shared interface: observe(metric, subject, since, until). Metric is a
closed ObserveMetric vocabulary; adding a metric means adding an enum value
and one computation, not a new tool. A metric that genuinely needs required
parameters beyond (subject, since, until) gets its own tool instead of
stretching this one.
"""

from datetime import date, timedelta

from .constants import canon_muscle_name, load_constants
from .db import conn
from .errors import RepsError
from .vocab import ObserveMetric, values


def _check_metric(metric):
    if metric not in values(ObserveMetric):
        raise RepsError(f"metric must be one of {', '.join(values(ObserveMetric))}")
    return metric


def _check_day(day, name):
    try:
        return date.fromisoformat(day).isoformat()
    except (ValueError, TypeError):
        raise RepsError(f"{name} must be YYYY-MM-DD")


def _range(since, until):
    today = date.today().isoformat()
    since = _check_day(since, "since") if since else (date.today() - timedelta(days=90)).isoformat()
    until = _check_day(until, "until") if until else today
    if since > until:
        raise RepsError("since must not be after until")
    return since, until


def _wrap(metric, subject, since, until, result, sources, definition):
    return {"metric": metric, "subject": subject, "since": since, "until": until,
            "result": result,
            "provenance": {"sources": sources, "definition": definition}}


def observe(metric, subject="", since="", until=""):
    """Compute one semantic observation over a date range."""
    _check_metric(metric)
    subject = (subject or "").strip()
    since, until = _range(since, until)
    impl = {"lift_trend": _lift_trend, "muscle_volume": _muscle_volume,
            "program_activity": _program_activity, "goal_trajectory": _goal_trajectory,
            "adherence_summary": _adherence_summary,
            "bodyweight_trend": _bodyweight_trend}[metric]
    return impl(subject, since, until)


def _lift_trend(subject, since, until):
    from .progression import top_e1rm_by_date

    exercise = subject.lower()
    if not exercise:
        raise RepsError("lift_trend needs a subject exercise")
    c = conn()
    if not c.execute("SELECT exercise FROM lift WHERE exercise = ?", (exercise,)).fetchone():
        raise RepsError(f"'{exercise}' is not a known lift")
    series = []
    for d, e, _notes, _created in top_e1rm_by_date(c, exercise):
        day = d[:10]
        if since <= day <= until:
            w, r = _top_set(c, exercise, day)
            series.append({"date": day, "e1rm": round(e, 1), "weight": w, "reps": r})
    if not series:
        result = {"exercise": exercise, "sessions": [], "sessions_count": 0,
                  "start_e1rm": None, "end_e1rm": None, "delta_e1rm": None,
                  "delta_pct": None, "best_e1rm": None}
    else:
        start, end = series[0]["e1rm"], series[-1]["e1rm"]
        best = max(s["e1rm"] for s in series)
        result = {"exercise": exercise, "sessions": series, "sessions_count": len(series),
                  "start_e1rm": start, "end_e1rm": end,
                  "delta_e1rm": round(end - start, 1),
                  "delta_pct": round((end - start) / start * 100, 1) if start else None,
                  "best_e1rm": best}
    return _wrap("lift_trend", exercise, since, until, result, ["sets", "workouts"],
                 "per-date top-set e1RM (Epley via reps/e1rm.py); "
                 "delta is last minus first in range, best is the range max")


def _top_set(c, exercise, day):
    row = c.execute("SELECT weight, reps FROM sets s JOIN workouts w ON w.id = s.workout_id "
                    "WHERE s.exercise = ? AND date(w.date) = ? "
                    "ORDER BY e1rm(weight, reps) DESC LIMIT 1", (exercise, day)).fetchone()
    return (row["weight"], row["reps"]) if row else (None, None)


def _muscle_volume(subject, since, until):
    c = conn()
    constants = load_constants()
    if subject:
        known = set(constants.muscles) | set(constants.untracked)
        hit = canon_muscle_name(subject.strip().lower(), known)
        muscle = hit or subject.strip().lower()
        if muscle not in constants.muscles:
            raise RepsError(f"'{subject}' is not a tracked muscle")
        muscles = [muscle]
    else:
        muscles = sorted(constants.muscles)
    rows = c.execute("SELECT sm.muscle AS muscle, COUNT(*) AS n FROM sets s "
                     "JOIN workouts w ON w.id = s.workout_id "
                     "JOIN set_muscle sm ON sm.set_id = s.id "
                     "WHERE date(w.date) BETWEEN ? AND ? GROUP BY sm.muscle",
                     (since, until)).fetchall()
    counts = {r["muscle"]: r["n"] for r in rows}
    span_days = (date.fromisoformat(until) - date.fromisoformat(since)).days + 1
    totals = {m: counts.get(m, 0) for m in muscles}
    result = {"totals": totals,
              "total_sets": sum(totals.values()),
              "avg_per_day": {m: round(n / span_days, 2) for m, n in totals.items()},
              "avg_per_week": ({m: round(n / (span_days / 7), 1) for m, n in totals.items()}
                               if span_days >= 7 else None),
              "span_days": span_days}
    return _wrap("muscle_volume", subject, since, until, result, ["sets", "set_muscle", "workouts"],
                 "logged working sets per muscle in range (full credit per mapped muscle); "
                 "avg_per_week is None for ranges under 7 days (a short range is not a weekly rate)")


def _program_activity(subject, since, until):
    from .history import list_changes

    changes = list_changes("program", subject, since, until)
    subjects = sorted({ch["subject"] for ch in changes})
    result = {"changes": len(changes), "subjects": subjects,
              "change_ids": [ch["id"] for ch in changes],
              "evidence": [ch["evidence"] for ch in changes if ch["evidence"]]}
    return _wrap("program_activity", subject, since, until, result, ["state_change"],
                 "recorded program day-snapshot transitions in range; "
                 "use history_get(change_id) for before/after detail")


def _not_in_effect(subject, exercise, since, until, goal_id):
    return _wrap("goal_trajectory", subject, since, until,
                 {"goal_id": goal_id, "exercise": exercise, "in_effect": False,
                  "target_e1rm": None, "deadline": None, "status": None,
                  "target_desc": None, "checkpoints_vs_actuals": [],
                  "completed": 0, "consecutive_misses": 0, "on_track": True,
                  "slippage": False,
                  "effective": {"as_of": until, "from_history": True}},
                 ["goals", "goal_checkpoints", "state_change"],
                 "the requested goal was not in effect during the range")


def _goal_trajectory(subject, since, until):
    from .goals import goal_progress
    from .history import state_at

    if not subject:
        raise RepsError("goal_trajectory needs a subject goal id or exercise")
    c = conn()
    gid = None
    try:
        gid = int(subject)
        row = c.execute("SELECT * FROM goals WHERE id = ?", (gid,)).fetchone()
    except ValueError:
        row = c.execute("SELECT * FROM goals WHERE exercise = ? ORDER BY id DESC LIMIT 1",
                        (subject.lower(),)).fetchone()
    if not row:
        raise RepsError(f"no goal '{subject}'")
    exercise = row["exercise"]
    st = state_at("goal", exercise, until)
    from_history = st["reconstructible"]
    if from_history:
        h = st["state"]
        eff_gid = h["goal_id"]
        if gid is not None and eff_gid != gid:
            return _not_in_effect(subject, exercise, since, until, gid)
        checkpoints = h["checkpoints"] or []
        target, deadline, status, desc = (h["target_e1rm"], h["deadline"],
                                          h["status"], h.get("target_desc"))
        grow = c.execute("SELECT created FROM goals WHERE id = ?", (eff_gid,)).fetchone()
        created = grow["created"] if grow else row["created"]
        in_effect = True
    elif st.get("reason", "").startswith("no recorded history for") \
            and row["created"][:10] <= until:
        eff_gid, checkpoints = row["id"], None
        target, deadline, status, desc = (row["target_e1rm"], row["deadline"],
                                          row["status"], row["target_desc"])
        created = row["created"]
        in_effect = True
    else:
        return _not_in_effect(subject, exercise, since, until,
                              row["id"] if gid is not None else None)
    goal = {"id": eff_gid, "exercise": exercise, "created": created,
            "target_e1rm": target, "deadline": deadline}
    prog = goal_progress(c, goal, checkpoints, through=until)
    pairs = [{"session_no": i + 1, "target": t,
              "actual": prog["actuals"][i]["e1rm"] if i < len(prog["actuals"]) else None,
              "actual_date": prog["actuals"][i]["date"] if i < len(prog["actuals"]) else None,
              "in_range": (prog["actuals"][i]["date"] if i < len(prog["actuals"]) else None) is not None
              and since <= prog["actuals"][i]["date"] <= until}
             for i, t in enumerate(prog["checkpoints"])]
    result = {"goal_id": eff_gid, "exercise": exercise, "in_effect": in_effect,
              "target_e1rm": target, "deadline": deadline,
              "status": status, "target_desc": desc, "checkpoints_vs_actuals": pairs,
              "completed": prog["completed"], "consecutive_misses": prog["consecutive_misses"],
              "on_track": prog["on_track"], "slippage": prog["slippage"],
              "effective": {"as_of": until, "from_history": from_history}}
    return _wrap("goal_trajectory", subject, since, until, result,
                 ["goals", "goal_checkpoints", "sets", "workouts", "state_change"],
                 "trajectory checkpoints folded from goal history to the range end, "
                 "so later rewrites do not move historical results; the trajectory "
                 "itself is session-numbered, in_range marks actuals inside the range")


def _value_at(change_list, day_iso, key):
    """State value in effect on a date: fold history to that date, else the
    earliest recorded before-image (stable under later changes, flagged as
    pre-history by the caller via coverage dates), else None."""
    past = [ch for ch in change_list if ch["date"] <= day_iso]
    if past:
        return past[-1]["after"].get(key)
    if change_list:
        return change_list[0]["before"].get(key)
    return None


def _split_map_at(prog_hist, day_iso, c):
    """Active split daymap in effect on a date: per-day snapshots folded from
    program history (earliest before-image before history starts), current
    days for never-recorded days. Never today's edited split."""
    from .program import parse_active_split_days, parse_movements

    by_subject: dict = {}
    for ch in prog_hist:
        if ch["subject"].startswith("active:"):
            by_subject.setdefault(ch["subject"], []).append(ch)
    covered = {sub.partition(":")[2] for sub in by_subject}
    daymap: dict = {}
    for sub, changes in by_subject.items():
        dayname = sub.partition(":")[2]
        past = [ch for ch in changes if ch["date"] <= day_iso]
        snap = (past[-1]["after"] if past else changes[0]["before"])["slots"]
        moves = []
        for s in snap:
            moves.extend(parse_movements(s["movements"]))
        if moves:
            daymap[dayname] = moves
    for dayname, moves in parse_active_split_days(c).items():
        if dayname not in covered:
            daymap[dayname] = moves
    return daymap


def _adherence_summary(subject, since, until):
    from .adherence import (classify_date, drift_days, get_anchor, match_day,
                            trained_exercises)
    from .history import list_changes
    from .program import get_rotation

    c = conn()
    rot_hist = list_changes("rotation", "rotation")
    anch_hist = list_changes("rotation", "anchor")
    prog_hist = list_changes("program")
    cur_rot = get_rotation(c)
    cur_anch = get_anchor(c)
    if not rot_hist and not cur_rot:
        raise RepsError("rotation adherence needs a rotation and an anchor")
    if not anch_hist and cur_anch is None:
        raise RepsError("rotation adherence needs a rotation and an anchor")
    days = []
    day = date.fromisoformat(since)
    end = date.fromisoformat(until)
    while day <= end:
        d = day.isoformat()
        rot = _value_at(rot_hist, d, "rotation")
        if rot is None and not rot_hist:
            rot = [None if x == "rest" else x for x in cur_rot]
        anch = _value_at(anch_hist, d, "anchor_date")
        anch_pos = _value_at(anch_hist, d, "position")
        if anch is None and not anch_hist and cur_anch is not None:
            anch, anch_pos = cur_anch["date"], cur_anch["index"]
        rot_names = ([r if r is not None else "rest" for r in rot]
                     if isinstance(rot, list) and rot else None)
        anchor = ({"date": anch, "index": anch_pos}
                  if anch is not None and anch_pos is not None
                  and rot_names is not None and anch_pos < len(rot_names) else None)
        trained = trained_exercises(c, d)
        daymap = _split_map_at(prog_hist, d, c)
        if rot_names is not None and anchor is not None:
            days.append(classify_date(c, rot_names, anchor, d, daymap))
        else:
            days.append({"date": d, "expected": None,
                         "trained": match_day(c, trained, daymap) if trained else None,
                         "status": "unknown"})
        day += timedelta(days=1)
    counts: dict = {}
    for v in days:
        counts[v["status"]] = counts.get(v["status"], 0) + 1
    result = {"days": len(days), "by_status": counts,
              "trailing_off_days": drift_days(days),
              "coverage": {"rotation_history_since": rot_hist[0]["date"] if rot_hist else None,
                           "anchor_history_since": anch_hist[0]["date"] if anch_hist else None},
              "verdicts": [{"date": v["date"], "expected": v.get("expected"),
                            "trained": v.get("trained"), "status": v["status"]} for v in days]}
    return _wrap("adherence_summary", subject, since, until, result,
                 ["workouts", "rotation", "rotation_anchor", "state_change"],
                 "each date classified with the rotation/anchor/split folded from history "
                 "to that date (earliest recorded image before history starts, "
                 "never today's state); dates without an applicable rotation/anchor "
                 "report expected None with status unknown")


def _bodyweight_trend(subject, since, until):
    c = conn()
    rows = [{"date": r["date"], "kg": r["kg"]}
            for r in c.execute("SELECT date, kg FROM bodyweight "
                               "WHERE date BETWEEN ? AND ? ORDER BY date", (since, until)).fetchall()]
    if not rows:
        result = {"entries": [], "n": 0, "start_kg": None, "end_kg": None, "delta_kg": None}
    else:
        delta = round(rows[-1]["kg"] - rows[0]["kg"], 1)
        result = {"entries": rows, "n": len(rows), "start_kg": rows[0]["kg"],
                  "end_kg": rows[-1]["kg"], "delta_kg": delta}
    return _wrap("bodyweight_trend", subject, since, until, result, ["bodyweight"],
                 "gym-scale weigh-ins in range; delta is last minus first")
