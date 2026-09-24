# SSOT owner: latest progression per exercise. Consumers: plan, sync, progression_show.

from datetime import datetime

from .errors import RepsError

from .db import conn, open_workout
from .vocab import Direction, Verdict, values


def top_e1rm_by_date(c, exercise):
    sql = ("SELECT w.date as day, MAX(e1rm(s.weight, s.reps)) as e1rm, "
           "GROUP_CONCAT(DISTINCT w.notes) as notes, GROUP_CONCAT(DISTINCT s.note) as set_notes, "
           "MAX(s.created) as max_created FROM sets s JOIN workouts w ON w.id = s.workout_id "
           "WHERE s.exercise = ? AND w.status = 'done' GROUP BY day ORDER BY day")
    return [(r["day"], r["e1rm"], " ".join(n for n in (r["notes"], r["set_notes"]) if n),
             r["max_created"]) for r in c.execute(sql, (exercise,)).fetchall()]


def latest(c):
    """Latest progression verdict per exercise (replaces every inline copy)."""
    return {r["exercise"]: dict(r) for r in c.execute(
        "SELECT p.* FROM progression p JOIN (SELECT exercise, MAX(workout_id) m FROM progression "
        "GROUP BY exercise) l ON l.exercise = p.exercise AND l.m = p.workout_id").fetchall()}


def format_target(weight, reps):
    return f"{weight:g}x{reps}"


def set_progression(exercise, verdict, next_weight, next_reps, direction, note="", workout_id=None):
    if verdict not in values(Verdict):
        raise RepsError("verdict must be one of hit miss hold baseline")
    if direction not in values(Direction):
        raise RepsError("direction must be one of up flat down")
    try:
        next_weight = float(next_weight)
    except (TypeError, ValueError):
        raise RepsError("next weight must be a number")
    try:
        next_reps = int(next_reps)
    except (TypeError, ValueError):
        raise RepsError("next reps must be an integer")
    if next_weight < 0:
        raise RepsError("next weight must be positive")
    if next_reps <= 0:
        raise RepsError("next reps must be a positive integer")
    c = conn()
    exercise = exercise.strip().lower()
    if next_weight == 0:
        from .program import lift_is_bodyweight_only
        if not lift_is_bodyweight_only(c, exercise):
            raise RepsError(f"next weight cannot be zero for '{exercise}' (not a bodyweight-only exercise)")
    if workout_id is None:
        w = open_workout(c)
        if not w:
            raise RepsError("no open workout (pass workout_id to backfill a closed one)")
        workout_id = w["id"]
    else:
        try:
            workout_id = int(workout_id)
        except (TypeError, ValueError):
            raise RepsError("no such workout")
        if not c.execute("SELECT id FROM workouts WHERE id = ?", (workout_id,)).fetchone():
            raise RepsError("no such workout")
    trained = {r["exercise"] for r in c.execute("SELECT DISTINCT exercise FROM sets WHERE workout_id = ?", (workout_id,)).fetchall()}
    if exercise not in trained:
        raise RepsError(f"'{exercise}' has no sets in workout {workout_id}, nothing to judge")
    created = datetime.now().isoformat(timespec="seconds")
    c.execute(
        "INSERT INTO progression (workout_id, exercise, verdict, next_weight, next_reps, direction, note, created) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT (workout_id, exercise) DO UPDATE SET verdict = excluded.verdict, "
        "next_weight = excluded.next_weight, next_reps = excluded.next_reps, "
        "direction = excluded.direction, note = excluded.note, created = excluded.created",
        (workout_id, exercise, verdict, next_weight, next_reps, direction, note, created))
    c.commit()
    return {"progression": exercise, "workout_id": workout_id, "verdict": verdict,
            "next": format_target(next_weight, next_reps),
            "next_weight": next_weight, "next_reps": next_reps, "direction": direction}


def get_progression(exercise=None):
    c = conn()
    if exercise:
        rows = [dict(r) for r in c.execute(
            "SELECT * FROM progression WHERE exercise = ? ORDER BY workout_id DESC",
            (exercise.strip().lower(),)).fetchall()]
    else:
        rows = [dict(r) for r in latest(c).values()]
        rows.sort(key=lambda r: r["exercise"])
    out = []
    for d in rows:
        d["next"] = format_target(d["next_weight"], d["next_reps"])
        out.append(d)
    return out
