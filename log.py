#!/usr/bin/env python3
"""reps: workout log. Code owns what is derivable or enforceable, the agent owns what is judgment."""

import json
import os
import re
import sqlite3
import sys
import urllib.error
import urllib.request
from datetime import date, datetime

DB = os.environ.get("REPS_DB", os.path.join(os.path.dirname(os.path.abspath(__file__)), "workouts.db"))
CFG = os.path.join(os.path.expanduser("~"), ".config", "reps", "config.json")
SCIENCE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "SCIENCE.md")
MEMORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "MEMORY.md")
CONSTANTS_FILE = os.environ.get("REPS_CONSTANTS", os.path.join(os.path.dirname(os.path.abspath(__file__)), "constants.json"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS workouts (
  id INTEGER PRIMARY KEY,
  date TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open',
  notes TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS sets (
  id INTEGER PRIMARY KEY,
  workout_id INTEGER NOT NULL REFERENCES workouts(id) ON DELETE CASCADE,
  exercise TEXT NOT NULL,
  weight REAL NOT NULL,
  reps INTEGER NOT NULL,
  note TEXT NOT NULL DEFAULT '',
  created TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sets_workout ON sets(workout_id);
CREATE INDEX IF NOT EXISTS idx_sets_exercise ON sets(exercise);
CREATE TABLE IF NOT EXISTS bodyweight (
  id INTEGER PRIMARY KEY,
  date TEXT NOT NULL,
  kg REAL NOT NULL,
  note TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_bw_date ON bodyweight(date);
CREATE TABLE IF NOT EXISTS lift_muscle_map (
  exercise TEXT PRIMARY KEY,
  muscles TEXT NOT NULL,
  is_bodyweight_only INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS set_muscles (
  set_id INTEGER NOT NULL REFERENCES sets(id) ON DELETE CASCADE,
  muscle TEXT NOT NULL,
  PRIMARY KEY (set_id, muscle)
);
CREATE TABLE IF NOT EXISTS progression (
  id INTEGER PRIMARY KEY,
  workout_id INTEGER NOT NULL REFERENCES workouts(id) ON DELETE CASCADE,
  exercise TEXT NOT NULL,
  verdict TEXT NOT NULL,
  next_target TEXT NOT NULL,
  direction TEXT NOT NULL,
  note TEXT NOT NULL DEFAULT '',
  created TEXT NOT NULL,
  UNIQUE (workout_id, exercise)
);
CREATE TABLE IF NOT EXISTS flags (
  id INTEGER PRIMARY KEY,
  subject TEXT NOT NULL,
  reason TEXT NOT NULL,
  created TEXT NOT NULL,
  consumed_at TEXT
);
CREATE TABLE IF NOT EXISTS priority (
  muscle TEXT PRIMARY KEY,
  tier TEXT NOT NULL,
  since TEXT NOT NULL,
  until TEXT
);
CREATE TABLE IF NOT EXISTS deload_state (
  id INTEGER PRIMARY KEY,
  scope TEXT NOT NULL,
  subject TEXT NOT NULL,
  set_on TEXT NOT NULL,
  cleared_on TEXT
);
CREATE TABLE IF NOT EXISTS meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
-- meta has no CLI: plan reads last_compacted, the compaction flow writes it.
CREATE UNIQUE INDEX IF NOT EXISTS idx_deload_active ON deload_state(scope, subject) WHERE cleared_on IS NULL;
CREATE TABLE IF NOT EXISTS splits (
  id INTEGER PRIMARY KEY,
  variant TEXT NOT NULL CHECK (variant IN ('active', 'baseline')),
  day TEXT NOT NULL,
  slot INTEGER NOT NULL,
  movements TEXT NOT NULL,
  sets INTEGER NOT NULL,
  UNIQUE (variant, day, slot)
);
CREATE TABLE IF NOT EXISTS movement_notes (
  id INTEGER PRIMARY KEY,
  exercise TEXT NOT NULL,
  note TEXT NOT NULL,
  created TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS rules (
  id INTEGER PRIMARY KEY,
  subject TEXT NOT NULL,
  text TEXT NOT NULL,
  start_date TEXT NOT NULL,
  expiry TEXT,
  status TEXT NOT NULL DEFAULT 'active',
  created TEXT NOT NULL
);
-- rotation order lives in meta (key rotation, JSON array).
CREATE TABLE IF NOT EXISTS goals (
  id INTEGER PRIMARY KEY,
  exercise TEXT NOT NULL,
  target_e1rm REAL NOT NULL,
  target_desc TEXT NOT NULL,
  deadline TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  created TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS goal_checkpoints (
  goal_id INTEGER NOT NULL REFERENCES goals(id) ON DELETE CASCADE,
  session_no INTEGER NOT NULL,
  target_e1rm REAL NOT NULL,
  PRIMARY KEY (goal_id, session_no)
);
-- trajectories target e1RM with linear per-session interpolation; target
-- choice and realism stay prose (see Goals). Sessions are numbered, dates float.
CREATE TABLE IF NOT EXISTS autoreg_holds (
  id INTEGER PRIMARY KEY,
  day TEXT NOT NULL,
  movements TEXT NOT NULL,
  action TEXT NOT NULL,
  set_on TEXT NOT NULL,
  hold_until TEXT NOT NULL,
  reason TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS autoreg_changes (
  id INTEGER PRIMARY KEY,
  date TEXT NOT NULL,
  action TEXT NOT NULL,
  day TEXT NOT NULL,
  slot INTEGER NOT NULL,
  before_movements TEXT NOT NULL,
  before_sets INTEGER NOT NULL,
  after_movements TEXT NOT NULL,
  after_sets INTEGER NOT NULL,
  evidence TEXT NOT NULL DEFAULT '',
  reverted_on TEXT
);
"""

AUTOREG_HOLD_COLS = {"id", "day", "movements", "action", "set_on", "hold_until", "reason"}
AUTOREG_CHANGE_COLS = {"id", "date", "action", "day", "slot", "before_movements",
                       "before_sets", "after_movements", "after_sets", "evidence", "reverted_on"}


def _drop_legacy_autoreg(c):
    """Drop pre-spec autoreg tables so connect recreates the current shape.

    An older shape of these tables (without slot/before_movements) briefly
    existed in one local DB and was dropped while empty. Nothing ever wrote
    rows to the old shape, so dropping is lossless.
    """
    live = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    if "autoreg_holds" in live:
        cols = {r[1] for r in c.execute("PRAGMA table_info(autoreg_holds)").fetchall()}
        if cols != AUTOREG_HOLD_COLS:
            c.execute("DROP TABLE autoreg_holds")
    if "autoreg_changes" in live:
        cols = {r[1] for r in c.execute("PRAGMA table_info(autoreg_changes)").fetchall()}
        if cols != AUTOREG_CHANGE_COLS:
            c.execute("DROP TABLE autoreg_changes")
    c.commit()


def conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA foreign_keys=ON")
    _drop_legacy_autoreg(c)
    c.executescript(SCHEMA)
    return c


def placeholders(n):
    return ",".join("?" * max(1, n))


def resolve_known_prefix(toks, known, max_words, what):
    """Split tokens into (known name, rest) via longest known-prefix match.

    Exits instead of guessing when nothing matches.
    """
    match = next((i for i in range(min(len(toks) - 1, max_words), 0, -1)
                  if " ".join(toks[:i]).lower() in known), None)
    if match is None:
        sys.exit(f"could not identify the {what}; quote a known name (see map show)")
    return " ".join(toks[:match]), " ".join(toks[match:])


def canon_muscle_name(text, vocab):
    """Canonical muscle name, tolerating a missing plural s (delt -> delts).

    Returns None for unknown names so callers can leave them through for
    audit/doctor to flag instead of guessing.
    """
    t = text.strip().lower()
    if t in vocab:
        return t
    if t + "s" in vocab:
        return t + "s"
    return None


def _join_muscles(words, vocab):
    """Reassemble muscle words into canonical names (multi-word heads re-joined)."""
    out, i = [], 0
    while i < len(words):
        two = canon_muscle_name(" ".join(words[i:i + 2]), vocab) if i + 1 < len(words) else None
        if two is not None:
            out.append(two)
            i += 2
            continue
        one = canon_muscle_name(words[i], vocab)
        out.append(one if one is not None else words[i].lower())
        i += 1
    return out


def clean_muscles(value):
    seen = set()
    out = []
    try:
        vocab = set(load_constants()["muscles"]) | set(load_constants().get("untracked", []))
    except SystemExit:
        vocab = set()
    for p in value.split(","):
        m = p.strip().lower()
        if not m:
            continue
        c = canon_muscle_name(m, vocab) or m
        if c in seen:
            continue
        seen.add(c)
        out.append(c)
    return ",".join(out)


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


def open_workout(c):
    row = c.execute("SELECT * FROM workouts WHERE status = 'open' ORDER BY id DESC LIMIT 1").fetchone()
    return row


def cmd_start(note):
    c = conn()
    existing = open_workout(c)
    if existing:
        sets_n = c.execute("SELECT COUNT(*) n FROM sets WHERE workout_id = ?", (existing["id"],)).fetchone()["n"]
        last = c.execute("SELECT created FROM sets WHERE workout_id = ? ORDER BY id DESC LIMIT 1", (existing["id"],)).fetchone()
        try:
            age_days = (date.today() - date.fromisoformat(existing["date"])).days
        except ValueError:
            age_days = 0
        print(json.dumps({"workout_id": existing["id"], "reused": True, "date": existing["date"],
                          "age_days": age_days, "sets": sets_n,
                          "last_set_created": last["created"] if last else None}))
        return
    today = date.today().isoformat()
    cur = c.execute("INSERT INTO workouts (date, status, notes) VALUES (?, 'open', ?)", (today, note))
    c.commit()
    print(json.dumps({"workout_id": cur.lastrowid, "reused": False, "date": today}))


def cmd_log(exercise, weight, reps, note, muscles, bodyweight=False):
    c = conn()
    w = open_workout(c)
    if not w:
        sys.exit("no open workout, run start first (workouts are only created explicitly)")
    exercise = exercise.strip().lower()
    try:
        weight = float(weight)
    except (TypeError, ValueError):
        sys.exit("weight must be a number")
    try:
        reps = int(reps)
    except (TypeError, ValueError):
        sys.exit("reps must be an integer")
    if weight < 0:
        sys.exit("weight cannot be negative")
    if reps <= 0:
        sys.exit("reps must be a positive integer")
    muscles = clean_muscles(muscles)

    mapping = c.execute("SELECT muscles, is_bodyweight_only FROM lift_muscle_map WHERE exercise = ?", (exercise,)).fetchone()
    if weight == 0:
        if bodyweight:
            pass
        elif not mapping or mapping["is_bodyweight_only"] != 1:
            sys.exit(f"zero weight not allowed for '{exercise}' (not a bodyweight-only exercise, add bw flag for bodyweight moves)")

    if not mapping:
        if not muscles:
            sys.exit(f"muscles= required for new exercise '{exercise}' (no mapping in lift_muscle_map)")
        c.execute("INSERT INTO lift_muscle_map (exercise, muscles, is_bodyweight_only) VALUES (?, ?, ?)",
                  (exercise, muscles, 1 if bodyweight else 0))
    elif not muscles:
        muscles = mapping["muscles"]
    elif bodyweight and mapping["is_bodyweight_only"] != 1:
        c.execute("UPDATE lift_muscle_map SET is_bodyweight_only = 1 WHERE exercise = ?", (exercise,))

    constants = load_constants()
    warn_ratio = constants["thresholds"].get("e1rm_warn_ratio", 1.5)
    dup_dist = constants["thresholds"].get("duplicate_name_distance", 2)
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
    if mapping and muscles and set(muscles.split(",")) != set(mapping["muscles"].split(",")):
        sys.exit(f"logged muscles {muscles} differ from the mapping for '{exercise}' ({mapping['muscles']}); "
                 f"the mapping is authoritative, log a genuine variation under its own exercise name "
                 f"or change it everywhere with map set")

    wid = w["id"]
    created = datetime.now().isoformat(timespec="seconds")
    cur = c.execute(
        "INSERT INTO sets (workout_id, exercise, weight, reps, note, created) VALUES (?, ?, ?, ?, ?, ?)",
        (wid, exercise, weight, reps, note, created),
    )
    set_id = cur.lastrowid
    # Populate set_muscles junction table
    for muscle in muscles.split(","):
        c.execute("INSERT INTO set_muscles (set_id, muscle) VALUES (?, ?)", (set_id, muscle))
    c.commit()
    out = {"set_id": set_id, "workout_id": wid}
    if warnings:
        out["warnings"] = warnings
    print(json.dumps(out))


def cmd_update(set_id, field, value):
    allowed = {"weight", "reps", "exercise", "note"}
    if field == "muscles":
        sys.exit("per-set muscles are gone, the mapping is authoritative; run map set <exercise> <muscles>")
    if field not in allowed:
        sys.exit("field must be one of weight reps exercise note")
    c = conn()
    try:
        set_id = int(set_id)
    except (TypeError, ValueError):
        sys.exit("no such set")
    existing = c.execute("SELECT * FROM sets WHERE id = ?", (set_id,)).fetchone()
    if not existing:
        sys.exit("no such set")
    if field == "exercise":
        value = value.strip().lower()
    if field == "weight":
        if value == "":
            sys.exit("weight cannot be empty, pass a number or delete the set")
        try:
            value = float(value)
        except (TypeError, ValueError):
            sys.exit("weight must be a number")
        if value < 0:
            sys.exit("weight cannot be negative")
        # Validate zero-weight against exercise type
        if value == 0:
            mapping = c.execute("SELECT is_bodyweight_only FROM lift_muscle_map WHERE exercise = ?", (existing["exercise"],)).fetchone()
            if not mapping or mapping["is_bodyweight_only"] != 1:
                sys.exit(f"zero weight not allowed for '{existing['exercise']}' (not a bodyweight-only exercise)")
    if field == "reps":
        try:
            value = int(value)
        except (TypeError, ValueError):
            sys.exit("reps must be an integer")
        if value <= 0:
            sys.exit("reps must be a positive integer")
    if field == "exercise":
        mapping = c.execute("SELECT muscles FROM lift_muscle_map WHERE exercise = ?", (value,)).fetchone()
        if not mapping:
            sys.exit(f"exercise '{value}' has no mapping (run map set first)")
        c.execute("DELETE FROM set_muscles WHERE set_id = ?", (set_id,))
        for muscle in mapping["muscles"].split(","):
            c.execute("INSERT INTO set_muscles (set_id, muscle) VALUES (?, ?)", (set_id, muscle))
    warnings = []
    if field in ("weight", "reps"):
        new_weight = value if field == "weight" else existing["weight"]
        new_reps = value if field == "reps" else existing["reps"]
        if new_weight > 0:
            new_e1rm = e1rm_of(new_weight, new_reps)
            best = best_e1rm(c, existing["exercise"], exclude_set=int(set_id))
            warn_ratio = load_constants()["thresholds"].get("e1rm_warn_ratio", 1.5)
            if best > 0 and new_e1rm > best * warn_ratio:
                warnings.append(f"e1RM {new_e1rm:.1f} is over {round((warn_ratio - 1) * 100)}% above best {best:.1f} for '{existing['exercise']}'; confirm weight and reps")
    c.execute("UPDATE sets SET {} = ? WHERE id = ?".format(field), (value, int(set_id)))
    c.commit()
    out = {"updated": int(set_id)}
    if warnings:
        out["warnings"] = warnings
    print(json.dumps(out))


def cmd_end(note, force=None):
    c = conn()
    w = open_workout(c)
    if not w:
        sys.exit("no open workout")
    outstanding = end_gate_items(c, w, note if not force else (note + f" {force}" if note else force))
    hard = [o for o in outstanding if o.get("hard")]
    if hard:
        print(f"cannot close workout {w['id']}, {len(hard)} hard items outstanding (--force cannot skip these):\n")
        for o in hard:
            print(f"  {o['item']}\n    {o['fix']}")
        sys.exit(1)
    if outstanding and not force:
        print(f"cannot close workout {w['id']}, {len(outstanding)} items outstanding:\n")
        for o in outstanding:
            print(f"  {o['item']}\n    {o['fix']}")
        print(f"\nor: log.py end --force \"<reason>\"   (reason is written into the workout note; "
              f"writeback items only, missing muscles always block)")
        sys.exit(1)
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
    print(json.dumps(out))


def cmd_rest(day, note):
    try:
        day = date.fromisoformat(day).isoformat()
    except ValueError:
        sys.exit("date must be YYYY-MM-DD")
    c = conn()
    if date.fromisoformat(day) > date.today():
        sys.exit("rest date cannot be in the future")
    if open_workout(c):
        sys.exit("open workout exists, end or delete it before marking a rest day")
    rows = c.execute("SELECT * FROM workouts WHERE date = ?", (day,)).fetchall()
    if any(r["status"] != "rest" for r in rows):
        sys.exit(f"already trained on {day}, cannot mark it rest")
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
        print(json.dumps({"rest_id": rid, "date": day, "appended": appended}))
        return
    cur = c.execute("INSERT INTO workouts (date, status, notes) VALUES (?, 'rest', ?)", (day, note))
    c.commit()
    print(json.dumps({"rest_id": cur.lastrowid, "date": day, "appended": False}))


def cmd_today():
    c = conn()
    w = open_workout(c)
    today = date.today().isoformat()
    rest = c.execute("SELECT * FROM workouts WHERE date = ? AND status = 'rest' ORDER BY id", (today,)).fetchone()
    rest_json = dict(rest) if rest else None
    if not w:
        print(json.dumps({"open": False, "rest": rest_json}))
        return
    sets = c.execute("SELECT * FROM sets WHERE workout_id = ? ORDER BY id", (w["id"],)).fetchall()
    print(json.dumps({"open": True, "workout": dict(w), "sets": attach_muscles(c, sets), "rest": rest_json}, indent=2))


def cmd_exercises():
    c = conn()
    rows = c.execute("SELECT DISTINCT exercise FROM sets ORDER BY exercise").fetchall()
    print(json.dumps([r["exercise"] for r in rows], indent=2))


def cmd_history(exercise, limit):
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        sys.exit("limit must be an integer")
    c = conn()
    rows = c.execute(
        "SELECT s.*, w.date FROM sets s JOIN workouts w ON w.id = s.workout_id WHERE s.exercise = ? ORDER BY s.id DESC LIMIT ?",
        (exercise.strip().lower(), limit),
    ).fetchall()
    print(json.dumps(attach_muscles(c, rows), indent=2))


def cmd_stats():
    c = conn()
    workouts = c.execute("SELECT id, date, status FROM workouts ORDER BY date").fetchall()
    out = {"workouts": len([w for w in workouts if w["status"] != "rest"]), "by_exercise": {}}
    rows = c.execute("SELECT exercise, COUNT(*) n, MAX(CASE WHEN reps = 1 THEN weight ELSE weight * (1 + reps / 30.0) END) max_e1rm, MAX(weight) max_w FROM sets GROUP BY exercise").fetchall()

    for r in rows:
        out["by_exercise"][r["exercise"]] = {"sets": r["n"], "max_weight": r["max_w"], "max_e1rm": round(r["max_e1rm"], 1)}
    print(json.dumps(out, indent=2))


def build_snapshot(c=None):
    """Full dashboard payload. Worker ignores unknown fields, so the CLI can
    extend this without breaking the page. Missing tables never fail: a fresh
    DB exports history plus empty forward sections."""
    c = c or conn()
    workouts = [dict(r) for r in c.execute("SELECT * FROM workouts ORDER BY id").fetchall()]
    sets = attach_muscles(c, c.execute("SELECT * FROM sets ORDER BY id").fetchall())
    bw = [dict(r) for r in c.execute("SELECT * FROM bodyweight ORDER BY date, id").fetchall()]
    try:
        constants = load_constants()
    except SystemExit:
        constants = None
    try:
        split_active = read_split("active", c=c)
    except sqlite3.Error:
        split_active = []
    try:
        rotation = parse_rotation(c)
    except sqlite3.Error:
        rotation = []
    try:
        progression = {r["exercise"]: {"verdict": r["verdict"], "next": r["next_target"],
                                       "direction": r["direction"], "workout_id": r["workout_id"]}
                       for r in c.execute(
                           "SELECT p.* FROM progression p JOIN (SELECT exercise, MAX(workout_id) m FROM progression "
                           "GROUP BY exercise) l ON l.exercise = p.exercise AND l.m = p.workout_id").fetchall()}
    except sqlite3.Error:
        progression = {}
    goals = []
    try:
        for g in c.execute("SELECT * FROM goals WHERE status = 'active' ORDER BY deadline").fetchall():
            entry = dict(g)
            try:
                entry.update(goal_progress(c, dict(g)))
            except (sqlite3.Error, SystemExit):
                pass
            goals.append(entry)
    except sqlite3.Error:
        goals = []
    try:
        priority = read_priorities(c)
    except sqlite3.Error:
        priority = {}
    try:
        deload = [dict(r) for r in active_deloads(c)]
    except sqlite3.Error:
        deload = []
    try:
        rules = rules_with_confirm(c)
    except sqlite3.Error:
        rules = []
    try:
        flags = [dict(r) for r in c.execute("SELECT * FROM flags WHERE consumed_at IS NULL ORDER BY id").fetchall()]
    except sqlite3.Error:
        flags = []
    try:
        mapping = [dict(r) for r in c.execute("SELECT * FROM lift_muscle_map ORDER BY exercise").fetchall()]
    except sqlite3.Error:
        mapping = []
    try:
        movement_notes = [dict(r) for r in c.execute("SELECT * FROM movement_notes ORDER BY exercise, id").fetchall()]
    except sqlite3.Error:
        movement_notes = []
    return {"exported": datetime.now().isoformat(timespec="seconds"), "workouts": workouts, "sets": sets,
            "bodyweight": bw, "split_active": split_active, "rotation": rotation, "constants": constants,
            "progression": progression, "goals": goals, "priority": priority, "deload": deload,
            "rules": rules, "flags": flags, "mapping": mapping, "movement_notes": movement_notes}


def cmd_export():
    print(json.dumps(build_snapshot(), indent=2))


def cmd_weigh(kg, note):
    c = conn()
    today = date.today().isoformat()
    try:
        kg = float(kg)
    except (TypeError, ValueError):
        sys.exit("bodyweight must be a number")
    if kg <= 0:
        sys.exit("bodyweight must be positive")
    if kg < 20 or kg > 300:
        sys.exit(f"bodyweight {kg}kg is implausible, confirm the value")
    cur = c.execute("INSERT INTO bodyweight (date, kg, note) VALUES (?, ?, ?)", (today, kg, note))
    c.commit()
    print(json.dumps({"weigh_id": cur.lastrowid, "date": today, "kg": kg}))


def cmd_restore(force=False):
    if not force:
        try:
            rc = sqlite3.connect(DB)
            row = rc.execute("SELECT id FROM workouts WHERE status = 'open' ORDER BY id DESC LIMIT 1").fetchone()
            rc.close()
            if row:
                sys.exit(f"workout {row[0]} is still open; end or delete it before restore, or use restore force")
        except sqlite3.Error:
            pass
    sql_file = os.path.join(os.path.dirname(DB), "workouts.sql")
    if not os.path.exists(sql_file):
        sys.exit("no workouts.sql found, cannot restore")
    # Build into a temp file first so a malformed dump can never empty the
    # live DB: the live file is only replaced after the restore verifies.
    import tempfile
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(DB)), suffix=".restore.db")
    os.close(fd)
    try:
        try:
            t = sqlite3.connect(tmp)
            with open(sql_file, 'r') as f:
                t.executescript(f.read())
            t.commit()
        except sqlite3.Error as e:
            sys.exit(f"dump failed to load ({e}), live DB untouched")
        if t.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            sys.exit("restored DB failed integrity check, live DB untouched")
        tables = {r[0] for r in t.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        expected = set(re.findall(r"CREATE TABLE IF NOT EXISTS (\w+)", SCHEMA))
        if tables != expected:
            sys.exit(f"dump is missing tables (has {sorted(tables)}, expected {sorted(expected)}), live DB untouched")
        t.close()
        try:
            live = sqlite3.connect(DB)
            live.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
            live.close()
        except sqlite3.Error:
            pass
        try:
            os.replace(tmp, DB)
        except OSError as e:
            sys.exit(f"restore failed to replace live DB ({e}), live DB untouched")
        for suffix in ("-wal", "-shm", "-journal"):
            try:
                os.remove(DB + suffix)
            except OSError:
                pass
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass
    print(json.dumps({"restored": True, "from": sql_file}))


def validate_constants(raw, source):
    """Validate a parsed constants candidate, exiting loudly on any defect."""
    if not isinstance(raw, dict) or not isinstance(raw.get("muscles"), dict) or not raw["muscles"]:
        sys.exit(f"constants invalid at {source}: missing or empty the muscles map")
    for muscle, entry in raw["muscles"].items():
        if not isinstance(entry, dict):
            sys.exit(f"constants invalid at {source}: muscle '{muscle}' is not an object")
        if not isinstance(entry.get("mev"), int) or isinstance(entry.get("mev"), bool) or entry["mev"] < 0:
            sys.exit(f"constants invalid at {source}: muscle '{muscle}' needs a non-negative mev")
        for bound in ("mav", "mrv"):
            val = entry.get(bound)
            if val is None:
                continue
            if bound == "mav":
                if (not isinstance(val, list) or len(val) != 2
                        or not all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in val)
                        or val[0] > val[1]):
                    sys.exit(f"constants invalid at {source}: muscle '{muscle}' needs {bound} as [lo, hi]")
            elif not isinstance(val, (int, float)) or isinstance(val, bool) or val < 0:
                sys.exit(f"constants invalid at {source}: muscle '{muscle}' needs a non-negative {bound}")
        freq = entry.get("freq")
        if (not isinstance(freq, list) or len(freq) != 2
                or not all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in freq)
                or freq[0] > freq[1]):
            sys.exit(f"constants invalid at {source}: muscle '{muscle}' needs freq as [lo, hi]")
        if entry.get("tier") not in ("settled", "contested", "opinion"):
            sys.exit(f"constants invalid at {source}: muscle '{muscle}' needs a tier")
        if not isinstance(entry.get("source"), str):
            sys.exit(f"constants invalid at {source}: muscle '{muscle}' needs a source string")
        if not isinstance(entry.get("color"), str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", entry["color"]):
            sys.exit(f"constants invalid at {source}: muscle '{muscle}' needs a #rrggbb color string")
    thresholds = raw.get("thresholds")
    if not isinstance(thresholds, dict):
        sys.exit(f"constants invalid at {source}: missing thresholds map")
    for key in ("stale_workout_hours", "stale_workout_days", "break_days",
                "e1rm_warn_ratio", "duplicate_name_distance"):
        val = thresholds.get(key)
        if not isinstance(val, (int, float)) or isinstance(val, bool) or val <= 0:
            sys.exit(f"constants invalid at {source}: thresholds.{key} must be positive")
    for key in ("volume_window_weeks", "volume_bad_weeks", "ledger_retention_days", "default_new_slot_sets"):
        val = thresholds.get(key)
        if not isinstance(val, int) or isinstance(val, bool) or val <= 0:
            sys.exit(f"constants invalid at {source}: thresholds.{key} must be a positive integer")
    drop = thresholds.get("progression_drop_pct")
    if not isinstance(drop, (int, float)) or isinstance(drop, bool) or drop >= 0:
        sys.exit(f"constants invalid at {source}: thresholds.progression_drop_pct must be negative")
    bands = raw.get("rep_bands")
    if not isinstance(bands, list) or not bands:
        sys.exit(f"constants invalid at {source}: missing rep_bands")
    prev_max = -1
    for band in bands:
        if not isinstance(band, dict):
            sys.exit(f"constants invalid at {source}: rep_bands entries must be objects")
        max_reps, jump = band.get("max_reps"), band.get("jump_pct")
        if max_reps is None and jump is None:
            continue
        if (not isinstance(max_reps, int) or isinstance(max_reps, bool) or max_reps <= prev_max
                or not isinstance(jump, (int, float)) or jump <= 0):
            sys.exit(f"constants invalid at {source}: rep_bands must order ascending max_reps with positive jump_pct")
        prev_max = max_reps
    return raw


def load_constants():
    """Load constants.json, the single source of truth for taxonomy and thresholds.

    Fails loudly on parse error or missing tracked muscle. No silent fallback.
    CONTRACT_MUSCLES is the completeness gate, not a parallel source: the file
    owns every number, the gate only names which muscles must be present.
    """
    try:
        with open(CONSTANTS_FILE, 'r') as f:
            raw = json.load(f)
    except (OSError, ValueError) as e:
        sys.exit(f"constants.json unreadable at {CONSTANTS_FILE} ({e}), fix or restore it")
    return validate_constants(raw, CONSTANTS_FILE)


def parse_mev_from_science():
    """Backward-compatible MEV map, now derived from constants.json."""
    constants = load_constants()
    return {muscle: entry["mev"] for muscle, entry in constants["muscles"].items()}


def rep_band_bound(reps):
    """Jump threshold for given reps, from constants.json rep_bands. None above 15."""
    constants = load_constants()
    for band in constants["rep_bands"]:
        max_reps = band.get("max_reps")
        if max_reps is None:
            return None
        if reps <= max_reps:
            return band.get("jump_pct")
    return None


def tracked_muscles():
    """Ordered tracked muscle list from constants.json."""
    return list(load_constants()["muscles"].keys())


def read_priorities(c):
    """Effective priority tiers. Absence means maintain; expired rows no longer apply."""
    today = date.today().isoformat()
    return {r["muscle"]: {"tier": r["tier"], "since": r["since"], "until": r["until"]}
            for r in c.execute("SELECT * FROM priority").fetchall()
            if r["until"] is None or r["until"] >= today}


def priority_needs_confirm(c):
    """Expired or soon-expiring tiers, for the renew-or-revert moment."""
    today = date.today()
    out = []
    for r in c.execute("SELECT * FROM priority").fetchall():
        if r["until"] and (date.fromisoformat(r["until"]) - today).days <= 7:
            out.append({"type": "priority", "muscle": r["muscle"], "tier": r["tier"],
                        "until": r["until"],
                        "expired": date.fromisoformat(r["until"]) < today})
    return out


def cmd_constants_show(key=None):
    constants = load_constants()
    if not key:
        print(json.dumps(constants, indent=2))
        return
    parts = key.split(".")
    node = constants
    for part in parts:
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            sys.exit(f"constants key '{key}' not found")
    print(json.dumps(node, indent=2))


def cmd_constants_validate():
    load_constants()
    print(json.dumps({"valid": True, "file": CONSTANTS_FILE}))


def cmd_constants_set(key, value):
    try:
        parsed = json.loads(value)
    except ValueError:
        parsed = value
    try:
        with open(CONSTANTS_FILE, 'r') as f:
            raw = json.load(f)
    except (OSError, ValueError) as e:
        sys.exit(f"constants.json unreadable at {CONSTANTS_FILE} ({e})")
    parts = key.split(".")
    node = raw
    for part in parts[:-1]:
        if not isinstance(node, dict) or part not in node:
            sys.exit(f"constants key '{key}' not found")
        node = node[part]
    if not isinstance(node, dict) or parts[-1] not in node:
        sys.exit(f"constants key '{key}' not found")
    node[parts[-1]] = parsed
    validate_constants(raw, f"candidate for {key}")
    import tempfile
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(CONSTANTS_FILE)), suffix=".constants")
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(raw, f, indent=2)
            f.write("\n")
        os.replace(tmp, CONSTANTS_FILE)
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass
    load_constants()
    print(json.dumps({"set": key, "value": parsed}))


def parse_movements(text):
    """Split a stored movements cell into a list of canonical names."""
    return [m.strip().lower() for m in text.split("/") if m.strip()]


def split_day_order(variant="active", c=None):
    """Day names in rotation order (rest entries excluded)."""
    c = c or conn()
    days = [r["day"] for r in c.execute(
        "SELECT DISTINCT day FROM splits WHERE variant = ?", (variant,)).fetchall()]
    rotation = parse_rotation(c)
    order = [d for d in rotation if d in days]
    return order + [d for d in sorted(days) if d not in order]


def read_split(variant="active", day=None, c=None):
    """Split rows as [{day, slot, movements, sets}], optionally one day."""
    c = c or conn()
    if day:
        rows = c.execute("SELECT day, slot, movements, sets FROM splits WHERE variant = ? AND day = ? ORDER BY slot",
                         (variant, day)).fetchall()
    else:
        rows = c.execute("SELECT day, slot, movements, sets FROM splits WHERE variant = ? ORDER BY day, slot",
                         (variant,)).fetchall()
    return [dict(r) for r in rows]


def parse_active_split_days(c=None):
    """Active split as {day: [movement, ...]} with interchangeable entries flattened."""
    days = {}
    for r in read_split("active", c=c):
        moves = days.setdefault(r["day"], [])
        for move in r["movements"].split("/"):
            move = move.strip().lower()
            if move:
                moves.append(move)
    return days


def parse_rotation(c=None):
    """Rotation order from meta."""
    c = c or conn()
    try:
        row = c.execute("SELECT value FROM meta WHERE key = 'rotation'").fetchone()
        return json.loads(row["value"]) if row else []
    except (sqlite3.Error, ValueError):
        return []


def weekly_volume(c, muscle, week_starts):
    from datetime import timedelta
    base = week_starts[0].isoformat()
    rows = c.execute("""
        SELECT date(w.date) as day, COUNT(*) as sets
        FROM sets s
        JOIN workouts w ON w.id = s.workout_id
        JOIN set_muscles sm ON sm.set_id = s.id
        WHERE sm.muscle = ? AND date(w.date) >= ?
        GROUP BY day
    """, (muscle, base)).fetchall()
    per_day = {r["day"]: r["sets"] for r in rows}
    out = []
    for ws in week_starts:
        we = ws + timedelta(days=7)
        out.append(sum(n for d, n in per_day.items() if ws.isoformat() <= d < we.isoformat()))
    return out


def count_bad_weeks(weekly, mev):
    """Zero and low week counts over the whole window (audit check 8 rule)."""
    if mev == 0:
        # MEV 0 means no direct work is required (covered indirectly),
        # so zero-set weeks meet the floor and never flag.
        return (0, 0)
    return (sum(1 for n in weekly if n == 0),
            sum(1 for n in weekly if 0 < n < mev))


def classify_volume(weekly, mev, mrv, vol_bad):
    """Shared volume classifier for plan status and audit flags.

    Below-MEV mirrors audit check 8 exactly (zero or low weeks counted over
    the whole window); above-MRV uses the recent-4-week average.
    """
    zero_weeks, low_weeks = count_bad_weeks(weekly, mev)
    if zero_weeks >= vol_bad or low_weeks >= vol_bad:
        return "below_mev"
    recent = weekly[-4:] if len(weekly) >= 4 else weekly
    avg = sum(recent) / len(recent) if recent else 0
    if mrv is not None and avg > mrv:
        return "above_mrv"
    return "in_range"


def meta_get(c, key):
    row = c.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def compaction_due():
    # Meta only. Nothing in log.py parses prose for this fact.
    c = conn()
    last = meta_get(c, "last_compacted")
    if last in (None, "", "never"):
        last = None
    postponed = meta_get(c, "compaction_postponed_until")
    if postponed:
        try:
            if date.today() < date.fromisoformat(postponed):
                return {"due": False, "last": last}
        except ValueError:
            pass
    if last is None:
        return {"due": date.today().day != 1, "last": None}
    try:
        last_date = datetime.strptime(last, "%b %d %Y").date()
    except ValueError:
        return {"due": False, "last": last}
    first = date.today().replace(day=1)
    return {"due": date.today() > first and last_date < first, "last": last}


def cmd_meta_show(key=None):
    c = conn()
    if key:
        print(json.dumps({key: meta_get(c, key)}))
        return
    print(json.dumps({r["key"]: r["value"] for r in c.execute("SELECT key, value FROM meta ORDER BY key")}, indent=2))


def cmd_meta_set(key, value):
    if key not in ("last_compacted", "compaction_postponed_until", "rotation"):
        sys.exit("meta key must be one of last_compacted compaction_postponed_until rotation")
    if key == "last_compacted" and value not in ("never", ""):
        try:
            datetime.strptime(value, "%b %d %Y")
        except ValueError:
            sys.exit('last_compacted must be "never" or "Mon D YYYY" (e.g. Oct 1 2026)')
    if key == "compaction_postponed_until":
        try:
            value = date.fromisoformat(value).isoformat()
        except ValueError:
            sys.exit("compaction_postponed_until must be YYYY-MM-DD")
    if key == "rotation":
        try:
            parsed = json.loads(value)
        except ValueError:
            sys.exit("rotation must be a JSON array")
        if not isinstance(parsed, list) or not parsed:
            sys.exit("rotation must be a non-empty JSON array")
        value = json.dumps(parsed)
    c = conn()
    c.execute("INSERT INTO meta (key, value) VALUES (?, ?) "
              "ON CONFLICT (key) DO UPDATE SET value = excluded.value", (key, value))
    c.commit()
    print(json.dumps({"meta": key, "value": value}))


def autoreg_permitted(c):
    """True iff an active rule with subject autoreg authorizes the coach pass."""
    return any(r["subject"] == "autoreg" for r in rule_status_rows(c))


def autoreg_active_holds(c, today=None):
    """Unexpired autoreg_holds rows, oldest first."""
    today = today or date.today().isoformat()
    return [dict(r) for r in c.execute(
        "SELECT * FROM autoreg_holds WHERE hold_until >= ? ORDER BY id", (today,)).fetchall()]


def autoreg_miss_streaks(c):
    """Exercises ending in 2+ consecutive miss progression verdicts, newest first."""
    out = []
    for r in c.execute("SELECT DISTINCT exercise FROM progression").fetchall():
        ex = r["exercise"]
        rows = c.execute("SELECT verdict, workout_id FROM progression WHERE exercise = ? "
                         "ORDER BY workout_id DESC", (ex,)).fetchall()
        streak = 0
        for p in rows:
            if p["verdict"] == "miss":
                streak += 1
            else:
                break
        if streak >= 2:
            out.append({"exercise": ex, "streak": streak, "workout_id": rows[0]["workout_id"]})
    out.sort(key=lambda e: e["workout_id"], reverse=True)
    return [{"exercise": e["exercise"], "streak": e["streak"]} for e in out]


def autoreg_drop_watch(c):
    """Exercises whose last 3 top-set e1RMs show two consecutive drops at deload_watch_pct size.

    Deload sessions are filtered out first (they deliberately deviate).
    Deterministic reuse of top_e1rm_by_date, same shape as the Session report watch.
    """
    threshold = load_constants()["thresholds"].get("deload_watch_pct", -5)
    out = []
    for r in c.execute("SELECT DISTINCT exercise FROM sets").fetchall():
        ex = r["exercise"]
        clean = [(day, e) for day, e, notes, _ in top_e1rm_by_date(c, ex)
                 if "deload" not in (notes or "").lower()]
        if len(clean) < 3:
            continue
        (_, e1), (_, e2), (_, e3) = clean[-3:]
        if e1 <= 0 or e2 <= 0:
            continue
        p1, p2 = (e2 - e1) / e1 * 100, (e3 - e2) / e2 * 100
        if p1 <= threshold and p2 <= threshold:
            out.append({"exercise": ex, "drops_pct": [round(p1, 1), round(p2, 1)]})
    return sorted(out, key=lambda e: e["exercise"])


def autoreg_grouped(c, flagged):
    """Flagged lifts sharing a muscle with 2+ members each, via the mapping table."""
    groups: dict = {}
    for ex in flagged:
        mapping = c.execute("SELECT muscles FROM lift_muscle_map WHERE exercise = ?", (ex,)).fetchone()
        if not mapping:
            continue
        for mu in mapping["muscles"].split(","):
            groups.setdefault(mu, set()).add(ex)
    return {mu: sorted(members) for mu, members in sorted(groups.items()) if len(members) >= 2}


def programmed_weekly_volume(c, split_rows=None):
    """Programmed weekly sets per muscle from the active split and rotation.

    Full credit per mapped muscle like plan volume, scaled from cycle length
    to a week. All tracked muscles initialize at zero so removed muscles read
    0, not absent. Unmapped movements contribute nothing.
    """
    constants = load_constants()
    totals = {m: 0 for m in constants["muscles"]}
    rows = split_rows if split_rows is not None else read_split("active", c=c)
    for r in rows:
        for move in parse_movements(r["movements"]):
            mapping = c.execute("SELECT muscles FROM lift_muscle_map WHERE exercise = ?", (move,)).fetchone()
            if not mapping:
                continue
            for mu in mapping["muscles"].split(","):
                if mu in totals:
                    totals[mu] += r["sets"]
    cycle = parse_rotation(c)
    cycle_days = len(cycle) if cycle else 7
    return {m: round(v * 7.0 / cycle_days, 1) for m, v in totals.items()}


def muscles_for_movements(c, text):
    """Tracked and untracked mapped muscles for a movements cell."""
    out = set()
    for move in parse_movements(text):
        mapping = c.execute("SELECT muscles FROM lift_muscle_map WHERE exercise = ?", (move,)).fetchone()
        if mapping:
            out.update(mapping["muscles"].split(","))
    return out


def mev_floor_warnings(after_vol, affected):
    """Below-MEV warnings scoped to edited muscles only. MEV 0 muscles never warn."""
    constants = load_constants()
    out = []
    for m in sorted(affected):
        entry = constants["muscles"].get(m)
        if entry is None or entry["mev"] == 0:
            continue
        if after_vol.get(m, 0) < entry["mev"]:
            out.append(f"{m}: programmed {after_vol.get(m, 0)}/wk below MEV {entry['mev']} after this edit")
    return out


def autoreg_block(c):
    """Fresh autoreg signal bundle for plan."""
    miss = autoreg_miss_streaks(c)
    drop = autoreg_drop_watch(c)
    flagged = sorted({m["exercise"] for m in miss} | {d["exercise"] for d in drop})
    return {"permitted": autoreg_permitted(c),
            "holds": autoreg_active_holds(c),
            "miss_streaks": miss,
            "drop_watch": drop,
            "grouped": autoreg_grouped(c, flagged),
            "program_volume": programmed_weekly_volume(c)}


def cmd_plan(slot=None, verbose=False):
    from datetime import timedelta
    c = conn()
    constants = load_constants()
    thresholds = constants["thresholds"]
    today = date.today()
    today_iso = today.isoformat()

    w = open_workout(c)
    rest_row = c.execute("SELECT * FROM workouts WHERE date = ? AND status = 'rest' ORDER BY id", (today_iso,)).fetchone()
    stale = None
    if w:
        try:
            age_days = (today - date.fromisoformat(w["date"])).days
        except ValueError:
            age_days = 0
        last = c.execute("SELECT created FROM sets WHERE workout_id = ? ORDER BY id DESC LIMIT 1", (w["id"],)).fetchone()
        last_created = last["created"] if last else None
        gap_over = False
        if last_created:
            try:
                gap_over = (datetime.now() - datetime.fromisoformat(last_created)).total_seconds() > thresholds["stale_workout_hours"] * 3600
            except ValueError:
                gap_over = False
        is_stale = w["date"] != today_iso or age_days >= thresholds["stale_workout_days"] or gap_over
        stale = {"is_stale": is_stale, "age_days": age_days, "last_set_created": last_created}
    last_done = c.execute(
        "SELECT date FROM workouts WHERE status = 'done' "
        "AND EXISTS (SELECT 1 FROM sets s WHERE s.workout_id = workouts.id) "
        "ORDER BY date DESC, id DESC LIMIT 1").fetchone()
    last_session = last_done["date"] if last_done else None
    gap_days = (today - date.fromisoformat(last_session)).days if last_session else None
    on_break = gap_days is not None and gap_days >= thresholds["break_days"] + 1

    days = parse_active_split_days(c)
    rotation = parse_rotation(c)
    slot_guess = {"day": None, "basis": "no history", "confidence": "low"}
    if slot:
        slot_guess = {"day": slot, "basis": "explicit --slot", "confidence": "high"}
    else:
        last_with_sets = c.execute(
            "SELECT w.date, w.id FROM workouts w WHERE w.status = 'done' "
            "AND EXISTS (SELECT 1 FROM sets s WHERE s.workout_id = w.id) "
            "ORDER BY w.date DESC, w.id DESC LIMIT 1").fetchone()
        if last_with_sets and days:
            trained = {r["exercise"] for r in c.execute(
                "SELECT DISTINCT exercise FROM sets WHERE workout_id = ?", (last_with_sets["id"],)).fetchall()}
            best_score = 0
            best_days = []
            for day, moves in days.items():
                score = len(trained & set(moves))
                if score > best_score:
                    best_score, best_days = score, [day]
                elif score == best_score and score > 0:
                    best_days.append(day)
            if len(best_days) > 1:
                slot_guess = {"day": None, "basis": f"last session matches {', '.join(best_days)} equally", "confidence": "low"}
                best_day = None
            else:
                best_day = best_days[0] if best_days else None
            if best_day and rotation:
                try:
                    idx = rotation.index(best_day)
                except ValueError:
                    idx = None
                if idx is not None:
                    skipped = []
                    j = (idx + 1) % len(rotation)
                    while rotation[j].lower() == "rest":
                        skipped.append(rotation[j])
                        j = (j + 1) % len(rotation)
                    nxt = rotation[j]
                    basis = f"last trained {best_day} ({last_with_sets['date']}), rotation {best_day}->{nxt}"
                    if skipped:
                        basis += " (rest day sits between)"
                    slot_guess = {"day": nxt, "basis": basis,
                                  "confidence": "high" if best_score == len(trained) else "medium"}
            elif best_day:
                slot_guess = {"day": None, "basis": f"last trained {best_day}, rotation unparseable", "confidence": "low"}

    vol_weeks = thresholds["volume_window_weeks"]
    week_starts = [today - timedelta(days=today.weekday() + 7 * i) for i in range(vol_weeks - 1, -1, -1)]
    vol_bad = thresholds["volume_bad_weeks"]
    volume = {}
    for muscle, entry in constants["muscles"].items():
        weekly = weekly_volume(c, muscle, week_starts)
        volume[muscle] = {"weekly": weekly, "mev": entry["mev"], "mav": entry["mav"],
                          "mrv": entry["mrv"], "freq": entry["freq"],
                          "status": classify_volume(weekly, entry["mev"], entry["mrv"], vol_bad)}

    retention = thresholds["ledger_retention_days"]
    cutoff = (today - timedelta(days=retention - 1)).isoformat()
    ledger = {}
    for muscle in constants["muscles"]:
        rows = c.execute("""
            SELECT w.date as day, COUNT(*) as sets
            FROM sets s
            JOIN workouts w ON w.id = s.workout_id
            JOIN set_muscles sm ON sm.set_id = s.id
            WHERE sm.muscle = ? AND date(w.date) >= ?
            GROUP BY day ORDER BY day
        """, (muscle, cutoff)).fetchall()
        ledger[muscle] = {"sessions": len(rows), "sets": sum(r["sets"] for r in rows),
                          "last_hit": rows[-1]["day"] if rows else None}

    lifts = []
    for r in c.execute("SELECT exercise, COUNT(*) n FROM sets GROUP BY exercise ORDER BY exercise").fetchall():
        top = c.execute(
            "SELECT weight, reps, CASE WHEN reps = 1 THEN weight ELSE weight * (1 + reps / 30.0) END AS e1rm "
            "FROM sets WHERE exercise = ? ORDER BY e1rm DESC LIMIT 1", (r["exercise"],)).fetchone()
        last = c.execute(
            "SELECT s.weight, s.reps FROM sets s JOIN workouts w ON w.id = s.workout_id "
            "WHERE s.exercise = ? ORDER BY w.date DESC, s.id DESC LIMIT 1", (r["exercise"],)).fetchone()
        lifts.append({"exercise": r["exercise"], "sets": r["n"],
                      "best_e1rm": round(top["e1rm"], 1) if top else None,
                      "last": dict(last) if last else None})

    progression = {r["exercise"]: {"verdict": r["verdict"], "next": r["next_target"],
                                                "direction": r["direction"], "workout_id": r["workout_id"]}
                   for r in c.execute(
                       "SELECT p.* FROM progression p JOIN (SELECT exercise, MAX(workout_id) m FROM progression "
                       "GROUP BY exercise) l ON l.exercise = p.exercise AND l.m = p.workout_id").fetchall()}
    priorities = read_priorities(c)
    deload = [dict(r) for r in active_deloads(c)]
    # Reading never consumes: consumption happens at `end` (flags touching the
    # closed session) or via explicit `flag consume`. Re-running plan is free.
    unconsumed = [dict(r) for r in c.execute("SELECT * FROM flags WHERE consumed_at IS NULL ORDER BY id").fetchall()]

    split_day = slot or slot_guess.get("day")
    split_section = None
    if split_day and read_split("active", split_day, c=c):
        slots = []
        for r in read_split("active", split_day, c=c):
            moves = parse_movements(r["movements"])
            entry = {"slot": r["slot"], "movements": moves, "sets": r["sets"],
                     "progression": {m: progression.get(m) for m in moves},
                     "flags": [f for f in unconsumed if f["subject"] in moves],
                     "goal": None, "notes": [], "muscles": []}
            for m in moves:
                entry["notes"].extend(n["note"] for n in c.execute(
                    "SELECT note FROM movement_notes WHERE exercise = ? ORDER BY id", (m,)).fetchall())
                mapping = c.execute("SELECT muscles FROM lift_muscle_map WHERE exercise = ?", (m,)).fetchone()
                if mapping:
                    entry["muscles"].extend(mu for mu in mapping["muscles"].split(",") if mu not in entry["muscles"])
            slots.append(entry)
        split_section = {"day": split_day, "slots": slots}

    goals = []
    by_exercise = {}
    for g in c.execute("SELECT * FROM goals WHERE status = 'active' ORDER BY deadline").fetchall():
        prog = goal_progress(c, dict(g))
        by_exercise[g["exercise"]] = {"id": g["id"], "next_checkpoint": prog["next_checkpoint"]}
        goals.append({"id": g["id"], "exercise": g["exercise"], "target_e1rm": g["target_e1rm"],
                      "deadline": g["deadline"], "next_checkpoint": prog["next_checkpoint"],
                      "on_track": prog["on_track"], "slippage": prog["slippage"],
                      "completed": prog["completed"]})
    if split_section:
        for slot_entry in split_section["slots"]:
            for m in slot_entry["movements"]:
                if m in by_exercise:
                    slot_entry["goal"] = by_exercise[m]
                    break

    rules = rules_with_confirm(c)
    needs_confirm = ([{"type": "rule", "id": r["id"], "subject": r["subject"], "expiry": r["expiry"]}
                      for r in rules if r["needs_confirm"]]
                     + priority_needs_confirm(c))

    autoreg = autoreg_block(c)

    bundle = {
        "today": {"open": w is not None,
                  "workout": {"id": w["id"], "date": w["date"], "status": w["status"]} if w else None,
                  "rest": bool(rest_row), "stale": stale,
                  "last_session": last_session, "gap_days": gap_days, "break": on_break},
        "slot_guess": slot_guess,
        "split": split_section,
        "goals": goals,
        "rules": {"active": rules, "needs_confirm": needs_confirm},
        "volume": volume,
        "ledger": ledger,
        "lifts": lifts,
        "progression": progression,
        "flags": unconsumed,
        "priority": priorities,
        "deload": deload if deload else None,
        "autoreg": autoreg,
        "compaction": compaction_due(),
    }
    if verbose:
        lines = []
        if w:
            flag = "STALE" if stale["is_stale"] else "open"
            lines.append(f"workout {w['id']} {flag} (age {stale['age_days']}d, last set {stale['last_set_created']})")
        elif rest_row:
            lines.append("today is marked rest")
        else:
            lines.append("no open workout")
        lines.append(f"last session {last_session} ({gap_days}d ago)" + (" BREAK, no PR attempts" if on_break else ""))
        lines.append(f"slot guess: {slot_guess['day']} ({slot_guess['basis']}, {slot_guess['confidence']})")
        below = [m for m, v in volume.items() if v["status"] == "below_mev"]
        over = [m for m, v in volume.items() if v["status"] == "above_mrv"]
        lines.append(f"below MEV: {', '.join(below) if below else 'none'}")
        if over:
            lines.append(f"above MRV: {', '.join(over)}")
        if autoreg["permitted"] and (autoreg["miss_streaks"] or autoreg["drop_watch"]):
            parts = ([f"{m['exercise']} {m['streak']}xmiss" for m in autoreg["miss_streaks"]]
                     + [f"{d['exercise']} dropping" for d in autoreg["drop_watch"]])
            lines.append(f"autoreg signals: {', '.join(parts)}")
        if bundle["compaction"]["due"]:
            lines.append("compaction due")
        print("\n".join(lines))
    else:
        print(json.dumps(bundle, indent=2))


def append_memory_state(line):
    try:
        with open(MEMORY_FILE, 'r') as f:
            text = f.read()
    except OSError:
        sys.exit(f"cannot append State line, {MEMORY_FILE} unreadable")
    m = re.search(r"^## State\s*$", text, re.MULTILINE)
    if not m:
        sys.exit("MEMORY.md has no ## State section")
    rest = text[m.end():]
    nxt = re.search(r"^## ", rest, re.MULTILINE)
    insert_at = m.end() + (nxt.start() if nxt else len(rest))
    block = text[m.end():insert_at]
    if line in block:
        return
    if not block.endswith("\n"):
        line = "\n" + line
    text = text[:insert_at] + ("" if block.endswith("\n") else "\n") + line + "\n" + text[insert_at:]
    with open(MEMORY_FILE, 'w') as f:
        f.write(text)


def cmd_progression_set(exercise, verdict, next_target, direction, note="", workout_id=None):
    if verdict not in ("hit", "miss", "hold", "baseline"):
        sys.exit("verdict must be one of hit miss hold baseline (quoting never needed; flags delimit values)")
    if direction not in ("up", "flat", "down"):
        sys.exit("direction must be one of up flat down (quoting never needed; flags delimit values)")
    if not next_target:
        sys.exit("next target is required (e.g. 82.5x5)")
    if not re.match(r"^\d+(\.\d+)?x\d+$", next_target.strip()):
        sys.exit(f"next target must be weight x reps (e.g. 82.5x5), got '{next_target}'")
    c = conn()
    exercise = exercise.strip().lower()
    if workout_id is None:
        w = open_workout(c)
        if not w:
            sys.exit("no open workout (pass --workout <id> to backfill a closed one)")
        workout_id = w["id"]
    else:
        try:
            workout_id = int(workout_id)
        except (TypeError, ValueError):
            sys.exit("no such workout")
        if not c.execute("SELECT id FROM workouts WHERE id = ?", (workout_id,)).fetchone():
            sys.exit("no such workout")
    trained = {r["exercise"] for r in c.execute("SELECT DISTINCT exercise FROM sets WHERE workout_id = ?", (workout_id,)).fetchall()}
    if exercise not in trained:
        sys.exit(f"'{exercise}' has no sets in workout {workout_id}, nothing to judge")
    created = datetime.now().isoformat(timespec="seconds")
    c.execute(
        "INSERT INTO progression (workout_id, exercise, verdict, next_target, direction, note, created) "
        "VALUES (?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT (workout_id, exercise) DO UPDATE SET verdict = excluded.verdict, next_target = excluded.next_target, "
        "direction = excluded.direction, note = excluded.note, created = excluded.created",
        (workout_id, exercise, verdict, next_target, direction, note, created))
    c.commit()
    print(json.dumps({"progression": exercise, "workout_id": workout_id, "verdict": verdict,
                      "next": next_target, "direction": direction}))


def cmd_progression_show(exercise=None):
    c = conn()
    if exercise:
        rows = c.execute("SELECT * FROM progression WHERE exercise = ? ORDER BY workout_id DESC", (exercise.strip().lower(),)).fetchall()
    else:
        rows = c.execute(
            "SELECT p.* FROM progression p JOIN (SELECT exercise, MAX(workout_id) m FROM progression GROUP BY exercise) "
            "l ON l.exercise = p.exercise AND l.m = p.workout_id ORDER BY p.exercise").fetchall()
    print(json.dumps([dict(r) for r in rows], indent=2))


def cmd_flag_add(subject, reason):
    if not reason:
        sys.exit("flag reason is required")
    c = conn()
    created = datetime.now().isoformat(timespec="seconds")
    cur = c.execute("INSERT INTO flags (subject, reason, created, consumed_at) VALUES (?, ?, ?, NULL)",
                    (subject.strip().lower(), reason, created))
    c.commit()
    print(json.dumps({"flag_id": cur.lastrowid, "subject": subject.strip().lower()}))


def cmd_flag_list():
    c = conn()
    rows = c.execute("SELECT * FROM flags WHERE consumed_at IS NULL ORDER BY id").fetchall()
    print(json.dumps([dict(r) for r in rows], indent=2))


def cmd_flag_consume(flag_id):
    c = conn()
    try:
        flag_id = int(flag_id)
    except (TypeError, ValueError):
        sys.exit("no such flag")
    cur = c.execute("UPDATE flags SET consumed_at = ? WHERE id = ? AND consumed_at IS NULL",
                    (datetime.now().isoformat(timespec="seconds"), flag_id))
    if cur.rowcount == 0:
        sys.exit("no such unconsumed flag (see flag list)")
    c.commit()
    print(json.dumps({"consumed": flag_id}))


def consume_session_flags(c, workout_id):
    trained = {r["exercise"] for r in c.execute(
        "SELECT DISTINCT exercise FROM sets WHERE workout_id = ?", (workout_id,)).fetchall()}
    muscles = set()
    for ex in trained:
        mapping = c.execute("SELECT muscles FROM lift_muscle_map WHERE exercise = ?", (ex,)).fetchone()
        if mapping:
            muscles.update(mapping["muscles"].split(","))
    subjects = trained | muscles
    if not subjects:
        return 0
    cur = c.execute("UPDATE flags SET consumed_at = ? WHERE consumed_at IS NULL AND subject IN (%s)" % placeholders(len(subjects)),
                    [datetime.now().isoformat(timespec="seconds")] + sorted(subjects))
    return cur.rowcount


def cmd_priority_set(muscle, tier, until=None):
    muscle = muscle.strip().lower()
    if tier not in ("priority", "maintain", "deprioritize"):
        sys.exit("tier must be one of priority maintain deprioritize (quoting never needed; tier is the last word)")
    constants = load_constants()
    known = set(constants["muscles"]) | set(constants.get("untracked", []))
    hit = canon_muscle_name(muscle, known)
    if hit is not None:
        muscle = hit
    if muscle not in constants["muscles"]:
        sys.exit(f"'{muscle}' is not a tracked muscle (untracked: {', '.join(constants.get('untracked', []))})")
    if until is not None:
        try:
            until = date.fromisoformat(until).isoformat()
        except ValueError:
            sys.exit("until must be YYYY-MM-DD")
    c = conn()
    c.execute("INSERT INTO priority (muscle, tier, since, until) VALUES (?, ?, ?, ?) "
              "ON CONFLICT (muscle) DO UPDATE SET tier = excluded.tier, since = excluded.since, until = excluded.until",
              (muscle, tier, date.today().isoformat(), until))
    c.commit()
    print(json.dumps({"priority": muscle, "tier": tier, "until": until}))


def cmd_priority_clear(muscle):
    c = conn()
    cur = c.execute("DELETE FROM priority WHERE muscle = ?", (muscle.strip().lower(),))
    c.commit()
    print(json.dumps({"cleared": muscle.strip().lower(), "rows": cur.rowcount}))


def cmd_priority_list():
    c = conn()
    rows = c.execute("SELECT * FROM priority ORDER BY muscle").fetchall()
    print(json.dumps([dict(r) for r in rows], indent=2))


def cmd_deload_set(scope, subject):
    if scope not in ("lift", "slot"):
        sys.exit("scope must be lift or slot (quote multi-word names)")
    if not subject:
        sys.exit("deload subject is required")
    c = conn()
    today = date.today().isoformat()
    if scope == "lift":
        subject = subject.strip().lower()
        if not c.execute("SELECT exercise FROM lift_muscle_map WHERE exercise = ?", (subject,)).fetchone():
            sys.exit(f"'{subject}' has no mapping (run map set first)")
    else:
        match = next((d for d in split_day_order("active", c=c) if d.lower() == subject.strip().lower()), None)
        if not match:
            sys.exit(f"no active split day '{subject.strip()}' (see split show)")
        subject = match
    existing = c.execute("SELECT id FROM deload_state WHERE scope = ? AND subject = ? AND cleared_on IS NULL",
                         (scope, subject)).fetchone()
    if existing:
        print(json.dumps({"deload_id": existing["id"], "scope": scope, "subject": subject, "reused": True}))
        return
    cur = c.execute("INSERT INTO deload_state (scope, subject, set_on, cleared_on) VALUES (?, ?, ?, NULL)",
                    (scope, subject, today))
    c.commit()
    print(json.dumps({"deload_id": cur.lastrowid, "scope": scope, "subject": subject}))


def cmd_deload_clear():
    # Prose first: if the State write fails, the DB is untouched and a retry
    # is safe. A markdown edit must never break a DB command halfway.
    c = conn()
    rows = c.execute("SELECT scope, subject FROM deload_state WHERE cleared_on IS NULL ORDER BY id").fetchall()
    today = date.today().isoformat()
    for r in rows:
        append_memory_state(f"{today}: deload completed for {r['scope']} {r['subject']}")
    c.execute("UPDATE deload_state SET cleared_on = ? WHERE cleared_on IS NULL", (today,))
    c.commit()
    print(json.dumps({"cleared": len(rows)}))


def active_deloads(c):
    return c.execute("SELECT * FROM deload_state WHERE cleared_on IS NULL ORDER BY id").fetchall()


def deload_covers(deloads, exercise, day_moves):
    """True if an active deload row covers this exercise (lift scope: exact name)."""
    lowered = {k.lower(): v for k, v in day_moves.items()}
    for d in deloads:
        if d["scope"] == "lift" and d["subject"] == exercise:
            return True
        if d["scope"] == "slot" and exercise in lowered.get(d["subject"].lower(), []):
            return True
    return False


def end_gate_items(c, w, note):
    """Preconditions for closing a workout. Returns list of {item, fix}."""
    outstanding = []
    missing = c.execute("""
        SELECT s.id, s.exercise FROM sets s
        LEFT JOIN set_muscles sm ON sm.set_id = s.id
        WHERE s.workout_id = ? AND sm.muscle IS NULL
    """, (w["id"],)).fetchall()
    for m in missing:
        outstanding.append({"item": f"set {m['id']} ({m['exercise']}) has no muscles",
                            "fix": f"log.py map set \"{m['exercise']}\" <a,b>", "hard": True})
    trained = [r["exercise"] for r in c.execute(
        "SELECT DISTINCT exercise FROM sets WHERE workout_id = ?", (w["id"],)).fetchall()]
    judged = {r["exercise"] for r in c.execute(
        "SELECT DISTINCT exercise FROM progression WHERE workout_id = ?", (w["id"],)).fetchall()}
    for ex in sorted(set(trained) - judged):
        outstanding.append({"item": f"missing progression: {ex}",
                            "fix": f"log.py progression set \"{ex}\" --verdict <hit|miss|hold|baseline> --next <target> --direction <up|flat|down>"})
    known = split_all_movements("active", c=c)
    unreconciled = sorted(set(trained) - known)
    if unreconciled:
        day = best_split_day(trained, c=c) or (split_day_order("active", c=c)[:1] or ["Upper A"])[0]
        performed = [r["exercise"] for r in c.execute(
            "SELECT exercise, MIN(id) m FROM sets WHERE workout_id = ? GROUP BY exercise ORDER BY m",
            (w["id"],)).fetchall()]
        anchor = next((ex for ex in reversed(performed) if ex in day_movements(day, c=c)), None)
        after = f" --after \"{anchor}\"" if anchor else ""
        for ex in unreconciled:
            outstanding.append({"item": f"unreconciled slot: {ex} (not in any active split day)",
                                "fix": f"log.py split reconcile --day \"{day}\"{after}"})
    deloads = active_deloads(c)
    if deloads:
        day_moves = parse_active_split_days(c)
        covered = [ex for ex in trained if deload_covers(deloads, ex, day_moves)]
        if covered:
            combined = ((w["notes"] + " " + note) if w["notes"] else note).lower()
            if "deload" not in combined:
                outstanding.append({"item": f"deload session covers {', '.join(sorted(set(covered)))} but the note has no 'deload'",
                                    "fix": "log.py end \"<note> deload\""})
    return outstanding


def cmd_check(note=""):
    c = conn()
    w = open_workout(c)
    if not w:
        sys.exit("no open workout")
    outstanding = end_gate_items(c, w, note)
    if outstanding:
        print(f"workout {w['id']} not ready to close, {len(outstanding)} items outstanding:")
        for o in outstanding:
            print(f"  {o['item']}\n    {o['fix']}")
        sys.exit(1)
    print(json.dumps({"ready": w["id"]}))


def split_all_movements(variant="active", c=None):
    moves = set()
    for r in read_split(variant, c=c):
        moves.update(parse_movements(r["movements"]))
    return moves


def split_day_prefix(toks, c=None):
    """Split leading tokens into (day, rest) using the longest known day name.

    Lets multi-word days go unquoted; unknown days fall back to first token
    so the command itself reports the problem.
    """
    days = split_day_order("active", c=c) + split_day_order("baseline", c=c)
    for n in range(min(3, len(toks)), 0, -1):
        candidate = " ".join(toks[:n])
        match = next((d for d in days if d.lower() == candidate.lower()), None)
        if match:
            return match, " ".join(toks[n:])
    return (toks[0], " ".join(toks[1:])) if toks else (None, None)


def day_movements(day, variant="active", c=None):
    moves = []
    for r in read_split(variant, day, c=c):
        moves.extend(parse_movements(r["movements"]))
    return moves


def best_split_day(trained, c=None):
    trained = set(trained)
    best_day, best_score = None, 0
    for day in split_day_order("active", c=c):
        score = len(trained & set(day_movements(day, c=c)))
        if score > best_score:
            best_day, best_score = day, score
    return best_day


def cmd_split_show(day=None, variant="active"):
    c = conn()
    if variant not in ("active", "baseline"):
        sys.exit("variant must be active or baseline")
    if day and not read_split(variant, day, c=c):
        sys.exit(f"no {variant} split day '{day}'")
    lines = []
    for d in ([day] if day else split_day_order(variant, c=c)):
        lines.append(f"### {d}")
        for r in read_split(variant, d, c=c):
            lines.append(f"{r['slot']}. {r['movements']} x{r['sets']}")
    print("\n".join(lines))


def cmd_split_set(day, slot, movements, sets, variant="active"):
    c = conn()
    if variant not in ("active", "baseline"):
        sys.exit("variant must be active or baseline (quote multi-word day names)")
    try:
        slot = int(slot)
        sets = int(sets)
    except (TypeError, ValueError):
        sys.exit("slot and sets must be integers")
    if sets <= 0:
        sys.exit("sets must be positive")
    movements = movements.strip().lower()
    if not movements:
        sys.exit("movements cannot be empty")
    for move in parse_movements(movements):
        if not c.execute("SELECT exercise FROM lift_muscle_map WHERE exercise = ?", (move,)).fetchone():
            sys.exit(f"'{move}' has no mapping (run map set first), split unchanged")
    before = c.execute("SELECT movements FROM splits WHERE variant = ? AND day = ? AND slot = ?",
                       (variant, day, slot)).fetchone()
    c.execute("INSERT INTO splits (variant, day, slot, movements, sets) VALUES (?, ?, ?, ?, ?) "
              "ON CONFLICT (variant, day, slot) DO UPDATE SET movements = excluded.movements, sets = excluded.sets",
              (variant, day, slot, movements, sets))
    c.commit()
    out = {"split": variant, "day": day, "slot": slot, "movements": movements, "sets": sets}
    if variant == "active":
        # MEV floor warns, never blocks: a human reviews split set first.
        # Scoped to muscles in the before or after movements only, so fresh
        # programs do not cry wolf about unrelated gaps.
        affected = muscles_for_movements(c, movements)
        if before:
            affected |= muscles_for_movements(c, before["movements"])
        warnings = mev_floor_warnings(programmed_weekly_volume(c), affected)
        if warnings:
            out["warnings"] = warnings
    print(json.dumps(out))


def cmd_split_move(day, exercise, to_slot):
    c = conn()
    exercise = exercise.strip().lower()
    try:
        to_slot = int(to_slot)
    except (TypeError, ValueError):
        sys.exit("slot must be an integer")
    rows = read_split("active", day, c=c)
    if not rows:
        sys.exit(f"no active split day '{day}'")
    origin = next((r for r in rows if exercise in parse_movements(r["movements"])), None)
    if not origin:
        sys.exit(f"'{exercise}' is not in {day}")
    if len(parse_movements(origin["movements"])) > 1:
        sys.exit(f"'{exercise}' shares slot {origin['slot']} ({origin['movements']}); "
                 f"use split set to rearrange interchangeable pairs explicitly")
    carry_sets = origin["sets"]
    remaining = []
    for r in rows:
        kept = [m for m in (m.strip() for m in r["movements"].split("/")) if m.lower() != exercise]
        if kept:
            remaining.append({"movements": " / ".join(kept), "sets": r["sets"]})
    to_slot = max(1, min(to_slot, len(remaining) + 1))
    remaining.insert(to_slot - 1, {"movements": exercise, "sets": carry_sets})
    c.execute("DELETE FROM splits WHERE variant = 'active' AND day = ?", (day,))
    for i, r in enumerate(remaining, 1):
        c.execute("INSERT INTO splits (variant, day, slot, movements, sets) VALUES ('active', ?, ?, ?, ?)",
                  (day, i, r["movements"], r["sets"]))
    c.commit()
    print(json.dumps({"moved": exercise, "day": day, "to_slot": to_slot}))


def cmd_split_reconcile(day, after=None):
    c = conn()
    if not read_split("active", day, c=c):
        sys.exit(f"no active split day '{day}'")
    w = open_workout(c)
    if not w:
        w = c.execute("SELECT * FROM workouts WHERE status = 'done' ORDER BY date DESC, id DESC LIMIT 1").fetchone()
    if not w:
        sys.exit("no workout to reconcile from")
    trained = [r["exercise"] for r in c.execute(
        "SELECT exercise, MIN(id) m FROM sets WHERE workout_id = ? GROUP BY exercise ORDER BY m",
        (w["id"],)).fetchall()]
    known = split_all_movements("active", c=c)
    new = [ex for ex in trained if ex not in known]
    if not new:
        print(json.dumps({"reconciled": day, "added": []}))
        return
    rows = read_split("active", day, c=c)
    if after:
        anchor = next((r for r in rows if after.strip().lower() in parse_movements(r["movements"])), None)
        if not anchor:
            sys.exit(f"'{after}' is not in {day}")
        insert_at = anchor["slot"] + 1
    else:
        insert_at = len(rows) + 1
    new_slot_sets = load_constants()["thresholds"].get("default_new_slot_sets", 2)
    for i, ex in enumerate(new):
        c.execute("UPDATE splits SET slot = slot + 1 WHERE variant = 'active' AND day = ? AND slot >= ?",
                  (day, insert_at + i))
        c.execute("INSERT INTO splits (variant, day, slot, movements, sets) VALUES ('active', ?, ?, ?, ?)",
                  (day, insert_at + i, ex, new_slot_sets))
    c.commit()
    print(json.dumps({"reconciled": day, "added": new}))


def cmd_split_diff():
    c = conn()
    active = {(r["day"], r["slot"]): (r["movements"], r["sets"]) for r in read_split("active", c=c)}
    baseline = {(r["day"], r["slot"]): (r["movements"], r["sets"]) for r in read_split("baseline", c=c)}
    lines = []
    for key in sorted(set(active) | set(baseline)):
        a, b = active.get(key), baseline.get(key)
        if a != b:
            lines.append(f"{key[0]} #{key[1]}: baseline {b} vs active {a}")
    print("\n".join(lines) if lines else "active matches baseline")


def cmd_split_revert(day=None):
    c = conn()
    if day:
        base = read_split("baseline", day, c=c)
        if not base:
            sys.exit(f"no baseline split day '{day}'")
        c.execute("DELETE FROM splits WHERE variant = 'active' AND day = ?", (day,))
        for r in base:
            c.execute("INSERT INTO splits (variant, day, slot, movements, sets) VALUES ('active', ?, ?, ?, ?)",
                      (day, r["slot"], r["movements"], r["sets"]))
    else:
        c.execute("DELETE FROM splits WHERE variant = 'active'")
        for r in read_split("baseline", c=c):
            c.execute("INSERT INTO splits (variant, day, slot, movements, sets) VALUES ('active', ?, ?, ?, ?)",
                      (r["day"], r["slot"], r["movements"], r["sets"]))
    c.commit()
    print(json.dumps({"reverted": day or "all"}))


def cmd_autoreg_apply(day, slot, to_movements, to_sets, evidence, from_movements=None):
    """Single entry point for every autonomous program edit.

    Refuses, in order: no permission rule, missing slot, --from mismatch,
    unmapped movements, held slot, below-MEV result.
    """
    from datetime import timedelta
    c = conn()
    today = date.today().isoformat()
    if not autoreg_permitted(c):
        sys.exit("autoreg has no standing permission (rule add <text> --subject autoreg)")
    try:
        slot = int(slot)
    except (TypeError, ValueError):
        sys.exit(f"no active split slot '{slot}' on '{day}'")
    match = next((d for d in split_day_order("active", c=c) if d.lower() == (day or "").strip().lower()), None)
    if match is None:
        sys.exit(f"no active split slot '{slot}' on '{day}'")
    day = match
    cur = next((r for r in read_split("active", day, c=c) if r["slot"] == slot), None)
    if cur is None:
        sys.exit(f"no active split slot '{slot}' on '{day}'")
    if from_movements is not None and parse_movements(from_movements) != parse_movements(cur["movements"]):
        sys.exit(f"--from mismatch: slot {slot} on '{day}' holds '{cur['movements']}', "
                 f"not '{from_movements.strip().lower()}' (refusing to clobber a concurrent edit)")
    to_movements = (to_movements or "").strip().lower()
    if not to_movements:
        sys.exit("movements cannot be empty")
    try:
        to_sets = int(to_sets)
    except (TypeError, ValueError):
        sys.exit("sets must be an integer")
    if to_sets <= 0:
        sys.exit("sets must be positive")
    if not (evidence or "").strip():
        sys.exit("evidence is required (quote the reason)")
    for move in parse_movements(to_movements):
        if not c.execute("SELECT exercise FROM lift_muscle_map WHERE exercise = ?", (move,)).fetchone():
            sys.exit(f"'{move}' has no mapping (run map set first), split unchanged")
    held = c.execute("SELECT * FROM autoreg_holds WHERE day = ? AND movements = ? AND hold_until >= ?",
                     (day, cur["movements"], today)).fetchone()
    if held:
        sys.exit(f"slot {slot} on '{day}' is held until {held['hold_until']}, revert first")
    simulated = [dict(r) for r in read_split("active", c=c)]
    for r in simulated:
        if r["day"] == day and r["slot"] == slot:
            r["movements"], r["sets"] = to_movements, to_sets
            break
    affected = muscles_for_movements(c, cur["movements"]) | muscles_for_movements(c, to_movements)
    below = mev_floor_warnings(programmed_weekly_volume(c, simulated), affected)
    if below:
        sys.exit("below MEV, refusing: " + "; ".join(below))
    if parse_movements(to_movements) != parse_movements(cur["movements"]):
        action = "swap"
    elif to_sets < cur["sets"]:
        action = "trim"
    else:
        action = "add"
    c.execute("INSERT INTO splits (variant, day, slot, movements, sets) VALUES ('active', ?, ?, ?, ?) "
              "ON CONFLICT (variant, day, slot) DO UPDATE SET movements = excluded.movements, sets = excluded.sets",
              (day, slot, to_movements, to_sets))
    hold_until = None
    if action in ("trim", "swap"):
        hold_until = (date.today() + timedelta(days=8)).isoformat()
        c.execute("INSERT INTO autoreg_holds (day, movements, action, set_on, hold_until, reason) "
                  "VALUES (?, ?, ?, ?, ?, ?)",
                  (day, to_movements, action, today, hold_until, evidence.strip()))
    cur_change = c.execute(
        "INSERT INTO autoreg_changes (date, action, day, slot, before_movements, before_sets, "
        "after_movements, after_sets, evidence, reverted_on) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)",
        (today, action, day, slot, cur["movements"], cur["sets"], to_movements, to_sets, evidence.strip()))
    c.commit()
    print(json.dumps({"autoreg": action, "day": day, "slot": slot,
                      "before": {"movements": cur["movements"], "sets": cur["sets"]},
                      "after": {"movements": to_movements, "sets": to_sets},
                      "hold_until": hold_until, "change_id": cur_change.lastrowid,
                      "evidence": evidence.strip()}))


def cmd_autoreg_log():
    c = conn()
    rows = c.execute("SELECT * FROM autoreg_changes ORDER BY id").fetchall()
    print(json.dumps([{**dict(r), "reverted": r["reverted_on"] is not None} for r in rows], indent=2))


def cmd_autoreg_revert(change_id):
    """Restore before state exactly; clears matching unexpired holds."""
    c = conn()
    today = date.today().isoformat()
    try:
        change_id = int(change_id)
    except (TypeError, ValueError):
        sys.exit("no such autoreg change")
    row = c.execute("SELECT * FROM autoreg_changes WHERE id = ?", (change_id,)).fetchone()
    if not row:
        sys.exit("no such autoreg change")
    if row["reverted_on"] is not None:
        sys.exit(f"change {change_id} already reverted on {row['reverted_on']}")
    cur = next((r for r in read_split("active", row["day"], c=c) if r["slot"] == row["slot"]), None)
    if (cur is None or parse_movements(cur["movements"]) != parse_movements(row["after_movements"])
            or cur["sets"] != row["after_sets"]):
        sys.exit(f"slot {row['slot']} on '{row['day']}' no longer matches the recorded after-state, reconcile manually")
    c.execute("INSERT INTO splits (variant, day, slot, movements, sets) VALUES ('active', ?, ?, ?, ?) "
              "ON CONFLICT (variant, day, slot) DO UPDATE SET movements = excluded.movements, sets = excluded.sets",
              (row["day"], row["slot"], row["before_movements"], row["before_sets"]))
    c.execute("UPDATE autoreg_changes SET reverted_on = ? WHERE id = ?", (today, change_id))
    cleared = c.execute("DELETE FROM autoreg_holds WHERE day = ? AND movements = ? AND hold_until >= ?",
                        (row["day"], row["after_movements"], today)).rowcount
    c.commit()
    print(json.dumps({"reverted": change_id, "day": row["day"], "slot": row["slot"],
                      "restored": {"movements": row["before_movements"], "sets": row["before_sets"]},
                      "holds_cleared": cleared}))


def cmd_map_show(exercise=None):
    c = conn()
    if exercise:
        exercise = exercise.strip().lower()
        mapping = c.execute("SELECT * FROM lift_muscle_map WHERE exercise = ?", (exercise,)).fetchone()
        if not mapping:
            sys.exit(f"'{exercise}' has no mapping (run map set first)")
        notes = [r["note"] for r in c.execute(
            "SELECT note FROM movement_notes WHERE exercise = ? ORDER BY id", (exercise,)).fetchall()]
        print(json.dumps({"exercise": exercise, "muscles": mapping["muscles"],
                          "is_bodyweight_only": mapping["is_bodyweight_only"], "notes": notes}, indent=2))
        return
    rows = c.execute("SELECT exercise, muscles FROM lift_muscle_map ORDER BY exercise").fetchall()
    print(json.dumps([dict(r) for r in rows], indent=2))


def cmd_map_note(exercise, text):
    if not text:
        sys.exit("note text is required")
    c = conn()
    created = datetime.now().isoformat(timespec="seconds")
    cur = c.execute("INSERT INTO movement_notes (exercise, note, created) VALUES (?, ?, ?)",
                    (exercise.strip().lower(), text, created))
    c.commit()
    print(json.dumps({"note_id": cur.lastrowid, "exercise": exercise.strip().lower()}))


def cmd_rule_add(text, subject, expires=None):
    if not text:
        sys.exit("rule text is required")
    if not subject:
        sys.exit("rule subject is required")
    if expires is not None:
        try:
            expires = date.fromisoformat(expires).isoformat()
        except ValueError:
            sys.exit("expiry must be YYYY-MM-DD")
    c = conn()
    today = date.today().isoformat()
    created = datetime.now().isoformat(timespec="seconds")
    cur = c.execute("INSERT INTO rules (subject, text, start_date, expiry, status, created) VALUES (?, ?, ?, ?, 'active', ?)",
                    (subject.strip().lower(), text, today, expires, created))
    c.commit()
    print(json.dumps({"rule_id": cur.lastrowid, "subject": subject.strip().lower(), "expiry": expires}))


def rule_status_rows(c):
    return [dict(r) for r in c.execute("SELECT * FROM rules WHERE status = 'active' ORDER BY id").fetchall()]


def rules_with_confirm(c):
    today = date.today()
    out = []
    for r in rule_status_rows(c):
        needs = bool(r["expiry"] and (date.fromisoformat(r["expiry"]) - today).days <= 7)
        entry = dict(r)
        entry["needs_confirm"] = needs
        out.append(entry)
    return out


def cmd_rule_list(expiring_within=None):
    c = conn()
    out = rules_with_confirm(c)
    today = date.today()
    if expiring_within is not None:
        try:
            window = int(expiring_within)
        except (TypeError, ValueError):
            sys.exit("expiring-within must be an integer")
        out = [r for r in out if r["expiry"] and (date.fromisoformat(r["expiry"]) - today).days <= window]
    print(json.dumps(out, indent=2))


def cmd_rule_confirm(rule_id, extend=None, archive=False):
    c = conn()
    try:
        rule_id = int(rule_id)
    except (TypeError, ValueError):
        sys.exit("no such rule")
    row = c.execute("SELECT * FROM rules WHERE id = ?", (rule_id,)).fetchone()
    if not row:
        sys.exit("no such rule")
    if archive:
        c.execute("UPDATE rules SET status = 'archived' WHERE id = ?", (rule_id,))
    elif extend:
        try:
            expiry = date.fromisoformat(extend).isoformat()
        except ValueError:
            sys.exit("extend date must be YYYY-MM-DD")
        c.execute("UPDATE rules SET expiry = ?, status = 'active' WHERE id = ?", (expiry, rule_id))
    else:
        sys.exit("rule confirm needs --extend <date> or --archive")
    c.commit()
    print(json.dumps({"rule_id": rule_id, "archived": archive, "expiry": extend if not archive else None}))


def goal_exercise_days(c, exercise):
    return [day for day in split_day_order("active", c=c) if exercise in day_movements(day, c=c)]


def sessions_possible_before(c, exercise, deadline):
    days_left = (date.fromisoformat(deadline) - date.today()).days
    if days_left < 0:
        return 0
    # One rotation slot counts as one calendar day (rest entries included),
    # so cycle length already prices in rest days.
    rotation = parse_rotation(c)
    cycle_days = len(rotation) if rotation else 7
    per_cycle = len(goal_exercise_days(c, exercise))
    return int(days_left / cycle_days * per_cycle + 0.5)


def build_checkpoints(start, target, n):
    # Session 1 is the already-logged baseline, so it checkpoints at start.
    if n <= 1:
        return [round(target, 1)]
    return [round(start + (target - start) * i / (n - 1), 1) for i in range(n)]


def top_e1rm_by_date(c, exercise):
    sql = ("SELECT w.date as day, MAX(CASE WHEN s.reps = 1 THEN s.weight ELSE s.weight * (1 + s.reps / 30.0) END) as e1rm, "
           "GROUP_CONCAT(DISTINCT w.notes) as notes, GROUP_CONCAT(DISTINCT s.note) as set_notes, "
           "MAX(s.created) as max_created FROM sets s JOIN workouts w ON w.id = s.workout_id "
           "WHERE s.exercise = ? AND w.status = 'done' GROUP BY day ORDER BY day")
    return [(r["day"], r["e1rm"], " ".join(n for n in (r["notes"], r["set_notes"]) if n),
             r["max_created"]) for r in c.execute(sql, (exercise,)).fetchall()]


def goal_sessions(c, goal):
    """Post-goal training dates with the last pre-goal date as session-1 anchor.

    Same-day rows count as post-goal only if their sets were logged after the
    goal was created (set created timestamps vs goal created timestamp).
    """
    all_sessions = top_e1rm_by_date(c, goal["exercise"])
    created_day = goal["created"][:10]
    prior = [s for s in all_sessions if s[0] < created_day
             or (s[0] == created_day and (s[3] or "") < goal["created"])]
    current = [s for s in all_sessions if s not in prior and s[0] >= created_day]
    return (prior[-1:] + current) if prior or current else []


def goal_progress(c, goal):
    checkpoints = [r["target_e1rm"] for r in c.execute(
        "SELECT target_e1rm FROM goal_checkpoints WHERE goal_id = ? ORDER BY session_no", (goal["id"],)).fetchall()]
    sessions = goal_sessions(c, goal)
    completed = min(len(sessions), len(checkpoints))
    divergence = load_constants()["thresholds"].get("goal_divergence_pct", 5)
    consecutive_misses = 0
    for i in range(completed):
        _, actual, notes, _ = sessions[i]
        if "deload" in (notes or "").lower():
            consecutive_misses = 0
            continue
        # One-sided: only shortfall misses. Overperformance is signal, not failure.
        if (checkpoints[i] - actual) / checkpoints[i] * 100 > divergence:
            consecutive_misses += 1
        else:
            consecutive_misses = 0
    remaining = len(checkpoints) - completed
    slippage = remaining > sessions_possible_before(c, goal["exercise"], goal["deadline"])
    return {"checkpoints": checkpoints, "completed": completed,
            "actuals": [{"date": d, "e1rm": round(e, 1)} for d, e, _, _ in sessions[:completed]],
            "consecutive_misses": consecutive_misses, "on_track": consecutive_misses < 2,
            "remaining": remaining, "slippage": slippage,
            "next_checkpoint": checkpoints[completed] if completed < len(checkpoints) else None}


def cmd_goal_add(exercise, target_e1rm, deadline, target_desc="", start_e1rm=None):
    c = conn()
    exercise = (exercise or "").strip().lower()
    if not exercise:
        sys.exit("goal exercise is required")
    if not c.execute("SELECT exercise FROM lift_muscle_map WHERE exercise = ?", (exercise,)).fetchone():
        sys.exit(f"'{exercise}' has no mapping (run map set first)")
    try:
        target_e1rm = float(target_e1rm)
    except (TypeError, ValueError):
        sys.exit("target e1RM must be a number")
    if target_e1rm <= 0:
        sys.exit("target e1RM must be positive")
    try:
        deadline = date.fromisoformat(deadline).isoformat()
    except ValueError:
        sys.exit("deadline must be YYYY-MM-DD")
    if date.fromisoformat(deadline) <= date.today():
        sys.exit("deadline must be in the future")
    if start_e1rm is None:
        top = c.execute(
            "SELECT CASE WHEN reps = 1 THEN weight ELSE weight * (1 + reps / 30.0) END AS e1rm "
            "FROM sets WHERE exercise = ? ORDER BY e1rm DESC LIMIT 1", (exercise,)).fetchone()
        if not top:
            sys.exit(f"no logged sets for '{exercise}', pass --from <e1rm> to seed the trajectory")
        start_e1rm = top["e1rm"]
    else:
        try:
            start_e1rm = float(start_e1rm)
        except (TypeError, ValueError):
            sys.exit("start e1RM must be a number")
    existing = c.execute("SELECT id FROM goals WHERE exercise = ? AND status = 'active'",
                         (exercise,)).fetchone()
    if existing:
        sys.exit(f"goal {existing['id']} already covers '{exercise}' (rewrite or drop it first)")
    n = sessions_possible_before(c, exercise, deadline)
    if n < 1:
        sys.exit(f"no '{exercise}' sessions fit before {deadline} at the current split frequency")
    now = datetime.now().isoformat(timespec="seconds")
    cur = c.execute("INSERT INTO goals (exercise, target_e1rm, target_desc, deadline, status, created) "
                    "VALUES (?, ?, ?, ?, 'active', ?)",
                    (exercise, target_e1rm, target_desc, deadline, now))
    gid = cur.lastrowid
    for i, cp in enumerate(build_checkpoints(start_e1rm, target_e1rm, n), 1):
        c.execute("INSERT INTO goal_checkpoints (goal_id, session_no, target_e1rm) VALUES (?, ?, ?)", (gid, i, cp))
    c.commit()
    print(json.dumps({"goal_id": gid, "exercise": exercise, "sessions": n,
                      "start_e1rm": round(start_e1rm, 1), "target_e1rm": target_e1rm, "deadline": deadline}))


def cmd_goal_show(goal_id=None):
    c = conn()
    if goal_id is not None:
        try:
            goal_id = int(goal_id)
        except (TypeError, ValueError):
            sys.exit("no such goal")
        goals = [dict(r) for r in c.execute("SELECT * FROM goals WHERE id = ?", (goal_id,)).fetchall()]
        if not goals:
            sys.exit("no such goal")
    else:
        goals = [dict(r) for r in c.execute("SELECT * FROM goals WHERE status = 'active' ORDER BY deadline").fetchall()]
    out = []
    for g in goals:
        entry = dict(g)
        entry.update(goal_progress(c, g))
        out.append(entry)
    print(json.dumps(out, indent=2))


def cmd_goal_rewrite(goal_id):
    c = conn()
    try:
        goal_id = int(goal_id)
    except (TypeError, ValueError):
        sys.exit("no such goal")
    goal = c.execute("SELECT * FROM goals WHERE id = ?", (goal_id,)).fetchone()
    if not goal:
        sys.exit("no such goal")
    goal = dict(goal)
    prog = goal_progress(c, goal)
    if prog["remaining"] <= 0:
        sys.exit("goal trajectory is complete, nothing to rewrite")
    sessions = goal_sessions(c, goal)
    anchor = sessions[prog["completed"] - 1][1] if prog["completed"] > 0 else prog["checkpoints"][0]
    fresh = build_checkpoints(anchor, goal["target_e1rm"], prog["remaining"])
    for i, cp in enumerate(fresh, prog["completed"] + 1):
        c.execute("UPDATE goal_checkpoints SET target_e1rm = ? WHERE goal_id = ? AND session_no = ?",
                  (cp, goal_id, i))
    c.commit()
    print(json.dumps({"goal_id": goal_id, "rewritten_from_session": prog["completed"] + 1, "checkpoints": fresh}))


def cmd_goal_drop(goal_id):
    c = conn()
    try:
        goal_id = int(goal_id)
    except (TypeError, ValueError):
        sys.exit("no such goal")
    cur = c.execute("UPDATE goals SET status = 'dropped' WHERE id = ?", (goal_id,))
    if cur.rowcount == 0:
        sys.exit("no such goal")
    c.commit()
    print(json.dumps({"dropped": goal_id}))


def cmd_dump():
    c = conn()
    sql_file = os.path.join(os.path.dirname(os.path.abspath(DB)), "workouts.sql")
    with open(sql_file, 'w') as f:
        for line in c.iterdump():
            f.write(f"{line}\n")
    print(json.dumps({"dumped": sql_file}))


def cmd_doctor():
    """Structural check: constants, DB, and dashboard agree. Non-correlated."""
    problems = []
    try:
        constants = load_constants()
    except SystemExit as e:
        print(json.dumps({"ok": False, "problems": [{"check": "constants_parse", "fix": str(e)}]}))
        sys.exit(1)
    root = os.path.dirname(os.path.abspath(__file__))
    charts = os.path.join(root, "dashboard", "src", "charts.ts")
    try:
        with open(charts) as f:
            charts_text = f.read()
        if "constants.json" not in charts_text:
            problems.append({"check": "dashboard_palette",
                             "fix": "dashboard/src/charts.ts must derive MC/GROUPS from ../../constants.json"})
    except OSError:
        problems.append({"check": "dashboard_palette", "fix": f"{charts} unreadable"})
    c = conn()
    for check, exercises in (
            ("sets_mapping", [r["exercise"] for r in c.execute(
                "SELECT DISTINCT exercise FROM sets WHERE exercise NOT IN (SELECT exercise FROM lift_muscle_map)").fetchall()]),
            ("split_mapping", sorted({m for d in split_day_order("active", c=c) for m in day_movements(d, c=c)
                                      if not c.execute("SELECT exercise FROM lift_muscle_map WHERE exercise = ?",
                                                       (m,)).fetchone()}))):
        for ex in exercises:
            problems.append({"check": check, "fix": f"map set \"{ex}\" <muscles>"})
    known_muscles = set(constants["muscles"]) | set(constants.get("untracked", []))
    stray = [r["muscle"] for r in c.execute("SELECT DISTINCT muscle FROM set_muscles").fetchall()
             if r["muscle"] not in known_muscles]
    for muscle in stray:
        problems.append({"check": "muscle_coverage",
                         "fix": f"logged muscle '{muscle}' is neither tracked nor untracked in constants.json"})
    rotation_row = c.execute("SELECT value FROM meta WHERE key = 'rotation'").fetchone()
    try:
        rotation = json.loads(rotation_row["value"]) if rotation_row else None
    except ValueError:
        rotation = None
    if not isinstance(rotation, list) or not rotation or not all(isinstance(d, str) for d in rotation):
        problems.append({"check": "rotation",
                         "fix": "meta.rotation must be a non-empty JSON array of day names (see meta show)"})
    else:
        split_days = {r["day"].lower() for r in c.execute("SELECT DISTINCT day FROM splits").fetchall()}
        for day in rotation:
            if day.lower() != "rest" and day.lower() not in split_days:
                problems.append({"check": "rotation",
                                 "fix": f"rotation day '{day}' matches no splits.day value (see split show)"})
    orphan_prog = c.execute(
        "SELECT workout_id, exercise FROM progression WHERE workout_id NOT IN (SELECT id FROM workouts)").fetchall()
    for r in orphan_prog:
        problems.append({"check": "progression_workout",
                         "fix": f"progression for '{r['exercise']}' points at missing workout {r['workout_id']}"})
    expected = set(re.findall(r"CREATE TABLE IF NOT EXISTS (\w+)", SCHEMA))
    live = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    if live != expected:
        problems.append({"check": "schema_drift",
                         "fix": f"live tables {sorted(live)} differ from SCHEMA {sorted(expected)}"})
    dump_file = os.path.join(os.path.dirname(os.path.abspath(DB)), "workouts.sql")
    try:
        with open(dump_file) as f:
            dump_text = f.read()
    except OSError:
        dump_text = None
    if dump_text is not None:
        dump_tables = set(re.findall(r"CREATE TABLE (?:IF NOT EXISTS )?(\w+)", dump_text))
        if dump_tables != expected:
            problems.append({"check": "dump_drift",
                             "fix": f"workouts.sql tables {sorted(dump_tables)} differ from SCHEMA "
                                    f"{sorted(expected)}; run log.py dump"})
    if problems:
        print(json.dumps({"ok": False, "problems": problems}, indent=2))
        sys.exit(1)
    print(json.dumps({"ok": True, "muscles": len(constants["muscles"])}))


def cmd_audit():
    """Run deterministic audit checks and output flagged items."""
    c = conn()
    import itertools

    flags = []

    # Checks 2 (missing muscle tags) and 3 (mapping drift) are structurally
    # impossible: the mapping is authoritative at log time, per-set overrides
    # are refused, and the end gate requires every set to carry muscles.

    # Check 4: Implausible progression jumps
    # Rep-band thresholds (same scale as the planning confidence bands): a +1
    # rep gain is always 2.2%+ e1RM, so flat science-rate bounds would flag
    # every routine rep PR. Band is read off the current session best's reps;
    # above 15 reps e1RM is informational only and never flags.
    # Jumps explained by set/workout notes are skipped.
    sets = c.execute("""
        SELECT s.id, s.exercise, s.weight, s.reps, w.date, s.note AS set_note, w.notes AS workout_notes,
               CASE WHEN s.reps = 1 THEN s.weight ELSE s.weight * (1 + s.reps / 30.0) END as e1rm
        FROM sets s JOIN workouts w ON w.id = s.workout_id
        WHERE s.weight > 0 ORDER BY s.exercise, w.date, s.id
    """).fetchall()

    by_ex = {}
    for s in sets:
        by_ex.setdefault(s["exercise"], []).append(s)

    constants = load_constants()
    explained = tuple(constants.get("explained_keywords", ["deload", "return", "program change", "injury", "technique", "sick", "travel"]))
    thresholds = constants.get("thresholds", {})
    drop_pct = thresholds.get("progression_drop_pct", -50)
    dup_dist = thresholds.get("duplicate_name_distance", 2)
    stale_hours = thresholds.get("stale_workout_hours", 8)
    vol_weeks = thresholds.get("volume_window_weeks", 8)
    vol_bad = thresholds.get("volume_bad_weeks", 4)

    def jump_bound(reps):
        for band in constants.get("rep_bands", []):
            max_reps = band.get("max_reps")
            if max_reps is None:
                return None
            if reps <= max_reps:
                return band.get("jump_pct")
        return None

    for ex, ex_sets in by_ex.items():
        by_date = {}
        notes_by_date = {}
        for s in ex_sets:
            d = s["date"]
            if d not in by_date or s["e1rm"] > by_date[d][0]:
                by_date[d] = (s["e1rm"], s["reps"])
            blob = ((s["set_note"] or "") + " " + (s["workout_notes"] or "")).lower()
            notes_by_date[d] = (notes_by_date.get(d, "") + " " + blob).strip()
        dates = sorted(by_date.keys())
        for i in range(1, len(dates)):
            prev, _ = by_date[dates[i-1]]
            curr, reps = by_date[dates[i]]
            bound = jump_bound(reps)
            if bound is None:
                continue
            if prev > 0:
                pct = (curr - prev) / prev * 100
                if pct > bound:
                    if any(k in notes_by_date.get(dates[i-1], "") or k in notes_by_date.get(dates[i], "") for k in explained):
                        continue
                    flags.append({"check": "progression_jump", "severity": "high", "evidence": f"{ex}: {prev:.1f} -> {curr:.1f} e1RM ({pct:.1f}% jump, bound {bound}%) on {dates[i]}", "fix": "verify data entry, add explanatory note, or update weight/reps"})
                elif pct < drop_pct:
                    if any(k in notes_by_date.get(dates[i-1], "") or k in notes_by_date.get(dates[i], "") for k in explained):
                        continue
                    flags.append({"check": "progression_drop", "severity": "medium", "evidence": f"{ex}: {prev:.1f} -> {curr:.1f} e1RM ({pct:.1f}% drop) on {dates[i]}", "fix": "verify data entry, or add deload/return note if intentional"})

    # Check 1: Exercise name duplicates
    exercises = [r["exercise"] for r in c.execute("SELECT DISTINCT exercise FROM sets").fetchall()]
    for a, b in itertools.combinations(exercises, 2):
        if _levenshtein(a, b) <= dup_dist:
            flags.append({"check": "duplicate_names", "severity": "low", "evidence": f"'{a}' vs '{b}' (Levenshtein <= {dup_dist})", "fix": "rename <old> <new>"})

    # Check 7: Stale open workouts
    stale = c.execute("""
        SELECT w.id, w.date FROM workouts w
        WHERE w.status = 'open'
          AND (date(w.date) < date('now') OR
               (SELECT MAX(created) FROM sets WHERE workout_id = w.id) < datetime('now', ?))
    """, (f"-{stale_hours} hours",)).fetchall()
    for s in stale:
        flags.append({"check": "stale_workout", "severity": "high", "evidence": f"workout {s['id']} from {s['date']} still open", "fix": "end with note, or delete-workout if empty"})

    # Check 5: Goal trajectory divergence (deterministic).
    for g in c.execute("SELECT * FROM goals WHERE status = 'active' ORDER BY id").fetchall():
        prog = goal_progress(c, dict(g))
        if prog["consecutive_misses"] >= 2:
            slippage_notes = c.execute(
                "SELECT DISTINCT w.id FROM workouts w JOIN sets s ON s.workout_id = w.id "
                "WHERE s.exercise = ? AND date(w.date) >= date(?) AND (w.notes LIKE '%slippage%' "
                "OR w.notes LIKE '%extend%' OR w.notes LIKE '%compress%' OR s.note LIKE '%slippage%')",
                (g["exercise"], g["created"][:10])).fetchall()
            if not slippage_notes:
                flags.append({"check": "goal_divergence", "severity": "high",
                              "evidence": f"goal {g['id']} ({g['exercise']} -> {g['target_e1rm']} by {g['deadline']}): "
                                          f"{prog['consecutive_misses']} consecutive sessions off trajectory",
                              "fix": f"goal rewrite {g['id']}, or extend the deadline conversation"})
        if prog["slippage"]:
            flags.append({"check": "goal_slippage", "severity": "medium",
                          "evidence": f"goal {g['id']} ({g['exercise']}): {prog['remaining']} sessions left "
                                      f"but split frequency fits fewer before {g['deadline']}",
                          "fix": f"extend the deadline or compress jumps, never silently"})

    # Check 8: Volume vs MEV, rolling window from constants (current week + back).
    # Every week in the window counts: weeks with no logged sets are 0, not
    # absent. Zero and low volume are separate flags; bad weeks are counted
    # across the whole window, a good week in between does not reset anything.
    from datetime import date, timedelta
    today = date.today()
    week_starts = [today - timedelta(days=today.weekday() + 7 * i) for i in range(vol_weeks - 1, -1, -1)]
    base = week_starts[0].isoformat()
    mev_bounds = {m: e["mev"] for m, e in constants["muscles"].items()}
    priorities = read_priorities(c)
    for muscle, mev in mev_bounds.items():
        rows = c.execute("""
            SELECT date(w.date) as day, COUNT(*) as sets
            FROM sets s
            JOIN workouts w ON w.id = s.workout_id
            JOIN set_muscles sm ON sm.set_id = s.id
            WHERE sm.muscle = ? AND date(w.date) >= ?
            GROUP BY day
        """, (muscle, base)).fetchall()
        per_day = {r["day"]: r["sets"] for r in rows}
        weekly = []
        for ws in week_starts:
            we = ws + timedelta(days=7)
            total = sum(n for d, n in per_day.items() if ws.isoformat() <= d < we.isoformat())
            weekly.append(total)
        counts = "[" + ", ".join(str(n) for n in weekly) + "]"
        zero_weeks, low_weeks = count_bad_weeks(weekly, mev)
        # A muscle explicitly marked deprioritize is intentionally held back:
        # its flags still stand (listed, never silently dropped) but drop one
        # severity level and carry the reason, so the audit reads as explained.
        deprioritized = priorities.get(muscle, {}).get("tier") == "deprioritize"
        suffix = " (priority: deprioritize, intentional)" if deprioritized else ""
        if zero_weeks >= vol_bad:
            flags.append({"check": "volume_zero", "severity": "medium" if deprioritized else "high",
                          "evidence": f"{muscle}: 0 sets in {zero_weeks} of last {vol_weeks} weeks {counts} (MEV {mev}){suffix}",
                          "fix": "add volume, or add Active rule explaining"})
        if low_weeks >= vol_bad:
            flags.append({"check": "volume_low", "severity": "low" if deprioritized else "medium",
                          "evidence": f"{muscle}: below MEV in {low_weeks} of last {vol_weeks} weeks {counts} (MEV {mev}){suffix}",
                          "fix": "add volume, or add Active rule explaining"})

    # Output report
    print(f"Audit complete: {len(flags)} flags (checks 2, 3, 6 are structurally impossible, see AUDIT.md)")
    for i, f in enumerate(flags, 1):
        print(f"{i}. [{f['check']}] - {f['severity'].upper()}")
        print(f"   Evidence: {f['evidence']}")
        print(f"   Fix: {f['fix']}")
    print(json.dumps({"flags": flags, "skipped": []}))


def cmd_sync(force=False):
    try:
        cfg = json.load(open(CFG))
        url, secret = cfg["url"], cfg["secret"]
    except (OSError, KeyError, ValueError):
        sys.exit("no sync config, expected url and secret in " + CFG)
    c = conn()
    # Integrity check before sync
    integrity = c.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok":
        sys.exit("database integrity check failed: " + integrity)
    # Pull-first: fetch the current snapshot ETag so the push below carries
    # If-Match. A stale base gets a 412 instead of silently overwriting.
    base_etag = None
    if not force:
        get_req = urllib.request.Request(url + "/snapshot",
                                         headers={"Authorization": "Bearer " + secret,
                                                  "User-Agent": "reps-sync/1"})
        try:
            with urllib.request.urlopen(get_req, timeout=30) as res:
                base_etag = res.headers.get("ETag")
        except OSError as e:
            sys.exit("sync pull-first failed: " + str(e))
    payload = json.dumps(build_snapshot(c)).encode()
    headers = {"Content-Type": "application/json", "Authorization": "Bearer " + secret,
               "User-Agent": "reps-sync/1"}
    if base_etag:
        headers["If-Match"] = base_etag
    if force:
        headers["X-Sync-Force"] = "1"
    req = urllib.request.Request(url + "/sync", data=payload, method="PUT", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            print(json.dumps({"synced": True, "bytes": len(payload), "reply": json.loads(res.read().decode())}))
    except urllib.error.HTTPError as e:
        if e.code == 412:
            try:
                detail = json.loads(e.read().decode())
            except ValueError:
                detail = {}
            server_etag = detail.get("etag") or e.headers.get("ETag")
            sys.exit(f"sync rejected: snapshot changed since pull (server {server_etag}), another session pushed first. "
                     "Reconcile, then 'log.py sync force' to overwrite deliberately.")
        sys.exit("sync failed: " + str(e))
    except OSError as e:
        sys.exit("sync failed: " + str(e))

    # Dump SQL for git history
    sql_file = os.path.join(os.path.dirname(DB), "workouts.sql")
    with open(sql_file, 'w') as f:
        for line in c.iterdump():
            f.write(f"{line}\n")
    print(f"dumped SQL to {sql_file}")


def cmd_rename(old, new):
    c = conn()
    old = old.strip().lower()
    new = new.strip().lower()
    if old == new:
        sys.exit("old and new exercise names are identical, nothing to rename")
    mapping = c.execute("SELECT muscles, is_bodyweight_only FROM lift_muscle_map WHERE exercise = ?", (old,)).fetchone()
    target = c.execute("SELECT muscles, is_bodyweight_only FROM lift_muscle_map WHERE exercise = ?", (new,)).fetchone()
    if mapping and target and set(mapping["muscles"].split(",")) != set(target["muscles"].split(",")):
        sys.exit(f"'{new}' already maps to {target['muscles']}, not {mapping['muscles']}; retag one of them first, then rename")
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
    print(json.dumps({"renamed": renamed, "map_moved": map_moved}))


def cmd_retag(exercise, muscles, bodyweight=False):
    c = conn()
    exercise = exercise.strip().lower()
    muscles = clean_muscles(muscles)
    if not muscles:
        sys.exit("muscles cannot be empty, pass at least one group")
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
    print(json.dumps({"retag_exercise": exercise, "updated": updated, "is_bodyweight_only": is_bw}))


def cmd_delete_set(set_id):
    try:
        set_id = int(set_id)
    except (TypeError, ValueError):
        sys.exit("no such set")
    c = conn()
    row = c.execute("SELECT s.*, w.date FROM sets s JOIN workouts w ON w.id = s.workout_id WHERE s.id = ?", (set_id,)).fetchone()
    if not row:
        sys.exit("no such set")
    c.execute("DELETE FROM sets WHERE id = ?", (set_id,))
    c.commit()
    print(json.dumps({"deleted": set_id, "workout_id": row["workout_id"], "date": row["date"],
                      "was": {"exercise": row["exercise"], "weight": row["weight"], "reps": row["reps"]}}))


def cmd_delete_workout(workout_id):
    try:
        workout_id = int(workout_id)
    except (TypeError, ValueError):
        sys.exit("no such workout")
    c = conn()
    row = c.execute("SELECT * FROM workouts WHERE id = ?", (workout_id,)).fetchone()
    if not row:
        sys.exit("no such workout")
    n = c.execute("SELECT COUNT(*) n FROM sets WHERE workout_id = ?", (workout_id,)).fetchone()["n"]
    c.execute("DELETE FROM sets WHERE workout_id = ?", (workout_id,))
    c.execute("DELETE FROM workouts WHERE id = ?", (workout_id,))
    c.commit()
    print(json.dumps({"deleted_workout": workout_id, "date": row["date"], "deleted_sets": n}))


def cmd_update_workout(workout_id, field, value):
    allowed = {"notes", "date", "status"}
    if field not in allowed:
        sys.exit("field must be one of notes date status")
    try:
        workout_id = int(workout_id)
    except (TypeError, ValueError):
        sys.exit("no such workout")
    if field == "date":
        try:
            date.fromisoformat(value)
        except ValueError:
            sys.exit("date must be YYYY-MM-DD")
        if date.fromisoformat(value) > date.today():
            sys.exit("workout date cannot be in the future")
    if field == "status" and value not in ("open", "done", "rest"):
        sys.exit("status must be open, done or rest")
    c = conn()
    if field == "status" and value == "open":
        other = c.execute("SELECT id FROM workouts WHERE status = 'open' AND id != ?", (int(workout_id),)).fetchone()
        if other:
            sys.exit(f"workout {other['id']} is already open; end or delete it first")
    if field == "status" and value == "rest":
        row = c.execute("SELECT date FROM workouts WHERE id = ?", (int(workout_id),)).fetchone()
        if not row:
            sys.exit("no such workout")
        n = c.execute("SELECT COUNT(*) n FROM sets WHERE workout_id = ?", (int(workout_id),)).fetchone()["n"]
        if n > 0:
            sys.exit("workout has sets, cannot mark it rest (move or delete them first)")
        dup = c.execute("SELECT id FROM workouts WHERE date = ? AND status = 'rest' AND id != ?",
                        (row["date"], int(workout_id))).fetchone()
        if dup:
            sys.exit(f"{row['date']} already has a rest row (id {dup['id']}), add a note there instead of doubling up")
    cur = c.execute(f"UPDATE workouts SET {field} = ? WHERE id = ?", (value, int(workout_id)))
    if cur.rowcount == 0:
        sys.exit("no such workout")
    c.commit()
    print(json.dumps({"updated_workout": int(workout_id), "field": field}))


def cmd_session(datestr):
    try:
        day = date.fromisoformat(datestr).isoformat()
    except ValueError:
        sys.exit("date must be YYYY-MM-DD")
    c = conn()
    wrows = c.execute("SELECT * FROM workouts WHERE date = ? ORDER BY id", (day,)).fetchall()
    out = []
    for w in wrows:
        sets = c.execute("SELECT * FROM sets WHERE workout_id = ? ORDER BY id", (w["id"],)).fetchall()
        out.append({"workout": dict(w), "sets": attach_muscles(c, sets)})
    print(json.dumps({"date": day, "workouts": out}, indent=2))


def cmd_range(fromstr, tostr):
    try:
        d0 = date.fromisoformat(fromstr).isoformat()
        d1 = date.fromisoformat(tostr).isoformat()
    except ValueError:
        sys.exit("dates must be YYYY-MM-DD")
    c = conn()
    wrows = c.execute("SELECT * FROM workouts WHERE date >= ? AND date <= ? ORDER BY date, id", (d0, d1)).fetchall()
    out = []
    for w in wrows:
        sets = c.execute("SELECT * FROM sets WHERE workout_id = ? ORDER BY id", (w["id"],)).fetchall()
        out.append({"workout": dict(w), "sets": attach_muscles(c, sets)})
    print(json.dumps({"from": d0, "to": d1, "workouts": out}, indent=2))


def cmd_notes(limit):
    try:
        lim = max(1, min(2000, int(limit)))
    except ValueError:
        lim = 200
    c = conn()
    wrows = c.execute("SELECT id, date, notes FROM workouts WHERE notes != '' ORDER BY date DESC, id DESC LIMIT ?", (lim,)).fetchall()
    srows = c.execute(
        "SELECT s.id, s.exercise, s.weight, s.reps, s.note, w.date FROM sets s "
        "JOIN workouts w ON w.id = s.workout_id WHERE s.note != '' ORDER BY w.date DESC, s.id DESC LIMIT ?", (lim,)).fetchall()
    print(json.dumps({"workout_notes": [dict(r) for r in wrows], "set_notes": [dict(r) for r in srows]}, indent=2))


def cmd_calendar():
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
    print(json.dumps({"dates": days}, indent=2))


def cmd_context(n):
    try:
        limit = max(1, min(5, int(n)))
    except ValueError:
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
            "SELECT weight, reps, CASE WHEN reps = 1 THEN weight ELSE weight * (1 + reps / 30.0) END AS e1rm FROM sets WHERE exercise = ? ORDER BY e1rm DESC LIMIT 1", (r["exercise"],)
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
    print(json.dumps({"recent": recent, "lifts": best, "workouts_total": totals["w"], "bodyweight_last": bw}, indent=2))


def usage():
    sys.exit(
        "usage: log.py start [note] | log <exercise> <weight> <reps> [note] [muscles=a,b] [bw] "
        "| update <id> <field> <value> | update-workout <id> <field> <value> | retag <exercise> <muscles> [bw] "
        "| delete-set <id> | delete-workout <id> | end [note] | today | exercises | history <ex> [limit] "
         "| session <yyyy-mm-dd> | range <from> <to> | notes [limit] | calendar "
         "| stats | export | rename <old> <new> | context [n] | weigh <kg> [note] | sync [force] | restore [force] | audit | rest [yyyy-mm-dd] [note]"
         " | constants show [key] | constants validate | constants set <key> <json-value>"
         " | plan [--slot <day>] [--verbose] | check [note]"
         " | progression set <exercise> --verdict <hit|miss|hold|baseline> --next <target> --direction <up|flat|down> [--note <t>] [--workout <id>]"
         " | progression show [exercise] | flag add <subject> <reason> | flag list | flag consume <id>"
         " | priority set <muscle> <tier> [--until <date>] | priority clear <muscle> | priority list"
         " | deload set --scope <lift|slot> <name> | deload clear"
         " | split show [day] [--variant active|baseline] | split set <day> <slot#> <movements> <sets> [--variant baseline]"
         " | split move <day> <exercise> --to <slot#> | split reconcile --day <day> [--after <exercise>]"
         " | split diff | split revert [day]"
         " | map show [exercise] | map set <exercise> <muscles> [bw] | map note <exercise> <text>"
         " | rule add <text> --subject <x> [--expires <date>] | rule list [--expiring-within <n>]"
         " | rule confirm <id> --extend <date> | --archive"
         " | goal add <exercise> --target <e1rm> --deadline <date> [--desc <t>] [--from <e1rm>]"
         " | goal show [id] | goal rewrite <id> | goal drop <id>"
         " | autoreg apply --day <day> --slot <n> --to <movements> <sets> --evidence <text> [--from <movements>]"
         " | autoreg log | autoreg revert <id>"
    )


def main():
    if len(sys.argv) < 2:
        usage()
    cmd = sys.argv[1]
    rest = sys.argv[2:]
    if cmd == "start":
        cmd_start(" ".join(rest))
    elif cmd == "log" and len(rest) >= 3:
        # Exercise is everything up to the first two numeric tokens (weight, reps).
        nums = [i for i, t in enumerate(rest) if re.fullmatch(r"\d+(\.\d+)?", t)]
        if len(nums) < 2:
            sys.exit("usage: log <exercise> <weight> <reps> [note] [muscles=a,b] [bw] (quoting never needed)")
        exercise, weight, reps = " ".join(rest[:nums[0]]), rest[nums[0]], rest[nums[1]]
        if not exercise:
            sys.exit("usage: log <exercise> <weight> <reps> [note] [muscles=a,b] [bw] (quoting never needed)")
        note_parts = []
        muscles = ""
        bodyweight = False
        for tok in rest[nums[1] + 1:]:
            if tok.startswith("muscles="):
                muscles = tok[len("muscles="):]
                continue
            if tok == "bw":
                bodyweight = True
                continue
            note_parts.append(tok)
        cmd_log(exercise, weight, reps, " ".join(note_parts), muscles, bodyweight)
    elif cmd == "update" and len(rest) >= 3:
        cmd_update(rest[0], rest[1], " ".join(rest[2:]))
    elif cmd == "end":
        force = None
        toks = list(rest)
        if "--force" in toks:
            i = toks.index("--force")
            force = " ".join(toks[i + 1:]).strip() or None
            toks = toks[:i]
            if not force:
                sys.exit("end --force needs a reason, it is written into the workout note")
        cmd_end(" ".join(toks), force)
    elif cmd == "today":
        cmd_today()
    elif cmd == "exercises":
        cmd_exercises()
    elif cmd == "history" and len(rest) >= 1:
        lim = rest[1] if len(rest) > 1 else "50"
        cmd_history(rest[0], lim)
    elif cmd == "stats":
        cmd_stats()
    elif cmd == "export":
        cmd_export()
    elif cmd == "rename" and len(rest) >= 2:
        cmd_rename(rest[0], " ".join(rest[1:]))
    elif cmd == "retag" and len(rest) >= 2:
        bodyweight = "bw" in rest
        rest = [r for r in rest if r != "bw"]
        if len(rest) >= 2:
            cmd_retag(rest[0], ",".join(rest[1:]), bodyweight)
    elif cmd == "delete-set" and len(rest) >= 1:
        cmd_delete_set(rest[0])
    elif cmd == "delete-workout" and len(rest) >= 1:
        cmd_delete_workout(rest[0])
    elif cmd == "update-workout" and len(rest) >= 3:
        cmd_update_workout(rest[0], rest[1], " ".join(rest[2:]))
    elif cmd == "session" and len(rest) >= 1:
        cmd_session(rest[0])
    elif cmd == "range" and len(rest) >= 2:
        cmd_range(rest[0], rest[1])
    elif cmd == "notes":
        cmd_notes(rest[0] if len(rest) > 0 else "200")
    elif cmd == "calendar":
        cmd_calendar()
    elif cmd == "context":
        lim = rest[0] if len(rest) > 0 else "3"
        cmd_context(lim)
    elif cmd == "weigh" and len(rest) >= 1:
        cmd_weigh(rest[0], " ".join(rest[1:]))
    elif cmd == "sync":
        cmd_sync("force" in rest)
    elif cmd == "restore":
        cmd_restore("force" in rest)
    elif cmd == "audit":
        cmd_audit()
    elif cmd == "constants" and rest[:1] == ["show"]:
        cmd_constants_show(rest[1] if len(rest) > 1 else None)
    elif cmd == "constants" and rest[:1] == ["validate"]:
        cmd_constants_validate()
    elif cmd == "constants" and rest[:1] == ["set"] and len(rest) >= 3:
        cmd_constants_set(rest[1], " ".join(rest[2:]))
    elif cmd == "check":
        cmd_check(" ".join(rest))
    elif cmd == "doctor":
        cmd_doctor()
    elif cmd == "dump":
        cmd_dump()
    elif cmd == "meta" and rest[:1] == ["show"]:
        cmd_meta_show(rest[1] if len(rest) > 1 else None)
    elif cmd == "meta" and rest[:1] == ["set"] and len(rest) >= 3:
        cmd_meta_set(rest[1], " ".join(rest[2:]))
    elif cmd == "progression" and rest[:1] == ["set"] and len(rest) >= 2:
        toks = rest[1:]
        first_flag = next((i for i, t in enumerate(toks) if t.startswith("--")), len(toks))
        exercise = " ".join(toks[:first_flag])
        verdict = next_target = direction = note = workout_id = None
        toks = toks[first_flag:]
        i = 0
        while i < len(toks):
            if toks[i] == "--verdict" and i + 1 < len(toks):
                verdict = toks[i + 1]
                i += 2
            elif toks[i] == "--next" and i + 1 < len(toks):
                next_target = toks[i + 1]
                i += 2
            elif toks[i] == "--direction" and i + 1 < len(toks):
                direction = toks[i + 1]
                i += 2
            elif toks[i] == "--note" and i + 1 < len(toks):
                note = toks[i + 1]
                i += 2
            elif toks[i] == "--workout" and i + 1 < len(toks):
                workout_id = toks[i + 1]
                i += 2
            else:
                i += 1
        cmd_progression_set(exercise, verdict, next_target, direction, note or "", workout_id)
    elif cmd == "progression" and rest[:1] == ["show"]:
        cmd_progression_show(" ".join(rest[1:]) or None)
    elif cmd == "flag" and rest[:1] == ["add"] and len(rest) >= 3:
        # Subject is an exercise or muscle: longest known match wins, so both
        # sides can go unquoted; unknown subjects fall back to first token.
        toks = rest[1:]
        known_subjects = ({r["exercise"] for r in conn().execute("SELECT exercise FROM lift_muscle_map").fetchall()}
                          | set(load_constants()["muscles"]))
        subject, reason = resolve_known_prefix(toks, known_subjects, 4, "subject (exercise or muscle)")
        cmd_flag_add(subject, reason)
    elif cmd == "flag" and rest[:1] == ["list"]:
        cmd_flag_list()
    elif cmd == "flag" and rest[:1] == ["consume"] and len(rest) >= 2:
        cmd_flag_consume(rest[1])
    elif cmd == "priority" and rest[:1] == ["set"] and len(rest) >= 3:
        toks = rest[1:]
        until = None
        if "--until" in toks:
            j = toks.index("--until")
            until = " ".join(toks[j + 1:]) if j + 1 < len(toks) else None
            toks = toks[:j]
        if len(toks) < 2:
            sys.exit("usage: log.py priority set <muscle> <tier> [--until <date>] (quoting never needed)")
        cmd_priority_set(" ".join(toks[:-1]), toks[-1], until)
    elif cmd == "priority" and rest[:1] == ["clear"] and len(rest) >= 2:
        cmd_priority_clear(" ".join(rest[1:]))
    elif cmd == "priority" and rest[:1] == ["list"]:
        cmd_priority_list()
    elif cmd == "deload" and rest[:1] == ["set"]:
        scope = subject = None
        toks = rest[1:]
        if "--scope" in toks:
            j = toks.index("--scope")
            scope = toks[j + 1] if j + 1 < len(toks) else None
            toks = toks[:j] + toks[j + 2:]
        subject = " ".join(toks) or None
        cmd_deload_set(scope, subject)
    elif cmd == "deload" and rest[:1] == ["clear"]:
        cmd_deload_clear()
    elif cmd == "split" and rest[:1] == ["show"]:
        toks = rest[1:]
        variant = "active"
        if "--variant" in toks:
            j = toks.index("--variant")
            variant = toks[j + 1] if j + 1 < len(toks) else "active"
            toks = toks[:j] + toks[j + 2:]
        cmd_split_show(" ".join(toks) or None, variant)
    elif cmd == "split" and rest[:1] == ["set"] and len(rest) >= 5:
        toks = rest[1:]
        variant = "active"
        if "--variant" in toks:
            j = toks.index("--variant")
            variant = toks[j + 1] if j + 1 < len(toks) else "active"
            toks = toks[:j] + toks[j + 2:]
        # Day is everything up to the first integer (the slot); sets is last.
        slot_at = next((i for i, t in enumerate(toks) if re.fullmatch(r"\d+", t)), None)
        if slot_at is None or slot_at < 1 or slot_at >= len(toks):
            sys.exit("usage: log.py split set <day> <slot#> <movements> <sets> (quote the day if this fails)")
        cmd_split_set(" ".join(toks[:slot_at]), toks[slot_at], " ".join(toks[slot_at + 1:-1]), toks[-1], variant)
    elif cmd == "split" and rest[:1] == ["move"] and len(rest) >= 4:
        toks = rest[1:]
        to_slot = None
        if "--to" in toks:
            j = toks.index("--to")
            to_slot = toks[j + 1] if j + 1 < len(toks) else None
            toks = toks[:j] + toks[j + 2:]
        day, exercise = split_day_prefix(toks)
        if not day or not exercise or to_slot is None:
            sys.exit("usage: log.py split move <day> <exercise> --to <slot#> (quote multi-word names if this fails)")
        cmd_split_move(day, exercise, to_slot)
    elif cmd == "split" and rest[:1] == ["reconcile"]:
        toks = rest[1:]
        day = after = None
        if "--day" in toks:
            j = toks.index("--day")
            k = next((i for i in range(j + 1, len(toks)) if toks[i].startswith("--")), len(toks))
            day, _ = split_day_prefix(toks[j + 1:k])
            toks = toks[:j] + toks[k:]
        if "--after" in toks:
            j = toks.index("--after")
            after = " ".join(toks[j + 1:]) if j + 1 < len(toks) else None
        if not day:
            sys.exit("usage: log.py split reconcile --day <day> [--after <exercise>]")
        cmd_split_reconcile(day, after)
    elif cmd == "split" and rest[:1] == ["diff"]:
        cmd_split_diff()
    elif cmd == "split" and rest[:1] == ["revert"]:
        cmd_split_revert(" ".join(rest[1:]) or None)
    elif cmd == "map" and rest[:1] == ["show"]:
        cmd_map_show(" ".join(rest[1:]) or None)
    elif cmd == "map" and rest[:1] == ["set"] and len(rest) >= 3:
        bodyweight = "bw" in rest or "--bw" in rest
        toks = [t for t in rest[1:] if t not in ("bw", "--bw")]
        # Muscles are matched word-by-word from the right against the known
        # vocabulary (commas ignored); everything before is the exercise name.
        vocab = set(load_constants()["muscles"]) | set(load_constants().get("untracked", []))
        words = " ".join(toks).replace(",", " ").split()
        takes = 0
        while takes < len(words):
            rest = len(words) - takes
            two = " ".join(words[rest - 2:rest]).lower() if rest >= 2 else None
            one = words[rest - 1].lower()
            if two is not None and canon_muscle_name(two, vocab) is not None:
                takes += 2
            elif canon_muscle_name(one, vocab) is not None:
                takes += 1
            else:
                break
        if takes == 0 or takes >= len(words):
            sys.exit("usage: log.py map set <exercise> <muscles> [bw] (quoting never needed)")
        cmd_retag(" ".join(words[:len(words) - takes]),
                  ",".join(_join_muscles(words[len(words) - takes:], vocab)), bodyweight)
    elif cmd == "map" and rest[:1] == ["note"] and len(rest) >= 3:
        toks = rest[1:]
        known = {r["exercise"] for r in conn().execute("SELECT exercise FROM lift_muscle_map").fetchall()}
        exercise, note = resolve_known_prefix(toks, known, 5, "exercise")
        cmd_map_note(exercise, note)
    elif cmd == "rule" and rest[:1] == ["add"] and len(rest) >= 2:
        toks = rest[1:]
        subject = expires = None
        if "--subject" in toks:
            j = toks.index("--subject")
            k = next((i for i in range(j + 1, len(toks)) if toks[i].startswith("--")), len(toks))
            subject = " ".join(toks[j + 1:k]) or None
            toks = toks[:j] + toks[k:]
        if "--expires" in toks:
            j = toks.index("--expires")
            expires = toks[j + 1] if j + 1 < len(toks) else None
            toks = toks[:j] + toks[j + 2:]
        cmd_rule_add(" ".join(toks), subject, expires)
    elif cmd == "rule" and rest[:1] == ["list"]:
        window = None
        if "--expiring-within" in rest:
            j = rest.index("--expiring-within")
            window = rest[j + 1] if j + 1 < len(rest) else None
        cmd_rule_list(window)
    elif cmd == "goal" and rest[:1] == ["add"] and len(rest) >= 2:
        exercise = rest[1]
        toks = rest[2:]
        target = deadline = desc = start = None
        i = 0
        while i < len(toks):
            if toks[i] == "--target" and i + 1 < len(toks):
                target = toks[i + 1]
                i += 2
            elif toks[i] == "--deadline" and i + 1 < len(toks):
                deadline = toks[i + 1]
                i += 2
            elif toks[i] == "--desc":
                desc = " ".join(toks[i + 1:]) if i + 1 < len(toks) else ""
                break
            elif toks[i] == "--from" and i + 1 < len(toks):
                start = toks[i + 1]
                i += 2
            else:
                i += 1
        cmd_goal_add(exercise, target, deadline, desc or "", start)
    elif cmd == "goal" and rest[:1] == ["show"]:
        cmd_goal_show(" ".join(rest[1:]) or None)
    elif cmd == "goal" and rest[:1] == ["rewrite"] and len(rest) >= 2:
        cmd_goal_rewrite(rest[1])
    elif cmd == "goal" and rest[:1] == ["drop"] and len(rest) >= 2:
        cmd_goal_drop(rest[1])
    elif cmd == "autoreg" and rest[:1] == ["log"]:
        cmd_autoreg_log()
    elif cmd == "autoreg" and rest[:1] == ["revert"] and len(rest) >= 2:
        cmd_autoreg_revert(rest[1])
    elif cmd == "autoreg" and rest[:1] == ["apply"]:
        # Flags delimit multi-word values, so day/movements/evidence go unquoted.
        vals: dict = {}
        current = None
        for tok in rest[1:]:
            if tok in ("--day", "--slot", "--to", "--evidence", "--from"):
                current = tok
                vals[current] = []
            elif current is None:
                sys.exit("usage: log.py autoreg apply --day <day> --slot <n> --to <movements> <sets> "
                         "--evidence <text> [--from <movements>]")
            else:
                vals[current].append(tok)
        day = " ".join(vals.get("--day", [])) or None
        slot = " ".join(vals.get("--slot", [])) or None
        to_toks = vals.get("--to", [])
        evidence = " ".join(vals.get("--evidence", [])) or None
        from_toks = vals.get("--from")
        if not day or not slot or len(to_toks) < 2 or not evidence:
            sys.exit("usage: log.py autoreg apply --day <day> --slot <n> --to <movements> <sets> "
                     "--evidence <text> [--from <movements>]")
        cmd_autoreg_apply(day, slot, " ".join(to_toks[:-1]), to_toks[-1], evidence,
                          " ".join(from_toks) if from_toks is not None else None)
    elif cmd == "rule" and rest[:1] == ["confirm"] and len(rest) >= 2:
        extend = archive = None
        archive = "--archive" in rest
        if "--extend" in rest:
            j = rest.index("--extend")
            extend = rest[j + 1] if j + 1 < len(rest) else None
        cmd_rule_confirm(rest[1], extend, archive)
    elif cmd == "plan":
        slot = None
        verbose = "--verbose" in rest
        toks = [t for t in rest if t != "--verbose"]
        if "--slot" in toks:
            i = toks.index("--slot")
            slot = " ".join(toks[i + 1:]) if i + 1 < len(toks) else None
        cmd_plan(slot, verbose)
    elif cmd == "rest":
        day = date.today().isoformat()
        words = rest
        if words:
            try:
                day = date.fromisoformat(words[0]).isoformat()
                words = words[1:]
            except ValueError:
                pass
        cmd_rest(day, " ".join(words))
    else:
        usage()


if __name__ == "__main__":
    main()
