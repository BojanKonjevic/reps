from datetime import datetime

from .errors import RepsError

from .constants import clean_muscles
from .db import conn


def attach_muscles(c, sets):
    """Attach a sorted comma 'muscles' string to set dicts from the junction table."""
    ids = [s["id"] for s in sets]
    if not ids:
        return [dict(s) for s in sets]
    rows = c.execute(
        "SELECT set_id, muscle FROM set_muscles WHERE set_id IN (%s) ORDER BY set_id, muscle"
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


def e1rm_of(weight, reps):
    if reps == 1:
        return weight
    return weight * (1 + reps / 30.0)


def best_e1rm(c, exercise, exclude_set=None):
    sql = "SELECT weight, reps FROM sets WHERE exercise = ?"
    args = [exercise]
    if exclude_set is not None:
        sql += " AND id != ?"
        args.append(exclude_set)
    best = 0.0
    for r in c.execute(sql, args).fetchall():
        v = e1rm_of(r["weight"], r["reps"])
        if v > best:
            best = v
    return best


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
        mapping = c.execute("SELECT * FROM lift_muscle_map WHERE exercise = ?", (exercise,)).fetchone()
        if not mapping:
            raise RepsError(f"'{exercise}' has no mapping (run muscle_map_set first)")
        notes = [r["note"] for r in c.execute(
            "SELECT note FROM movement_notes WHERE exercise = ? ORDER BY id", (exercise,)).fetchall()]
        return {"exercise": exercise, "muscles": mapping["muscles"],
                "is_bodyweight_only": mapping["is_bodyweight_only"], "notes": notes}
    rows = c.execute("SELECT exercise, muscles FROM lift_muscle_map ORDER BY exercise").fetchall()
    return [dict(r) for r in rows]


def set_movement_note(exercise, text):
    if not text:
        raise RepsError("note text is required")
    c = conn()
    created = datetime.now().isoformat(timespec="seconds")
    cur = c.execute("INSERT INTO movement_notes (exercise, note, created) VALUES (?, ?, ?)",
                    (exercise.strip().lower(), text, created))
    c.commit()
    return {"note_id": cur.lastrowid, "exercise": exercise.strip().lower()}


def set_exercise_mapping(exercise, muscles, bodyweight=False):
    c = conn()
    exercise = exercise.strip().lower()
    muscles = clean_muscles(muscles)
    if not muscles:
        raise RepsError("muscles cannot be empty, pass at least one group")
    existing = c.execute("SELECT is_bodyweight_only FROM lift_muscle_map WHERE exercise = ?", (exercise,)).fetchone()
    is_bw = existing["is_bodyweight_only"] if existing else 0
    if bodyweight:
        is_bw = 1
    c.execute("DELETE FROM set_muscles WHERE set_id IN (SELECT id FROM sets WHERE exercise = ?)", (exercise,))
    updated = 0
    for set_row in c.execute("SELECT id FROM sets WHERE exercise = ?", (exercise,)).fetchall():
        set_id = set_row["id"]
        for muscle in muscles.split(","):
            c.execute("INSERT INTO set_muscles (set_id, muscle) VALUES (?, ?)", (set_id, muscle))
        updated += 1
    c.execute("INSERT OR REPLACE INTO lift_muscle_map (exercise, muscles, is_bodyweight_only) VALUES (?, ?, ?)",
              (exercise, muscles, is_bw))
    c.commit()
    return {"retag_exercise": exercise, "updated": updated, "is_bodyweight_only": is_bw}


def rename_exercise(old, new):
    c = conn()
    old = old.strip().lower()
    new = new.strip().lower()
    if old == new:
        raise RepsError("old and new exercise names are identical, nothing to rename")
    mapping = c.execute("SELECT muscles, is_bodyweight_only FROM lift_muscle_map WHERE exercise = ?", (old,)).fetchone()
    target = c.execute("SELECT muscles, is_bodyweight_only FROM lift_muscle_map WHERE exercise = ?", (new,)).fetchone()
    if mapping and target and set(mapping["muscles"].split(",")) != set(target["muscles"].split(",")):
        raise RepsError(f"'{new}' already maps to {target['muscles']}, not {mapping['muscles']}; retag one of them first, then rename")
    cur = c.execute("UPDATE sets SET exercise = ? WHERE exercise = ?", (new, old))
    renamed = cur.rowcount
    map_moved = False
    if mapping:
        is_bw = mapping["is_bodyweight_only"] or (target["is_bodyweight_only"] if target else 0)
        c.execute("INSERT OR REPLACE INTO lift_muscle_map (exercise, muscles, is_bodyweight_only) VALUES (?, ?, ?)",
                  (new, mapping["muscles"], is_bw))
        c.execute("DELETE FROM lift_muscle_map WHERE exercise = ?", (old,))
        map_moved = True
    c.commit()
    return {"renamed": renamed, "map_moved": map_moved}
