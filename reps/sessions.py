from datetime import date, datetime

from .constants import clean_muscles, load_constants
from .db import conn, open_workout
from .e1rm import e1rm as e1rm_of
from .errors import Fix, GateItem, RepsError
from .vocab import WorkoutStatus, values
from .muscles import _levenshtein, attach_muscles, best_e1rm
from .program import (active_deloads, best_split_day, consume_session_flags,
                      day_movements, deload_covers, ensure_lift,
                      lift_is_bodyweight_only, lift_muscles_csv,
                      parse_active_split_days, set_lift_muscles,
                      split_all_movements, split_day_order)
from .records import personal_records


def staleness(workout, today=None):
    """One stale-workout computation for plan, audit, and start.

    Assembly: threshold reads live here so the three callers cannot drift.
    Returns {"is_stale", "age_days", "last_set_created"}.
    """
    from .db import conn as _conn
    today = today or date.today()
    c = _conn()
    try:
        age_days = (today - date.fromisoformat(workout["date"])).days
    except ValueError:
        age_days = 0
    last = c.execute("SELECT created FROM sets WHERE workout_id = ? ORDER BY id DESC LIMIT 1",
                     (workout["id"],)).fetchone()
    last_created = last["created"] if last else None
    thresholds = load_constants().thresholds
    gap_over = False
    if last_created:
        try:
            gap_over = (datetime.now() - datetime.fromisoformat(last_created)).total_seconds() > thresholds.stale_workout_hours * 3600
        except ValueError:
            gap_over = False
    return {"is_stale": workout["date"] != today.isoformat()
            or age_days >= thresholds.stale_workout_days or gap_over,
            "age_days": age_days, "last_set_created": last_created}


def last_done(c):
    """Most recent done session carrying sets (replaces every inline copy)."""
    return c.execute(
        "SELECT w.date, w.id FROM workouts w WHERE w.status = 'done' "
        "AND EXISTS (SELECT 1 FROM sets s WHERE s.workout_id = w.id) "
        "ORDER BY w.date DESC, w.id DESC LIMIT 1").fetchone()


def break_threshold() -> int:
    """Days since the last done session that counts as a break (V11 owner).

    Plan, signals, and the snapshot status all compare against this;
    the dashboard reads the emitted break facts, never the threshold.
    """
    return load_constants().thresholds.break_days + 1


def session_prs(workout_id):
    """Computed PR flags per set in a workout (replaces hand-reasoned reports)."""
    c = conn()
    try:
        workout_id = int(workout_id)
    except (TypeError, ValueError):
        raise RepsError("no such workout")
    w = c.execute("SELECT * FROM workouts WHERE id = ?", (workout_id,)).fetchone()
    if not w:
        raise RepsError("no such workout")
    out = []
    for ex in c.execute("SELECT DISTINCT exercise FROM sets WHERE workout_id = ?",
                        (workout_id,)).fetchall():
        exercise = ex["exercise"]
        hist = c.execute(
            "SELECT s.id, s.weight, s.reps, s.created, w.date FROM sets s "
            "JOIN workouts w ON w.id = s.workout_id "
            "WHERE s.exercise = ? AND (w.status = 'done' OR w.id = ?) "
            "ORDER BY s.created, s.id", (exercise, workout_id)).fetchall()
        flags = personal_records([dict(r) for r in hist])
        for r in c.execute("SELECT id FROM sets WHERE workout_id = ? AND exercise = ?",
                           (workout_id, exercise)).fetchall():
            out.append({"set_id": r["id"], "exercise": exercise, "is_pr": flags.get(r["id"], False)})
    return {"workout_id": workout_id, "prs": sorted(out, key=lambda e: e["set_id"])}


