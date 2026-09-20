#!/usr/bin/env python3
"""reps: dumb store for workout logs. No domain logic, agent owns meaning."""

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
"""


def conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA foreign_keys=ON")
    c.executescript(SCHEMA)
    return c


def clean_muscles(value):
    seen = set()
    out = []
    for p in value.split(","):
        m = p.strip().lower()
        if m and m not in seen:
            seen.add(m)
            out.append(m)
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
        warnings.append(f"logged muscles {muscles} differ from mapping {mapping['muscles']}; mapping kept, retag to change it everywhere")

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
    allowed = {"weight", "reps", "exercise", "note", "muscles"}
    if field not in allowed:
        sys.exit("field must be one of weight reps exercise note muscles")
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
    if field == "muscles":
        value = clean_muscles(value)
        if not value:
            sys.exit("muscles cannot be empty, pass at least one group or delete the set")
        c.execute("DELETE FROM set_muscles WHERE set_id = ?", (set_id,))
        for muscle in value.split(","):
            c.execute("INSERT INTO set_muscles (set_id, muscle) VALUES (?, ?)", (set_id, muscle))
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
            sys.exit(f"exercise '{value}' has no mapping in lift_muscle_map (run retag first)")
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
    if field != "muscles":
        c.execute("UPDATE sets SET {} = ? WHERE id = ?".format(field), (value, int(set_id)))
    c.commit()
    out = {"updated": int(set_id)}
    if warnings:
        out["warnings"] = warnings
    print(json.dumps(out))


def cmd_end(note):
    c = conn()
    w = open_workout(c)
    if not w:
        sys.exit("no open workout")
    if note:
        old = w["notes"]
        combined = (old + " " + note).strip() if old else note
        c.execute("UPDATE workouts SET notes = ? WHERE id = ?", (combined, w["id"]))
    c.execute("UPDATE workouts SET status = 'done' WHERE id = ?", (w["id"],))
    c.commit()
    n = c.execute("SELECT COUNT(*) n FROM sets WHERE workout_id = ?", (w["id"],)).fetchone()["n"]
    print(json.dumps({"closed": w["id"], "sets": n, "next": "audit this session, then sync, then commit workouts.sql"}))


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


def cmd_export():
    c = conn()
    workouts = [dict(r) for r in c.execute("SELECT * FROM workouts ORDER BY id").fetchall()]
    sets = attach_muscles(c, c.execute("SELECT * FROM sets ORDER BY id").fetchall())
    bw = [dict(r) for r in c.execute("SELECT * FROM bodyweight ORDER BY date, id").fetchall()]
    print(json.dumps({"exported": datetime.now().isoformat(timespec="seconds"), "workouts": workouts, "sets": sets, "bodyweight": bw}, indent=2))


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
        expected = {"workouts", "sets", "set_muscles", "bodyweight", "lift_muscle_map"}
        if tables != expected:
            sys.exit(f"dump is missing tables (has {sorted(tables)}), live DB untouched")
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


CONTRACT_MUSCLES = frozenset([
    "chest", "back", "front delt", "side delt", "rear delt",
    "biceps", "triceps", "quads", "hamstrings", "glutes",
    "adductors", "abs", "forearms",
])


def validate_constants(raw, source):
    """Validate a parsed constants candidate, exiting loudly on any defect."""
    if not isinstance(raw, dict) or not isinstance(raw.get("muscles"), dict):
        sys.exit(f"constants invalid at {source}: missing the muscles map")
    missing = CONTRACT_MUSCLES - set(raw["muscles"].keys())
    if missing:
        sys.exit(f"constants invalid at {source}: missing tracked muscles {sorted(missing)}")
    for muscle, entry in raw["muscles"].items():
        if not isinstance(entry, dict):
            sys.exit(f"constants invalid at {source}: muscle '{muscle}' is not an object")
        if not isinstance(entry.get("mev"), int) or isinstance(entry.get("mev"), bool) or entry["mev"] < 0:
            sys.exit(f"constants invalid at {source}: muscle '{muscle}' needs a non-negative mev")
        for bound in ("mav", "mrv"):
            val = entry.get(bound)
            if muscle == "forearms" and val is None:
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
        if not isinstance(entry.get("source"), str) or not isinstance(entry.get("color"), str):
            sys.exit(f"constants invalid at {source}: muscle '{muscle}' needs source and color strings")
    thresholds = raw.get("thresholds")
    if not isinstance(thresholds, dict):
        sys.exit(f"constants invalid at {source}: missing thresholds map")
    for key in ("stale_workout_hours", "stale_workout_days", "break_days",
                "e1rm_warn_ratio", "duplicate_name_distance"):
        val = thresholds.get(key)
        if not isinstance(val, (int, float)) or isinstance(val, bool) or val <= 0:
            sys.exit(f"constants invalid at {source}: thresholds.{key} must be positive")
    for key in ("volume_window_weeks", "volume_bad_weeks"):
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


def parse_priority_from_memory():
    """Parse the Priority (machine-readable) block from MEMORY.md.

    Mirrors parse_mev_from_science in structure: primary source is the
    fenced ````json priority`` block, absent muscles default to `maintain`.
    Returns {muscle: {"tier": ..., "since": ..., "until": ...}} with only
    well-formed entries; invalid ones are warned about and skipped.
    """
    valid_tiers = {"priority", "maintain", "deprioritize"}
    priorities: dict = {}
    try:
        with open(MEMORY_FILE, 'r') as f:
            content = f.read()
    except OSError:
        content = ""
    if not content:
        print("WARNING: parse_priority_from_memory could not read MEMORY.md, assuming all maintain")
        return priorities
    block = re.search(r'```json[^\n]*priority[^\n]*\n(.*?)```', content, re.DOTALL | re.IGNORECASE)
    if not block:
        print("WARNING: parse_priority_from_memory found no json priority block, assuming all maintain")
        return priorities
    try:
        raw = json.loads(block.group(1))
    except ValueError as e:
        print(f"WARNING: parse_priority_from_memory found priority JSON block but failed to parse it ({e}), assuming all maintain")
        return priorities
    if not isinstance(raw, dict):
        print("WARNING: parse_priority_from_memory priority block is not a JSON object, assuming all maintain")
        return priorities
    invalid = {}
    for k, v in raw.items():
        muscle = k.strip().lower() if isinstance(k, str) else k
        if (isinstance(muscle, str) and muscle
                and isinstance(v, dict)
                and v.get("tier") in valid_tiers
                and ("since" not in v or v["since"] is None or isinstance(v["since"], str))
                and ("until" not in v or v["until"] is None or isinstance(v["until"], str))):
            priorities[muscle] = {"tier": v["tier"], "since": v.get("since"), "until": v.get("until")}
        else:
            invalid[k] = v
    if invalid:
        print(f"WARNING: parse_priority_from_memory ignoring invalid priority entries: {invalid}")
    return priorities


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


def cmd_audit():
    """Run deterministic audit checks and output flagged items."""
    c = conn()
    import itertools

    flags = []

    # Check 2: Missing muscle tags
    missing = c.execute("""
        SELECT s.id, s.exercise, w.date
        FROM sets s
        JOIN workouts w ON w.id = s.workout_id
        LEFT JOIN set_muscles sm ON sm.set_id = s.id
        WHERE sm.muscle IS NULL
    """).fetchall()
    for m in missing:
        flags.append({"check": "missing_muscles", "severity": "high", "evidence": f"set {m['id']} ({m['exercise']} on {m['date']}) has no muscles", "fix": "retag <exercise> <muscles>"})

    # Check 3: Muscle mapping drift
    drift = c.execute("""
        SELECT s.id, s.exercise,
               group_concat(sm.muscle, ',') as logged,
               m.muscles as mapped
        FROM sets s
        JOIN lift_muscle_map m ON m.exercise = s.exercise
        LEFT JOIN set_muscles sm ON sm.set_id = s.id
        GROUP BY s.id
    """).fetchall()
    for d in drift:
        logged_set = set(d['logged'].split(',')) if d['logged'] else set()
        mapped_set = set(d['mapped'].split(',')) if d['mapped'] else set()
        if logged_set != mapped_set:
            flags.append({"check": "muscle_drift", "severity": "medium", "evidence": f"set {d['id']} ({d['exercise']}): logged {d['logged']} vs mapped {d['mapped']}", "fix": "retag <exercise> <muscles> or update Lift mapping"})

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

    # Check 8: Volume vs MEV, rolling window from constants (current week + back).
    # Every week in the window counts: weeks with no logged sets are 0, not
    # absent. Zero and low volume are separate flags; bad weeks are counted
    # across the whole window, a good week in between does not reset anything.
    from datetime import date, timedelta
    today = date.today()
    week_starts = [today - timedelta(days=today.weekday() + 7 * i) for i in range(vol_weeks - 1, -1, -1)]
    base = week_starts[0].isoformat()
    mev_bounds = {m: e["mev"] for m, e in constants["muscles"].items()}
    priorities = parse_priority_from_memory()
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
        zero_weeks = sum(1 for n in weekly if n == 0)
        low_weeks = sum(1 for n in weekly if 0 < n < mev)
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
    print(f"Audit complete: {len(flags)} flags (checks 5 and 6 are manual only, see AUDIT.md)")
    for i, f in enumerate(flags, 1):
        print(f"{i}. [{f['check']}] - {f['severity'].upper()}")
        print(f"   Evidence: {f['evidence']}")
        print(f"   Fix: {f['fix']}")
    print(json.dumps({"flags": flags, "skipped": ["goal_trajectory", "split_slots"]}))


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
    workouts = [dict(r) for r in c.execute("SELECT * FROM workouts ORDER BY id").fetchall()]
    sets = attach_muscles(c, c.execute("SELECT * FROM sets ORDER BY id").fetchall())
    bw = [dict(r) for r in c.execute("SELECT * FROM bodyweight ORDER BY date, id").fetchall()]
    payload = json.dumps({"exported": datetime.now().isoformat(timespec="seconds"), "workouts": workouts, "sets": sets, "bodyweight": bw}).encode()
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
            "SELECT weight, reps FROM sets WHERE exercise = ? ORDER BY id DESC LIMIT 1", (r["exercise"],)
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
    )


def main():
    if len(sys.argv) < 2:
        usage()
    cmd = sys.argv[1]
    rest = sys.argv[2:]
    if cmd == "start":
        cmd_start(" ".join(rest))
    elif cmd == "log" and len(rest) >= 3:
        exercise, weight, reps = rest[0], rest[1], rest[2]
        note_parts = []
        muscles = ""
        bodyweight = False
        for tok in rest[3:]:
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
        cmd_end(" ".join(rest))
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
