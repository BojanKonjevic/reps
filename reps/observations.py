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


def _goal_trajectory(subject, since, until):
    from .goals import goal_progress

    if not subject:
        raise RepsError("goal_trajectory needs a subject goal id or exercise")
    c = conn()
    try:
        gid = int(subject)
        row = c.execute("SELECT * FROM goals WHERE id = ?", (gid,)).fetchone()
    except ValueError:
        gid = None
        row = c.execute("SELECT * FROM goals WHERE exercise = ? ORDER BY id DESC LIMIT 1",
                        (subject.lower(),)).fetchone()
    if not row:
        raise RepsError(f"no goal '{subject}'")
    goal = dict(row)
    prog = goal_progress(c, goal)
    pairs = [{"session_no": i + 1, "target": t,
              "actual": prog["actuals"][i]["e1rm"] if i < len(prog["actuals"]) else None,
              "actual_date": prog["actuals"][i]["date"] if i < len(prog["actuals"]) else None,
              "in_range": (prog["actuals"][i]["date"] if i < len(prog["actuals"]) else None) is not None
              and since <= prog["actuals"][i]["date"] <= until}
             for i, t in enumerate(prog["checkpoints"])]
    result = {"goal_id": goal["id"], "exercise": goal["exercise"],
              "target_e1rm": goal["target_e1rm"], "deadline": goal["deadline"],
              "status": goal["status"], "checkpoints_vs_actuals": pairs,
              "completed": prog["completed"], "consecutive_misses": prog["consecutive_misses"],
              "on_track": prog["on_track"], "slippage": prog["slippage"]}
    return _wrap("goal_trajectory", subject, since, until, result,
                 ["goals", "goal_checkpoints", "sets", "workouts"],
                 "trajectory checkpoints against logged top-set e1RMs; "
                 "range selects the goal, the trajectory itself is session-numbered")


def _adherence_summary(subject, since, until):
    from .adherence import drift_days, get_rotation_status

    days = get_rotation_status(since, until)
    counts: dict = {}
    for d in days:
        counts[d["status"]] = counts.get(d["status"], 0) + 1
    result = {"days": len(days), "by_status": counts,
              "trailing_off_days": drift_days(days),
              "verdicts": [{"date": d["date"], "expected": d.get("expected"),
                            "trained": d.get("trained"), "status": d["status"]} for d in days]}
    return _wrap("adherence_summary", subject, since, until, result,
                 ["workouts", "rotation", "rotation_anchor"],
                 "per-date rotation verdicts from reps/adherence.py; "
                 "counts group by verdict, never a hand tally")


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