def start_workout(note):
    c = conn()
    existing = open_workout(c)
    if existing:
        sets_n = c.execute("SELECT COUNT(*) n FROM sets WHERE workout_id = ?", (existing["id"],)).fetchone()["n"]
        last = c.execute("SELECT created FROM sets WHERE workout_id = ? ORDER BY id DESC LIMIT 1", (existing["id"],)).fetchone()
        try:
            age_days = (date.today() - date.fromisoformat(existing["date"])).days
        except ValueError:
            age_days = 0
        return {"workout_id": existing["id"], "reused": True, "date": existing["date"],
                "age_days": age_days, "sets": sets_n,
                "last_set_created": last["created"] if last else None}
    today = date.today().isoformat()
    cur = c.execute("INSERT INTO workouts (date, status, notes) VALUES (?, 'open', ?)", (today, note))
    c.commit()
    return {"workout_id": cur.lastrowid, "reused": False, "date": today}


def log_set(exercise, weight, reps, note, muscles, bodyweight=False):
    c = conn()
    w = open_workout(c)
    if not w:
        raise RepsError("no open workout, run start first (workouts are only created explicitly)")
    exercise = exercise.strip().lower()
    try:
        weight = float(weight)
    except (TypeError, ValueError):
        raise RepsError("weight must be a number")
    try:
        reps = int(reps)
    except (TypeError, ValueError):
        raise RepsError("reps must be an integer")
    if weight < 0:
        raise RepsError("weight cannot be negative")
    if reps <= 0:
        raise RepsError("reps must be a positive integer")
    muscles = clean_muscles(muscles)

    mapping = lift_muscles_csv(c, exercise)
    if weight == 0:
        if bodyweight:
            pass
        elif not mapping or not lift_is_bodyweight_only(c, exercise):
            raise RepsError(f"zero weight not allowed for '{exercise}' (not a bodyweight-only exercise, add bw flag for bodyweight moves)")

    if mapping is None:
        if not muscles:
            raise RepsError(f"muscles required for new exercise '{exercise}' (no mapping in lift_muscle_map)")
        ensure_lift(c, exercise)
        set_lift_muscles(c, exercise, muscles, 1 if bodyweight else 0)
    elif not muscles:
        muscles = mapping

    constants = load_constants()
    warn_ratio = constants.thresholds.e1rm_warn_ratio
    dup_dist = constants.thresholds.duplicate_name_distance
    warnings = []
    if w["date"] != date.today().isoformat():
        warnings.append(f"open workout is from {w['date']}, not today; confirm this set belongs there")
    for other in c.execute("SELECT DISTINCT exercise FROM sets").fetchall():
        if other["exercise"] != exercise and _levenshtein(exercise, other["exercise"]) <= dup_dist:
            warnings.append(f"'{exercise}' is close to existing exercise '{other['exercise']}'; confirm spelling")
            break
    new_e1rm = e1rm_of(weight, reps)
    if weight > 0:
        best = best_e1rm(c, exercise)
        if best > 0 and new_e1rm > best * warn_ratio:
            warnings.append(f"e1RM {new_e1rm:.1f} is over {round((warn_ratio - 1) * 100)}% above best {best:.1f} for '{exercise}'; confirm weight and reps")
        prev = c.execute("SELECT weight, reps FROM sets WHERE workout_id = ? AND exercise = ? ORDER BY id DESC LIMIT 1", (w["id"], exercise)).fetchone()
        if prev:
            prev_e1rm = e1rm_of(prev["weight"], prev["reps"])
            if prev_e1rm > 0 and new_e1rm < prev_e1rm / 3:
                warnings.append(f"e1RM {new_e1rm:.1f} is under a third of this workout's earlier {prev_e1rm:.1f} for '{exercise}'; confirm weight and reps")
    if mapping and muscles and set(muscles.split(",")) != set(mapping.split(",")):  # sanctioned: input-boundary vs read-model compare
        raise RepsError(f"logged muscles {muscles} differ from the mapping for '{exercise}' ({mapping}); "
                        f"the mapping is authoritative, log a genuine variation under its own exercise name "
                        f"or change it everywhere with muscle_map_set")

    # Refusals above leave the lift untouched: the bodyweight flag flips only
    # on the validated write path below.
    if mapping is not None and bodyweight and not lift_is_bodyweight_only(c, exercise):
        c.execute("UPDATE lift SET is_bodyweight_only = 1 WHERE exercise = ?", (exercise,))

    wid = w["id"]
    created = datetime.now().isoformat(timespec="seconds")
    cur = c.execute(
        "INSERT INTO sets (workout_id, exercise, weight, reps, note, created) VALUES (?, ?, ?, ?, ?, ?)",
        (wid, exercise, weight, reps, note, created),
    )
    set_id = cur.lastrowid
    c.commit()
    out = {"set_id": set_id, "workout_id": wid}
    if warnings:
        out["warnings"] = warnings
    return out


