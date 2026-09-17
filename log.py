#!/usr/bin/env python3
"""reps: dumb store for workout logs. No domain logic, agent owns meaning."""

import json
import os
import re
import sqlite3
import sys
import urllib.request
from datetime import date, datetime

DB = os.environ.get("REPS_DB", os.path.join(os.path.dirname(os.path.abspath(__file__)), "workouts.db"))
CFG = os.path.join(os.path.expanduser("~"), ".config", "reps", "config.json")
SCIENCE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "SCIENCE.md")

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
CREATE TABLE IF NOT EXISTS schema_version (
  version INTEGER PRIMARY KEY,
  applied_at TEXT NOT NULL DEFAULT (datetime('now'))
);
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
CURRENT_SCHEMA_VERSION = 2


# Migration functions - each takes a connection and performs one schema version upgrade
def _migrate_v1_to_v2(c):
    """Migration v2: create set_muscles table and populate from muscles column"""
    c.execute("""
        INSERT INTO set_muscles (set_id, muscle)
        SELECT sets.id, trim(value) FROM sets, json_each('["' || replace(muscles, ',', '","') || '"]')
        WHERE muscles != ''
    """)


MIGRATIONS = {
    1: _migrate_v1_to_v2,
}


def _run_migrations(c):
    """Run pending schema migrations in order."""
    cur = c.execute("SELECT COALESCE(MAX(version), 0) FROM schema_version")
    current = cur.fetchone()[0]
    for version in range(current + 1, CURRENT_SCHEMA_VERSION + 1):
        if version in MIGRATIONS:
            MIGRATIONS[version](c)
        c.execute("INSERT INTO schema_version (version) VALUES (?)", (version,))
        c.commit()


def conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA foreign_keys=ON")
    c.executescript(SCHEMA)
    # Ensure muscles column exists before migrations that depend on it
    try:
        c.execute("ALTER TABLE sets ADD COLUMN muscles TEXT NOT NULL DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    _run_migrations(c)
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


def cmd_log(exercise, weight, reps, note, muscles):
    c = conn()
    w = open_workout(c)
    if not w:
        sys.exit("no open workout, run start first (workouts are only created explicitly)")
    exercise = exercise.strip().lower()
    weight = float(weight)
    reps = int(reps)
    muscles = clean_muscles(muscles)

    # Validation: zero-weight sets only allowed for bodyweight exercises
    mapping = c.execute("SELECT is_bodyweight_only FROM lift_muscle_map WHERE exercise = ?", (exercise,)).fetchone()
    if weight == 0:
        if not mapping or mapping["is_bodyweight_only"] != 1:
            sys.exit(f"zero weight not allowed for '{exercise}' (not a bodyweight-only exercise)")

    # Validation: muscles required if no mapping exists
    if not mapping:
        if not muscles:
            sys.exit(f"muscles= required for new exercise '{exercise}' (no mapping in lift_muscle_map)")
        # Auto-create mapping for new exercise
        # Agent must specify is_bodyweight_only via retag or external tool; default to 0
        c.execute("INSERT INTO lift_muscle_map (exercise, muscles, is_bodyweight_only) VALUES (?, ?, ?)",
                  (exercise, muscles, 0))
    elif not muscles:
        # Use stored mapping
        muscles = c.execute("SELECT muscles FROM lift_muscle_map WHERE exercise = ?", (exercise,)).fetchone()["muscles"]

    wid = w["id"]
    created = datetime.now().isoformat(timespec="seconds")
    cur = c.execute(
        "INSERT INTO sets (workout_id, exercise, weight, reps, note, created, muscles) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (wid, exercise, weight, reps, note, created, muscles),
    )
    set_id = cur.lastrowid
    # Populate set_muscles junction table
    for muscle in muscles.split(","):
        c.execute("INSERT INTO set_muscles (set_id, muscle) VALUES (?, ?)", (set_id, muscle))
    c.commit()
    print(json.dumps({"set_id": set_id, "workout_id": wid}))


def cmd_update(set_id, field, value):
    allowed = {"weight", "reps", "exercise", "note", "muscles"}
    if field not in allowed:
        sys.exit("field must be one of weight reps exercise note muscles")
    c = conn()
    if field == "exercise":
        value = value.strip().lower()
    if field == "muscles":
        value = clean_muscles(value)
    if field == "muscles":
        # Update set_muscles junction table
        c.execute("DELETE FROM set_muscles WHERE set_id = ?", (set_id,))
        for muscle in value.split(","):
            c.execute("INSERT INTO set_muscles (set_id, muscle) VALUES (?, ?)", (set_id, muscle))
    if field == "weight":
        if value == "":
            sys.exit("weight cannot be empty, pass a number or delete the set")
        value = float(value)
        # Validate zero-weight against exercise type
        row = c.execute("SELECT exercise FROM sets WHERE id = ?", (set_id,)).fetchone()
        if row and value == 0:
            mapping = c.execute("SELECT is_bodyweight_only FROM lift_muscle_map WHERE exercise = ?", (row["exercise"],)).fetchone()
            if not mapping or mapping["is_bodyweight_only"] != 1:
                sys.exit(f"zero weight not allowed for '{row['exercise']}' (not a bodyweight-only exercise)")
    if field == "reps":
        value = int(value)
    if field == "exercise":
        # Validate new exercise has mapping or muscles provided elsewhere
        mapping = c.execute("SELECT muscles FROM lift_muscle_map WHERE exercise = ?", (value,)).fetchone()
        if not mapping:
            sys.exit(f"exercise '{value}' has no mapping in lift_muscle_map (run retag first)")
    c.execute("UPDATE sets SET {} = ? WHERE id = ?".format(field), (value, int(set_id)))
    c.commit()
    print(json.dumps({"updated": int(set_id)}))


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
    print(json.dumps({"closed": w["id"]}))


def cmd_today():
    c = conn()
    w = open_workout(c)
    if not w:
        print(json.dumps({"open": False}))
        return
    sets = c.execute("SELECT * FROM sets WHERE workout_id = ? ORDER BY id", (w["id"],)).fetchall()
    print(json.dumps({"open": True, "workout": dict(w), "sets": [dict(s) for s in sets]}, indent=2))


def cmd_exercises():
    c = conn()
    rows = c.execute("SELECT DISTINCT exercise FROM sets ORDER BY exercise").fetchall()
    print(json.dumps([r["exercise"] for r in rows], indent=2))


def cmd_history(exercise, limit):
    c = conn()
    rows = c.execute(
        "SELECT s.*, w.date FROM sets s JOIN workouts w ON w.id = s.workout_id WHERE s.exercise = ? ORDER BY s.id DESC LIMIT ?",
        (exercise.strip().lower(), int(limit)),
    ).fetchall()
    print(json.dumps([dict(r) for r in rows], indent=2))


def cmd_stats():
    c = conn()
    workouts = c.execute("SELECT id, date, status FROM workouts ORDER BY date").fetchall()
    out = {"workouts": len(workouts), "by_exercise": {}}
    rows = c.execute("SELECT exercise, COUNT(*) n, MAX(weight) max_w FROM sets GROUP BY exercise").fetchall()
    for r in rows:
        out["by_exercise"][r["exercise"]] = {"sets": r["n"], "max_weight": r["max_w"]}
    print(json.dumps(out, indent=2))


def cmd_export():
    c = conn()
    workouts = [dict(r) for r in c.execute("SELECT * FROM workouts ORDER BY id").fetchall()]
    sets = [dict(r) for r in c.execute("SELECT * FROM sets ORDER BY id").fetchall()]
    bw = [dict(r) for r in c.execute("SELECT * FROM bodyweight ORDER BY date, id").fetchall()]
    print(json.dumps({"exported": datetime.now().isoformat(timespec="seconds"), "workouts": workouts, "sets": sets, "bodyweight": bw}, indent=2))


def cmd_weigh(kg, note):
    c = conn()
    today = date.today().isoformat()
    cur = c.execute("INSERT INTO bodyweight (date, kg, note) VALUES (?, ?, ?)", (today, float(kg), note))
    c.commit()
    print(json.dumps({"weigh_id": cur.lastrowid, "date": today, "kg": float(kg)}))


def cmd_restore():
    sql_file = os.path.join(os.path.dirname(DB), "workouts.sql")
    if not os.path.exists(sql_file):
        sys.exit("no workouts.sql found, cannot restore")
    # Use a fresh connection without schema init
    import sqlite3
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    # Drop all tables before restoring
    c.executescript("""
        DROP TABLE IF EXISTS sets;
        DROP TABLE IF EXISTS workouts;
        DROP TABLE IF EXISTS bodyweight;
        DROP TABLE IF EXISTS lift_muscle_map;
        DROP TABLE IF EXISTS schema_version;
    """)
    c.commit()
    with open(sql_file, 'r') as f:
        c.executescript(f.read())
    c.commit()
    print(json.dumps({"restored": True, "from": sql_file}))


def parse_mev_from_science():
    """Parse MEV (minimum effective volume) bounds from SCIENCE.md."""
    mev_bounds = {}
    # Normalize muscle names from SCIENCE.md to match database convention
    name_map = {
        'chest': 'chest',
        'back': 'back',
        'shoulders (side delt)': 'shoulders',
        'biceps': 'biceps',
        'triceps': 'triceps',
        'quads': 'quads',
        'hamstrings': 'hamstrings',
        'glutes': 'glutes',
        'abs': 'abs',
    }
    try:
        with open(SCIENCE_FILE, 'r') as f:
            content = f.read()
        in_volume_section = False
        for line in content.split('\n'):
            if line.strip().startswith('## Volume landmarks'):
                in_volume_section = True
                continue
            if in_volume_section and line.strip().startswith('## '):
                in_volume_section = False
                break
            if in_volume_section and line.strip().startswith('| ') and not line.strip().startswith('|---'):
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 4 and parts[1] and parts[2]:
                    muscle = parts[1].lower()
                    mev_str = parts[2]
                    mev_match = re.match(r'(\d+)', mev_str)
                    if mev_match and muscle in name_map:
                        mev_bounds[name_map[muscle]] = int(mev_match.group(1))
    except (OSError, ValueError):
        pass
    return mev_bounds


def cmd_audit():
    """Run deterministic audit checks and output flagged items."""
    c = conn()
    import itertools
    
    def levenshtein(a, b):
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
        HAVING logged != m.muscles
    """).fetchall()
    for d in drift:
        flags.append({"check": "muscle_drift", "severity": "medium", "evidence": f"set {d['id']} ({d['exercise']}): logged {d['logged']} vs mapped {d['mapped']}", "fix": "retag <exercise> <muscles> or update Lift mapping"})
    
    # Check 4: Implausible progression jumps
    sets = c.execute("""
        SELECT s.id, s.exercise, s.weight, s.reps, w.date,
               s.weight * (1 + s.reps / 30.0) as e1rm
        FROM sets s JOIN workouts w ON w.id = s.workout_id
        WHERE s.weight > 0 ORDER BY s.exercise, w.date, s.id
    """).fetchall()
    
    by_ex = {}
    for s in sets:
        by_ex.setdefault(s["exercise"], []).append(s)
    
    for ex, ex_sets in by_ex.items():
        # Group by date
        by_date = {}
        for s in ex_sets:
            d = s["date"]
            if d not in by_date or s["e1rm"] > by_date[d]:
                by_date[d] = s["e1rm"]
        dates = sorted(by_date.keys())
        for i in range(1, len(dates)):
            prev = by_date[dates[i-1]]
            curr = by_date[dates[i]]
            if prev > 0:
                pct = (curr - prev) / prev * 100
                if pct > 1.0:  # intermediate compound bound from SCIENCE.md
                    flags.append({"check": "progression_jump", "severity": "high", "evidence": f"{ex}: {prev:.1f} -> {curr:.1f} e1RM ({pct:.1f}% jump) on {dates[i]}", "fix": "verify data entry, add explanatory note, or update weight/reps"})
    
    # Check 1: Exercise name duplicates
    exercises = [r["exercise"] for r in c.execute("SELECT DISTINCT exercise FROM sets").fetchall()]
    for a, b in itertools.combinations(exercises, 2):
        if levenshtein(a, b) <= 2:
            flags.append({"check": "duplicate_names", "severity": "low", "evidence": f"'{a}' vs '{b}' (Levenshtein <= 2)", "fix": "rename <old> <new>"})
    
    # Check 7: Stale open workouts
    stale = c.execute("""
        SELECT w.id, w.date FROM workouts w
        WHERE w.status = 'open'
          AND (date(w.date) < date('now') OR 
               (SELECT MAX(created) FROM sets WHERE workout_id = w.id) < datetime('now', '-8 hours'))
    """).fetchall()
    for s in stale:
        flags.append({"check": "stale_workout", "severity": "high", "evidence": f"workout {s['id']} from {s['date']} still open", "fix": "end with note, or delete-workout if empty"})
    
    # Check 8: Volume vs MEV
    from datetime import date, timedelta
    base = date.today() - timedelta(weeks=10)
    mev_bounds = parse_mev_from_science()
    for muscle, mev in mev_bounds.items():
        weeks = c.execute("""
            SELECT strftime('%Y-%W', w.date) as week, COUNT(*) as sets
            FROM sets s 
            JOIN workouts w ON w.id = s.workout_id
            JOIN set_muscles sm ON sm.set_id = s.id
            WHERE sm.muscle = ? AND date(w.date) >= ?
            GROUP BY week ORDER BY week
        """, (muscle, base.isoformat())).fetchall()
        low_weeks = sum(1 for w in weeks if w["sets"] < mev)
        if low_weeks >= 4:
            flags.append({"check": "volume_below_mev", "severity": "medium", "evidence": f"{muscle}: {low_weeks} of last {len(weeks)} weeks below MEV ({mev})", "fix": "add volume, or add Active rule explaining"})
    
    # Output report
    print(f"Audit complete: {len(flags)} flags")
    for i, f in enumerate(flags, 1):
        print(f"{i}. [{f['check']}] — {f['severity'].upper()}")
        print(f"   Evidence: {f['evidence']}")
        print(f"   Fix: {f['fix']}")
    print(json.dumps({"flags": flags}))


def cmd_sync():
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
    workouts = [dict(r) for r in c.execute("SELECT * FROM workouts ORDER BY id").fetchall()]
    sets = [dict(r) for r in c.execute("SELECT * FROM sets ORDER BY id").fetchall()]
    bw = [dict(r) for r in c.execute("SELECT * FROM bodyweight ORDER BY date, id").fetchall()]
    payload = json.dumps({"exported": datetime.now().isoformat(timespec="seconds"), "workouts": workouts, "sets": sets, "bodyweight": bw}).encode()
    req = urllib.request.Request(url + "/sync", data=payload, method="PUT",
                                 headers={"Content-Type": "application/json", "Authorization": "Bearer " + secret,
                                          "User-Agent": "reps-sync/1"})
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            print(json.dumps({"synced": True, "bytes": len(payload), "reply": json.loads(res.read().decode())}))
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
    cur = c.execute("UPDATE sets SET exercise = ? WHERE exercise = ?", (new.strip().lower(), old.strip().lower()))
    c.commit()
    print(json.dumps({"renamed": cur.rowcount}))


def cmd_retag(exercise, muscles, bodyweight=False):
    c = conn()
    exercise = exercise.strip().lower()
    muscles = clean_muscles(muscles)
    # Preserve existing is_bodyweight_only if mapping exists, default to 0
    existing = c.execute("SELECT is_bodyweight_only FROM lift_muscle_map WHERE exercise = ?", (exercise,)).fetchone()
    is_bw = existing["is_bodyweight_only"] if existing else 0
    if bodyweight:
        is_bw = 1
    cur = c.execute("UPDATE sets SET muscles = ? WHERE exercise = ?", (muscles, exercise))
    # Update set_muscles for all affected sets
    c.execute("DELETE FROM set_muscles WHERE set_id IN (SELECT id FROM sets WHERE exercise = ?)", (exercise,))
    for set_row in c.execute("SELECT id FROM sets WHERE exercise = ?", (exercise,)).fetchall():
        set_id = set_row["id"]
        for muscle in muscles.split(","):
            c.execute("INSERT INTO set_muscles (set_id, muscle) VALUES (?, ?)", (set_id, muscle))
    c.execute("INSERT OR REPLACE INTO lift_muscle_map (exercise, muscles, is_bodyweight_only) VALUES (?, ?, ?)",
              (exercise, muscles, is_bw))
    c.commit()
    print(json.dumps({"retag_exercise": exercise, "updated": cur.rowcount, "is_bodyweight_only": is_bw}))


def cmd_delete_set(set_id):
    c = conn()
    row = c.execute("SELECT s.*, w.date FROM sets s JOIN workouts w ON w.id = s.workout_id WHERE s.id = ?", (int(set_id),)).fetchone()
    if not row:
        sys.exit("no such set")
    c.execute("DELETE FROM sets WHERE id = ?", (int(set_id),))
    c.commit()
    print(json.dumps({"deleted": int(set_id), "workout_id": row["workout_id"], "date": row["date"],
                      "was": {"exercise": row["exercise"], "weight": row["weight"], "reps": row["reps"]}}))


def cmd_delete_workout(workout_id):
    c = conn()
    row = c.execute("SELECT * FROM workouts WHERE id = ?", (int(workout_id),)).fetchone()
    if not row:
        sys.exit("no such workout")
    n = c.execute("SELECT COUNT(*) n FROM sets WHERE workout_id = ?", (int(workout_id),)).fetchone()["n"]
    c.execute("DELETE FROM sets WHERE workout_id = ?", (int(workout_id),))
    c.execute("DELETE FROM workouts WHERE id = ?", (int(workout_id),))
    c.commit()
    print(json.dumps({"deleted_workout": int(workout_id), "date": row["date"], "deleted_sets": n}))


def cmd_update_workout(workout_id, field, value):
    allowed = {"notes", "date", "status"}
    if field not in allowed:
        sys.exit("field must be one of notes date status")
    if field == "date":
        try:
            date.fromisoformat(value)
        except ValueError:
            sys.exit("date must be YYYY-MM-DD")
    if field == "status" and value not in ("open", "done"):
        sys.exit("status must be open or done")
    c = conn()
    cur = c.execute(f"UPDATE workouts SET {field} = ? WHERE id = ?", (value, int(workout_id)))
    if cur.rowcount == 0:
        sys.exit("no such workout")
    c.commit()
    print(json.dumps({"updated_workout": int(workout_id), "field": field}))


def cmd_session(datestr):
    day = date.fromisoformat(datestr).isoformat()
    c = conn()
    wrows = c.execute("SELECT * FROM workouts WHERE date = ? ORDER BY id", (day,)).fetchall()
    out = []
    for w in wrows:
        sets = c.execute("SELECT * FROM sets WHERE workout_id = ? ORDER BY id", (w["id"],)).fetchall()
        out.append({"workout": dict(w), "sets": [dict(s) for s in sets]})
    print(json.dumps({"date": day, "workouts": out}, indent=2))


def cmd_range(fromstr, tostr):
    d0 = date.fromisoformat(fromstr).isoformat()
    d1 = date.fromisoformat(tostr).isoformat()
    c = conn()
    wrows = c.execute("SELECT * FROM workouts WHERE date >= ? AND date <= ? ORDER BY date, id", (d0, d1)).fetchall()
    out = []
    for w in wrows:
        sets = c.execute("SELECT * FROM sets WHERE workout_id = ? ORDER BY id", (w["id"],)).fetchall()
        out.append({"workout": dict(w), "sets": [dict(s) for s in sets]})
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
        recent.append({"workout": dict(w), "sets": [dict(s) for s in sets]})
    best = []
    for r in c.execute("SELECT exercise, COUNT(*) n, MAX(weight) max_w FROM sets GROUP BY exercise ORDER BY exercise").fetchall():
        last = c.execute(
            "SELECT weight, reps FROM sets WHERE exercise = ? ORDER BY id DESC LIMIT 1", (r["exercise"],)
        ).fetchone()
        best.append({"exercise": r["exercise"], "sets": r["n"], "max_weight": r["max_w"], "last": dict(last) if last else None})
    totals = c.execute("SELECT COUNT(*) w FROM workouts").fetchone()
    bw = [dict(r) for r in c.execute("SELECT date, kg, note FROM bodyweight ORDER BY date DESC, id DESC LIMIT 5").fetchall()]
    print(json.dumps({"recent": recent, "lifts": best, "workouts_total": totals["w"], "bodyweight_last": bw}, indent=2))


def usage():
    sys.exit(
        "usage: log.py start [note] | log <exercise> <weight> <reps> [note] [muscles=a,b] "
        "| update <id> <field> <value> | update-workout <id> <field> <value> | retag <exercise> <muscles> "
        "| delete-set <id> | delete-workout <id> | end [note] | today | exercises | history <ex> [limit] "
        "| session <yyyy-mm-dd> | range <from> <to> | notes [limit] | calendar "
        "| stats | export | rename <old> <new> | context [n] | weigh <kg> [note] | sync | restore | audit"
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
        for tok in rest[3:]:
            if tok.startswith("muscles="):
                muscles = tok[len("muscles="):]
                continue
            note_parts.append(tok)
        cmd_log(exercise, weight, reps, " ".join(note_parts), muscles)
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
        bodyweight = "--bodyweight" in rest
        rest = [r for r in rest if r != "--bodyweight"]
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
        cmd_sync()
    elif cmd == "restore":
        cmd_restore()
    elif cmd == "audit":
        cmd_audit()
    else:
        usage()


if __name__ == "__main__":
    main()
