import re
from datetime import datetime

from .errors import RepsError

from .db import conn, open_workout


def top_e1rm_by_date(c, exercise):
    sql = ("SELECT w.date as day, MAX(CASE WHEN s.reps = 1 THEN s.weight ELSE s.weight * (1 + s.reps / 30.0) END) as e1rm, "
           "GROUP_CONCAT(DISTINCT w.notes) as notes, GROUP_CONCAT(DISTINCT s.note) as set_notes, "
           "MAX(s.created) as max_created FROM sets s JOIN workouts w ON w.id = s.workout_id "
           "WHERE s.exercise = ? AND w.status = 'done' GROUP BY day ORDER BY day")
    return [(r["day"], r["e1rm"], " ".join(n for n in (r["notes"], r["set_notes"]) if n),
             r["max_created"]) for r in c.execute(sql, (exercise,)).fetchall()]


def set_progression(exercise, verdict, next_target, direction, note="", workout_id=None):
    if verdict not in ("hit", "miss", "hold", "baseline"):
        raise RepsError("verdict must be one of hit miss hold baseline")
    if direction not in ("up", "flat", "down"):
        raise RepsError("direction must be one of up flat down")
    if not next_target:
        raise RepsError("next target is required (e.g. 82.5x5)")
    if not re.match(r"^\d+(\.\d+)?x\d+$", next_target.strip()):
        raise RepsError(f"next target must be weight x reps (e.g. 82.5x5), got '{next_target}'")
    c = conn()
    exercise = exercise.strip().lower()
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
        "INSERT INTO progression (workout_id, exercise, verdict, next_target, direction, note, created) "
        "VALUES (?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT (workout_id, exercise) DO UPDATE SET verdict = excluded.verdict, next_target = excluded.next_target, "
        "direction = excluded.direction, note = excluded.note, created = excluded.created",
        (workout_id, exercise, verdict, next_target, direction, note, created))
    c.commit()
    return {"progression": exercise, "workout_id": workout_id, "verdict": verdict,
            "next": next_target, "direction": direction}


def get_progression(exercise=None):
    c = conn()
    if exercise:
        rows = c.execute("SELECT * FROM progression WHERE exercise = ? ORDER BY workout_id DESC", (exercise.strip().lower(),)).fetchall()
    else:
        rows = c.execute(
            "SELECT p.* FROM progression p JOIN (SELECT exercise, MAX(workout_id) m FROM progression GROUP BY exercise) "
            "l ON l.exercise = p.exercise AND l.m = p.workout_id ORDER BY p.exercise").fetchall()
    return [dict(r) for r in rows]