def update_set(set_id, field, value):
    allowed = {"weight", "reps", "exercise", "note"}
    if field == "muscles":
        raise RepsError("per-set muscles are gone, the mapping is authoritative; run muscle_map_set for the exercise")
    if field not in allowed:
        raise RepsError("field must be one of weight reps exercise note")
    c = conn()
    try:
        set_id = int(set_id)
    except (TypeError, ValueError):
        raise RepsError("no such set")
    existing = c.execute("SELECT * FROM sets WHERE id = ?", (set_id,)).fetchone()
    if not existing:
        raise RepsError("no such set")
    if field == "exercise":
        value = value.strip().lower()
        if lift_muscles_csv(c, value) is None:
            raise RepsError(f"exercise '{value}' is not a known lift")
    if field == "weight":
        if value == "":
            raise RepsError("weight cannot be empty, pass a number or delete the set")
        try:
            value = float(value)
        except (TypeError, ValueError):
            raise RepsError("weight must be a number")
        if value < 0:
            raise RepsError("weight cannot be negative")
        # Validate zero-weight against exercise type
        if value == 0:
            if not lift_is_bodyweight_only(c, existing["exercise"]):
                raise RepsError(f"zero weight not allowed for '{existing['exercise']}' (not a bodyweight-only exercise)")
    if field == "reps":
        try:
            value = int(value)
        except (TypeError, ValueError):
            raise RepsError("reps must be an integer")
        if value <= 0:
            raise RepsError("reps must be a positive integer")
    warnings = []
    if field in ("weight", "reps"):
        new_weight = value if field == "weight" else existing["weight"]
        new_reps = value if field == "reps" else existing["reps"]
        if new_weight > 0:
            new_e1rm = e1rm_of(new_weight, new_reps)
            best = best_e1rm(c, existing["exercise"], exclude_set=int(set_id))
            warn_ratio = load_constants().thresholds.e1rm_warn_ratio
            if best > 0 and new_e1rm > best * warn_ratio:
                warnings.append(f"e1RM {new_e1rm:.1f} is over {round((warn_ratio - 1) * 100)}% above best {best:.1f} for '{existing['exercise']}'; confirm weight and reps")
    c.execute("UPDATE sets SET {} = ? WHERE id = ?".format(field), (value, int(set_id)))
    c.commit()
    out = {"updated": int(set_id)}
    if warnings:
        out["warnings"] = warnings
    return out


def end_workout(note, force=None):
    c = conn()
    w = open_workout(c)
    if not w:
        raise RepsError("no open workout")
    outstanding = end_gate_items(c, w, note if not force else (note + f" {force}" if note else force))
    hard = [o for o in outstanding if o.get("hard")]
    if hard:
        lines = [f"cannot close workout {w['id']}, {len(hard)} hard items outstanding (force cannot skip these):", ""]
        for o in hard:
            lines.append(f"  {o['item']}\n    {o['fix']}")
        raise RepsError("\n".join(lines))
    if outstanding and not force:
        lines = [f"cannot close workout {w['id']}, {len(outstanding)} items outstanding:", ""]
        for o in outstanding:
            lines.append(f"  {o['item']}\n    {o['fix']}")
        lines.append("or: session_end with a force reason (the reason is written into the workout note; "
                     "writeback items only, missing muscles always block)")
        raise RepsError("\n".join(lines))
    if force:
        note = (note + f" (forced: {force})").strip() if note else f"(forced: {force})"
    if note:
        old = w["notes"]
        combined = (old + " " + note).strip() if old else note
        c.execute("UPDATE workouts SET notes = ? WHERE id = ?", (combined, w["id"]))
    c.execute("UPDATE workouts SET status = 'done' WHERE id = ?", (w["id"],))
    consumed = consume_session_flags(c, w["id"])
    c.commit()
    n = c.execute("SELECT COUNT(*) n FROM sets WHERE workout_id = ?", (w["id"],)).fetchone()["n"]
    out = {"closed": w["id"], "sets": n, "flags_consumed": consumed,
           "next": "audit this session, then sync, then commit workouts.sql"}
    if force:
        out["forced"] = force
    return out


