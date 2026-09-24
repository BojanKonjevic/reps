from datetime import datetime

import sqlite3

from .errors import RepsError

from .constants import clean_muscles
from .db import conn
from .e1rm import e1rm as e1rm_of
from .program import (ensure_lift, lift_is_bodyweight_only, lift_muscles,
                      lift_muscles_csv,
                      merge_lifts, rename_lift, set_lift_muscles)


def attach_muscles(c, sets):
    """Attach a sorted comma 'muscles' string to set dicts via the set_muscle view."""
    ids = [s["id"] for s in sets]
    if not ids:
        return [dict(s) for s in sets]
    rows = c.execute(
        "SELECT set_id, muscle FROM set_muscle WHERE set_id IN (%s) ORDER BY set_id, muscle"
        % ",".join("?" * len(ids)),
        ids,
    ).fetchall()
    by_id: dict = {}
    for r in rows:
        by_id.setdefault(r["set_id"], []).append(r["muscle"])
    out = []
    for s in sets:
        d = dict(s)
        d["muscles"] = ",".join(by_id.get(s["id"], []))
        out.append(d)
    return out


def best_e1rm(c, exercise, exclude_set=None):
    row = c.execute(
        "SELECT MAX(e1rm(weight, reps)) AS best FROM sets WHERE exercise = ?"
        + (" AND id != ?" if exclude_set is not None else ""),
        [exercise] + ([exclude_set] if exclude_set is not None else []),
    ).fetchone()
    return row["best"] or 0.0


def _levenshtein(a, b):
    if len(a) < len(b):
        a, b = b, a
    if len(b) == 0:
        return len(a)
    previous_row = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        current_row = [i + 1]
        for j, cb in enumerate(b):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (ca != cb)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]


def get_mapping(exercise=None):
    c = conn()
    if exercise:
        exercise = exercise.strip().lower()
        csv = lift_muscles_csv(c, exercise)
        if csv is None:
            raise RepsError(f"'{exercise}' is not a known lift")
        notes = [r["note"] for r in c.execute(
            "SELECT note FROM movement_note WHERE exercise = ? ORDER BY id", (exercise,)).fetchall()]
        return {"exercise": exercise, "muscles": csv,
                "is_bodyweight_only": 1 if lift_is_bodyweight_only(c, exercise) else 0,
                "notes": notes}
    rows = c.execute("SELECT exercise FROM lift ORDER BY exercise").fetchall()
    return [{"exercise": r["exercise"], "muscles": lift_muscles_csv(c, r["exercise"])} for r in rows]


def set_movement_note(exercise, text):
    if not text:
        raise RepsError("note text is required")
    c = conn()
    created = datetime.now().isoformat(timespec="seconds")
    try:
        cur = c.execute("INSERT INTO movement_note (exercise, note, created) VALUES (?, ?, ?)",
                        (exercise.strip().lower(), text, created))
    except sqlite3.IntegrityError:
        raise RepsError(f"'{exercise.strip().lower()}' is not a known lift")
    c.commit()
    return {"note_id": cur.lastrowid, "exercise": exercise.strip().lower()}


def set_exercise_mapping(exercise, muscles, bodyweight=False):
    c = conn()
    exercise = exercise.strip().lower()
    muscles = clean_muscles(muscles)
    if not muscles:
        raise RepsError("muscles cannot be empty, pass at least one group")
    existing = lift_muscles(c, exercise)
    is_bw = lift_is_bodyweight_only(c, exercise) if existing is not None else False
    if bodyweight:
        is_bw = True
    set_lift_muscles(c, exercise, muscles, 1 if is_bw else 0)
    updated = c.execute("SELECT COUNT(*) n FROM sets WHERE exercise = ?", (exercise,)).fetchone()["n"]
    c.commit()
    return {"retag_exercise": exercise, "updated": updated, "is_bodyweight_only": 1 if is_bw else 0}


def rename_exercise(old, new):
    c = conn()
    old = old.strip().lower()
    new = new.strip().lower()
    if old == new:
        raise RepsError("old and new exercise names are identical, nothing to rename")
    old_m = lift_muscles(c, old)
    new_m = lift_muscles(c, new)
    if old_m and new_m and set(old_m) != set(new_m):
        raise RepsError(f"'{new}' already maps to {','.join(new_m)}, not {','.join(old_m)}; retag one of them first, then rename")
    if new_m is not None and old_m is None:
        renamed = c.execute("UPDATE sets SET exercise = ? WHERE exercise = ?", (new, old)).rowcount
        c.commit()
        return {"renamed": renamed, "map_moved": False}
    if new_m is not None:
        out = merge_lifts(c, old, new)
        c.commit()
        return {"renamed": out["moved"], "map_moved": True, "merged": True}
    renamed = c.execute("SELECT COUNT(*) n FROM sets WHERE exercise = ?", (old,)).fetchone()["n"]
    rename_lift(c, old, new)
    c.commit()
    return {"renamed": renamed, "map_moved": old_m is not None}


def merge_exercises(old, new):
    """Merge one lift into an existing lift (refuses on conflicting muscle sets)."""
    from .program import merge_lifts as _merge
    c = conn()
    out = _merge(c, old.strip().lower(), new.strip().lower())
    c.commit()
    return out