def mark_rest(day, note):
    try:
        day = date.fromisoformat(day).isoformat()
    except ValueError:
        raise RepsError("date must be YYYY-MM-DD")
    c = conn()
    if date.fromisoformat(day) > date.today():
        raise RepsError("rest date cannot be in the future")
    if open_workout(c):
        raise RepsError("open workout exists, end or delete it before marking a rest day")
    rows = c.execute("SELECT * FROM workouts WHERE date = ?", (day,)).fetchall()
    if any(r["status"] != "rest" for r in rows):
        raise RepsError(f"already trained on {day}, cannot mark it rest")
    rest_rows = [r for r in rows if r["status"] == "rest"]
    if rest_rows:
        rid = rest_rows[0]["id"]
        appended = False
        if note:
            old = rest_rows[0]["notes"]
            combined = (old + " " + note).strip() if old else note
            c.execute("UPDATE workouts SET notes = ? WHERE id = ?", (combined, rid))
            c.commit()
            appended = True
        return {"rest_id": rid, "date": day, "appended": appended}
    cur = c.execute("INSERT INTO workouts (date, status, notes) VALUES (?, 'rest', ?)", (day, note))
    c.commit()
    return {"rest_id": cur.lastrowid, "date": day, "appended": False}


def get_today():
    c = conn()
    w = open_workout(c)
    today = date.today().isoformat()
    rest = c.execute("SELECT * FROM workouts WHERE date = ? AND status = 'rest' ORDER BY id", (today,)).fetchone()
    rest_json = dict(rest) if rest else None
    if not w:
        return {"open": False, "rest": rest_json}
    sets = c.execute("SELECT * FROM sets WHERE workout_id = ? ORDER BY id", (w["id"],)).fetchall()
    return {"open": True, "workout": dict(w), "sets": attach_muscles(c, sets), "rest": rest_json}


def list_exercises():
    c = conn()
    rows = c.execute("SELECT DISTINCT exercise FROM sets ORDER BY exercise").fetchall()
    return [r["exercise"] for r in rows]


def get_history(exercise, limit):
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        raise RepsError("limit must be an integer")
    c = conn()
    rows = c.execute(
        "SELECT s.*, w.date FROM sets s JOIN workouts w ON w.id = s.workout_id WHERE s.exercise = ? ORDER BY s.id DESC LIMIT ?",
        (exercise.strip().lower(), limit),
    ).fetchall()
    return attach_muscles(c, rows)


def get_stats():
    c = conn()
    workouts = c.execute("SELECT id, date, status FROM workouts ORDER BY date").fetchall()
    out = {"workouts": len([w for w in workouts if w["status"] != "rest"]), "by_exercise": {}}
    rows = c.execute("SELECT exercise, COUNT(*) n, MAX(e1rm(weight, reps)) max_e1rm, MAX(weight) max_w FROM sets GROUP BY exercise").fetchall()

    for r in rows:
        out["by_exercise"][r["exercise"]] = {"sets": r["n"], "max_weight": r["max_w"], "max_e1rm": round(r["max_e1rm"], 1)}
    return out


def record_bodyweight(kg, note):
    c = conn()
    today = date.today().isoformat()
    try:
        kg = float(kg)
    except (TypeError, ValueError):
        raise RepsError("bodyweight must be a number")
    if kg <= 0:
        raise RepsError("bodyweight must be positive")
    if kg < 20 or kg > 300:
        raise RepsError(f"bodyweight {kg}kg is implausible, confirm the value")
    cur = c.execute("INSERT INTO bodyweight (date, kg, note) VALUES (?, ?, ?)", (today, kg, note))
    c.commit()
    return {"weigh_id": cur.lastrowid, "date": today, "kg": kg}


def end_gate_items(c, w, note):
    """Preconditions for closing a workout. Returns list of {item, fix, ...}.

    Fixes travel as typed Fix(tool, args) verified against the MCP registry
    (tests/test_docs.py); the human "fix" string is rendered from the real
    tool name, never invented prose.
    """
    outstanding = []
    missing = c.execute("""
        SELECT s.id, s.exercise FROM sets s
        LEFT JOIN set_muscle sm ON sm.set_id = s.id
        WHERE s.workout_id = ? AND sm.muscle IS NULL
    """, (w["id"],)).fetchall()
    for m in missing:
        outstanding.append(GateItem(
            f"set {m['id']} ({m['exercise']}) has no muscles",
            Fix("muscle_map_set", {"exercise": m["exercise"]}), hard=True).as_dict())
    trained = [r["exercise"] for r in c.execute(
        "SELECT DISTINCT exercise FROM sets WHERE workout_id = ?", (w["id"],)).fetchall()]
    judged = {r["exercise"] for r in c.execute(
        "SELECT DISTINCT exercise FROM progression WHERE workout_id = ?", (w["id"],)).fetchall()}
    for ex in sorted(set(trained) - judged):
        item = GateItem(f"missing progression: {ex}",
                        Fix("progression_set", {"exercise": ex}))
        d = item.as_dict()
        d["fix"] = f"progression_set for \"{ex}\" with verdict and next target"
        outstanding.append(d)
    known = split_all_movements("active", c=c)
    unreconciled = sorted(set(trained) - known)
    if unreconciled:
        day = best_split_day(trained, c=c) or (split_day_order("active", c=c)[:1] or ["Upper A"])[0]
        performed = [r["exercise"] for r in c.execute(
            "SELECT exercise, MIN(id) m FROM sets WHERE workout_id = ? GROUP BY exercise ORDER BY m",
            (w["id"],)).fetchall()]
        anchor = next((ex for ex in reversed(performed) if ex in day_movements(day, c=c)), None)
        after = f" after \"{anchor}\"" if anchor else ""
        for ex in unreconciled:
            item = GateItem(f"unreconciled slot: {ex} (not in any active split day)",
                            Fix("program_split_reconcile", {"day": day}))
            d = item.as_dict()
            d["fix"] = f"program_split_reconcile on \"{day}\"{after}"
            outstanding.append(d)
    deloads = active_deloads(c)
    if deloads:
        day_moves = parse_active_split_days(c)
        covered = [ex for ex in trained if deload_covers(deloads, ex, day_moves)]
        if covered:
            combined = ((w["notes"] + " " + note) if w["notes"] else note).lower()
            if "deload" not in combined:
                outstanding.append({"item": f"deload session covers {', '.join(sorted(set(covered)))} but the note has no 'deload'",
                                    "fix": "session_end with deload in the note"})
    return outstanding


def check_end_gate(note=""):
    c = conn()
    w = open_workout(c)
    if not w:
        raise RepsError("no open workout")
    outstanding = end_gate_items(c, w, note)
    if outstanding:
        lines = [f"workout {w['id']} not ready to close, {len(outstanding)} items outstanding:"]
        for o in outstanding:
            lines.append(f"  {o['item']}\n    {o['fix']}")
        raise RepsError("\n".join(lines))
    return {"ready": w["id"]}


def delete_set(set_id):
    try:
        set_id = int(set_id)
    except (TypeError, ValueError):
        raise RepsError("no such set")
    c = conn()
    row = c.execute("SELECT s.*, w.date FROM sets s JOIN workouts w ON w.id = s.workout_id WHERE s.id = ?", (set_id,)).fetchone()
    if not row:
        raise RepsError("no such set")
    c.execute("DELETE FROM sets WHERE id = ?", (set_id,))
    c.commit()
    return {"deleted": set_id, "workout_id": row["workout_id"], "date": row["date"],
            "was": {"exercise": row["exercise"], "weight": row["weight"], "reps": row["reps"]}}


def delete_workout(workout_id):
    try:
        workout_id = int(workout_id)
    except (TypeError, ValueError):
        raise RepsError("no such workout")
    c = conn()
    row = c.execute("SELECT * FROM workouts WHERE id = ?", (workout_id,)).fetchone()
    if not row:
        raise RepsError("no such workout")
    n = c.execute("SELECT COUNT(*) n FROM sets WHERE workout_id = ?", (workout_id,)).fetchone()["n"]
    c.execute("DELETE FROM sets WHERE workout_id = ?", (workout_id,))
    c.execute("DELETE FROM workouts WHERE id = ?", (workout_id,))
    c.commit()
    return {"deleted_workout": workout_id, "date": row["date"], "deleted_sets": n}


def update_workout(workout_id, field, value):
    allowed = {"notes", "date", "status"}
    if field not in allowed:
        raise RepsError("field must be one of notes date status")
    try:
        workout_id = int(workout_id)
    except (TypeError, ValueError):
        raise RepsError("no such workout")
    if field == "date":
        try:
            date.fromisoformat(value)
        except ValueError:
            raise RepsError("date must be YYYY-MM-DD")
        if date.fromisoformat(value) > date.today():
            raise RepsError("workout date cannot be in the future")
    if field == "status" and value not in values(WorkoutStatus):
        raise RepsError("status must be open, done or rest")
    c = conn()
    if field == "status" and value == "open":
        other = c.execute("SELECT id FROM workouts WHERE status = 'open' AND id != ?", (int(workout_id),)).fetchone()
        if other:
            raise RepsError(f"workout {other['id']} is already open; end or delete it first")
    if field == "status" and value == "rest":
        row = c.execute("SELECT date FROM workouts WHERE id = ?", (int(workout_id),)).fetchone()
        if not row:
            raise RepsError("no such workout")
        n = c.execute("SELECT COUNT(*) n FROM sets WHERE workout_id = ?", (int(workout_id),)).fetchone()["n"]
        if n > 0:
            raise RepsError("workout has sets, cannot mark it rest (move or delete them first)")
        dup = c.execute("SELECT id FROM workouts WHERE date = ? AND status = 'rest' AND id != ?",
                        (row["date"], int(workout_id))).fetchone()
        if dup:
            raise RepsError(f"{row['date']} already has a rest row (id {dup['id']}), add a note there instead of doubling up")
    cur = c.execute(f"UPDATE workouts SET {field} = ? WHERE id = ?", (value, int(workout_id)))
    if cur.rowcount == 0:
        raise RepsError("no such workout")
    c.commit()
    return {"updated_workout": int(workout_id), "field": field}


def get_session(datestr):
    try:
        day = date.fromisoformat(datestr).isoformat()
    except ValueError:
        raise RepsError("date must be YYYY-MM-DD")
    c = conn()
    wrows = c.execute("SELECT * FROM workouts WHERE date = ? ORDER BY id", (day,)).fetchall()
    out = []
    for w in wrows:
        sets = c.execute("SELECT * FROM sets WHERE workout_id = ? ORDER BY id", (w["id"],)).fetchall()
        out.append({"workout": dict(w), "sets": attach_muscles(c, sets)})
    return {"date": day, "workouts": out}


def get_session_range(fromstr, tostr):
    try:
        d0 = date.fromisoformat(fromstr).isoformat()
        d1 = date.fromisoformat(tostr).isoformat()
    except ValueError:
        raise RepsError("dates must be YYYY-MM-DD")
    c = conn()
    wrows = c.execute("SELECT * FROM workouts WHERE date >= ? AND date <= ? ORDER BY date, id", (d0, d1)).fetchall()
    out = []
    for w in wrows:
        sets = c.execute("SELECT * FROM sets WHERE workout_id = ? ORDER BY id", (w["id"],)).fetchall()
        out.append({"workout": dict(w), "sets": attach_muscles(c, sets)})
    return {"from": d0, "to": d1, "workouts": out}


def get_notes(limit):
    try:
        lim = max(1, min(2000, int(limit)))
    except (TypeError, ValueError):
        lim = 200
    c = conn()
    wrows = c.execute("SELECT id, date, notes FROM workouts WHERE notes != '' ORDER BY date DESC, id DESC LIMIT ?", (lim,)).fetchall()
    srows = c.execute(
        "SELECT s.id, s.exercise, s.weight, s.reps, s.note, w.date FROM sets s "
        "JOIN workouts w ON w.id = s.workout_id WHERE s.note != '' ORDER BY w.date DESC, s.id DESC LIMIT ?", (lim,)).fetchall()
    return {"workout_notes": [dict(r) for r in wrows], "set_notes": [dict(r) for r in srows]}


def get_calendar():
    c = conn()
    wrows = c.execute("SELECT id, date, status FROM workouts ORDER BY date, id").fetchall()
    by_date = {}
    for w in wrows:
        d = by_date.setdefault(w["date"], {"date": w["date"], "workouts": [], "sets": 0})
        d["workouts"].append(w["id"])
    for d in by_date.values():
        n = c.execute("SELECT COUNT(*) n FROM sets s JOIN workouts w ON w.id = s.workout_id WHERE w.date = ?", (d["date"],)).fetchone()["n"]
        d["sets"] = n
    statuses: dict = {}
    for r in c.execute("SELECT date, status FROM workouts").fetchall():
        statuses.setdefault(r["date"], []).append(r["status"])
    for d in by_date.values():
        sts = statuses.get(d["date"], [])
        d["rest"] = bool(sts) and all(s == "rest" for s in sts)
    days = sorted(by_date.values(), key=lambda d: d["date"])
    prev = None
    for d in days:
        if prev is None:
            d["gap_since_prev"] = None
        else:
            d["gap_since_prev"] = (date.fromisoformat(d["date"]) - date.fromisoformat(prev)).days - 1
        prev = d["date"]
    return {"dates": days}


def get_context(n):
    try:
        limit = max(1, min(5, int(n)))
    except (TypeError, ValueError):
        limit = 3
    c = conn()
    wrows = c.execute("SELECT * FROM workouts ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    recent = []
    for w in reversed(wrows):
        sets = c.execute("SELECT * FROM sets WHERE workout_id = ? ORDER BY id", (w["id"],)).fetchall()
        recent.append({"workout": dict(w), "sets": attach_muscles(c, sets)})
    best = []
    for r in c.execute("SELECT exercise, COUNT(*) n FROM sets GROUP BY exercise ORDER BY exercise").fetchall():
        top = c.execute(
            "SELECT weight, reps, e1rm(weight, reps) AS e1rm FROM sets WHERE exercise = ? ORDER BY e1rm DESC LIMIT 1", (r["exercise"],)
        ).fetchone()
        last = c.execute(
            "SELECT s.weight, s.reps FROM sets s JOIN workouts w ON w.id = s.workout_id WHERE s.exercise = ? ORDER BY w.date DESC, s.id DESC LIMIT 1", (r["exercise"],)
        ).fetchone()
        best.append({"exercise": r["exercise"], "sets": r["n"],
                     "max_e1rm": round(top["e1rm"], 1) if top else None,
                     "max_weight": top["weight"] if top else None,
                     "last": dict(last) if last else None})
    totals = c.execute("SELECT COUNT(*) w FROM workouts WHERE status != 'rest'").fetchone()
    bw = [dict(r) for r in c.execute("SELECT date, kg, note FROM bodyweight ORDER BY date DESC, id DESC LIMIT 5").fetchall()]
    return {"recent": recent, "lifts": best, "workouts_total": totals["w"], "bodyweight_last": bw}
