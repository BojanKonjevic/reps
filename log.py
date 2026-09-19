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
    weight = float(weight)
    reps = int(reps)
    if weight < 0:
        sys.exit("weight cannot be negative")
    if reps <= 0:
        sys.exit("reps must be a positive integer")
    muscles = clean_muscles(muscles)

    mapping = c.execute("SELECT is_bodyweight_only FROM lift_muscle_map WHERE exercise = ?", (exercise,)).fetchone()
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
        muscles = c.execute("SELECT muscles FROM lift_muscle_map WHERE exercise = ?", (exercise,)).fetchone()["muscles"]
    elif bodyweight and mapping["is_bodyweight_only"] != 1:
        c.execute("UPDATE lift_muscle_map SET is_bodyweight_only = 1 WHERE exercise = ?", (exercise,))

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
        c.execute("DELETE FROM set_muscles WHERE set_id = ?", (set_id,))
        for muscle in value.split(","):
            c.execute("INSERT INTO set_muscles (set_id, muscle) VALUES (?, ?)", (set_id, muscle))
    if field == "weight":
        if value == "":
            sys.exit("weight cannot be empty, pass a number or delete the set")
        value = float(value)
        if value < 0:
            sys.exit("weight cannot be negative")
        # Validate zero-weight against exercise type
        row = c.execute("SELECT exercise FROM sets WHERE id = ?", (set_id,)).fetchone()
        if row and value == 0:
            mapping = c.execute("SELECT is_bodyweight_only FROM lift_muscle_map WHERE exercise = ?", (row["exercise"],)).fetchone()
            if not mapping or mapping["is_bodyweight_only"] != 1:
                sys.exit(f"zero weight not allowed for '{row['exercise']}' (not a bodyweight-only exercise)")
    if field == "reps":
        value = int(value)
        if value <= 0:
            sys.exit("reps must be a positive integer")
    if field == "exercise":
        mapping = c.execute("SELECT muscles FROM lift_muscle_map WHERE exercise = ?", (value,)).fetchone()
        if not mapping:
            sys.exit(f"exercise '{value}' has no mapping in lift_muscle_map (run retag first)")
        c.execute("DELETE FROM set_muscles WHERE set_id = ?", (set_id,))
        for muscle in mapping["muscles"].split(","):
            c.execute("INSERT INTO set_muscles (set_id, muscle) VALUES (?, ?)", (set_id, muscle))
    if field != "muscles":
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
    c = conn()
    rows = c.execute(
        "SELECT s.*, w.date FROM sets s JOIN workouts w ON w.id = s.workout_id WHERE s.exercise = ? ORDER BY s.id DESC LIMIT ?",
        (exercise.strip().lower(), int(limit)),
    ).fetchall()
    print(json.dumps(attach_muscles(c, rows), indent=2))


def cmd_stats():
    c = conn()
    workouts = c.execute("SELECT id, date, status FROM workouts ORDER BY date").fetchall()
    out = {"workouts": len([w for w in workouts if w["status"] != "rest"]), "by_exercise": {}}
    rows = c.execute("SELECT exercise, COUNT(*) n, MAX(weight * (1 + reps / 30.0)) max_e1rm, MAX(weight) max_w FROM sets GROUP BY exercise").fetchall()

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
    kg = float(kg)
    if kg <= 0:
        sys.exit("bodyweight must be positive")
    cur = c.execute("INSERT INTO bodyweight (date, kg, note) VALUES (?, ?, ?)", (today, kg, note))
    c.commit()
    print(json.dumps({"weigh_id": cur.lastrowid, "date": today, "kg": kg}))


def cmd_restore():
    sql_file = os.path.join(os.path.dirname(DB), "workouts.sql")
    if not os.path.exists(sql_file):
        sys.exit("no workouts.sql found, cannot restore")
    import sqlite3
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.executescript("""
        DROP TABLE IF EXISTS set_muscles;
        DROP TABLE IF EXISTS sets;
        DROP TABLE IF EXISTS workouts;
        DROP TABLE IF EXISTS bodyweight;
        DROP TABLE IF EXISTS lift_muscle_map;
    """)
    c.commit()
    with open(sql_file, 'r') as f:
        c.executescript(f.read())
    c.commit()
    print(json.dumps({"restored": True, "from": sql_file}))


def parse_mev_from_science():
    """Parse MEV (minimum effective volume) bounds from SCIENCE.md.

    Primary source is the fenced ````json mev-bounds`` block in SCIENCE.md,
    which survives prose and table reformatting. The legacy volume-landmarks
    table parse is kept as a fallback for files predating the JSON block.
    """
    name_map = {
        'chest': 'chest',
        'back': 'back',
        'front delt': 'front delt',
        'side delt': 'side delt',
        'rear delt': 'rear delt',
        'biceps': 'biceps',
        'triceps': 'triceps',
        'quads': 'quads',
        'hamstrings': 'hamstrings',
        'glutes': 'glutes',
        'abs': 'abs',
        'forearms': 'forearms',
        'adductors': 'adductors',
    }
    expected = set(name_map.values())
    opinion_fallback = {'forearms': 6, 'adductors': 4}
    mev_bounds: dict = {}
    try:
        with open(SCIENCE_FILE, 'r') as f:
            content = f.read()
    except OSError:
        content = ""
    if not content:
        print("WARNING: parse_mev_from_science could not read SCIENCE.md, using fallback bounds only")
    else:
        block = re.search(r'```json[^\n]*mev[^\n]*\n(.*?)```', content, re.DOTALL | re.IGNORECASE)
        if block:
            try:
                raw = json.loads(block.group(1))
            except ValueError as e:
                print(f"WARNING: parse_mev_from_science found mev-bounds JSON block but failed to parse it ({e}), falling back to table")
                raw = None
            if raw is not None:
                if not isinstance(raw, dict):
                    print("WARNING: parse_mev_from_science mev-bounds block is not a JSON object, falling back to table")
                else:
                    invalid = {}
                    for k, v in raw.items():
                        muscle = k.strip().lower() if isinstance(k, str) else k
                        if muscle in expected and isinstance(v, int) and not isinstance(v, bool) and v >= 0:
                            mev_bounds[muscle] = v
                        else:
                            invalid[k] = v
                    if invalid:
                        print(f"WARNING: parse_mev_from_science ignoring invalid mev-bounds entries: {invalid}")
                    missing_json = expected - set(mev_bounds.keys())
                    if missing_json:
                        print(f"WARNING: parse_mev_from_science mev-bounds block missing: {missing_json}, filling from table/fallback")
        else:
            print("WARNING: parse_mev_from_science found no mev-bounds JSON block, falling back to table parse")
        if len(mev_bounds) < len(expected):
            try:
                in_volume_section = False
                for line in content.split('\n'):
                    if line.strip().startswith('## Volume landmarks'):
                        in_volume_section = True
                        continue
                    if in_volume_section and line.strip().startswith('## '):
                        in_volume_section = False
                        break
                    if in_volume_section and line.strip().startswith('| ') and not line.strip().startswith('|' + '-' * 3):
                        parts = [p.strip() for p in line.split('|')]
                        if len(parts) >= 4 and parts[1] and parts[2]:
                            muscle = parts[1].lower()
                            mev_str = parts[2]
                            mev_match = re.match(r'(\d+)', mev_str)
                            if mev_match and muscle in name_map and name_map[muscle] not in mev_bounds:
                                mev_bounds[name_map[muscle]] = int(mev_match.group(1))
            except ValueError:
                pass
    for muscle, fallback in opinion_fallback.items():
        mev_bounds.setdefault(muscle, fallback)
    if len(mev_bounds) < len(name_map):
        missing = set(name_map.values()) - set(mev_bounds.keys())
        print(f"WARNING: parse_mev_from_science parsed {len(mev_bounds)}/{len(name_map)} muscles; missing: {missing}")
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
    """).fetchall()
    for d in drift:
        logged_set = set(d['logged'].split(',')) if d['logged'] else set()
        mapped_set = set(d['mapped'].split(',')) if d['mapped'] else set()
        if logged_set != mapped_set:
            flags.append({"check": "muscle_drift", "severity": "medium", "evidence": f"set {d['id']} ({d['exercise']}): logged {d['logged']} vs mapped {d['mapped']}", "fix": "retag <exercise> <muscles> or update Lift mapping"})

    # Check 4: Implausible progression jumps
    # Deterministic proxy for AUDIT.md check 4: the per-type SCIENCE.md bounds need
    # training age, which the db does not track, so flag only jumps exceeding the
    # loosest plausible rate (novice compound 2% for multi-muscle lifts, isolation
    # 1.5% for single-muscle lifts). Jumps explained by set/workout notes are skipped.
    sets = c.execute("""
        SELECT s.id, s.exercise, s.weight, s.reps, w.date, s.note AS set_note, w.notes AS workout_notes,
               s.weight * (1 + s.reps / 30.0) as e1rm
        FROM sets s JOIN workouts w ON w.id = s.workout_id
        WHERE s.weight > 0 ORDER BY s.exercise, w.date, s.id
    """).fetchall()

    by_ex = {}
    for s in sets:
        by_ex.setdefault(s["exercise"], []).append(s)

    explained = ("deload", "return", "program change", "injury", "technique", "sick", "travel")

    for ex, ex_sets in by_ex.items():
        by_date = {}
        notes_by_date = {}
        for s in ex_sets:
            d = s["date"]
            if d not in by_date or s["e1rm"] > by_date[d]:
                by_date[d] = s["e1rm"]
            blob = ((s["set_note"] or "") + " " + (s["workout_notes"] or "")).lower()
            notes_by_date[d] = (notes_by_date.get(d, "") + " " + blob).strip()
        dates = sorted(by_date.keys())
        row = c.execute("SELECT muscles FROM lift_muscle_map WHERE exercise = ?", (ex,)).fetchone()
        groups = len((row["muscles"] or "").split(",")) if row and row["muscles"] else 1
        bound = 2.0 if groups > 1 else 1.5
        for i in range(1, len(dates)):
            prev = by_date[dates[i-1]]
            curr = by_date[dates[i]]
            if prev > 0:
                pct = (curr - prev) / prev * 100
                if pct > bound:
                    if any(k in notes_by_date.get(dates[i-1], "") or k in notes_by_date.get(dates[i], "") for k in explained):
                        continue
                    flags.append({"check": "progression_jump", "severity": "high", "evidence": f"{ex}: {prev:.1f} -> {curr:.1f} e1RM ({pct:.1f}% jump, bound {bound}%) on {dates[i]}", "fix": "verify data entry, add explanatory note, or update weight/reps"})

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
    cur = c.execute("UPDATE sets SET exercise = ? WHERE exercise = ?", (new, old))
    renamed = cur.rowcount
    mapping = c.execute("SELECT muscles, is_bodyweight_only FROM lift_muscle_map WHERE exercise = ?", (old,)).fetchone()
    map_moved = False
    if mapping:
        c.execute("INSERT OR REPLACE INTO lift_muscle_map (exercise, muscles, is_bodyweight_only) VALUES (?, ?, ?)",
                  (new, mapping["muscles"], mapping["is_bodyweight_only"]))
        c.execute("DELETE FROM lift_muscle_map WHERE exercise = ?", (old,))
        map_moved = True
    c.commit()
    print(json.dumps({"renamed": renamed, "map_moved": map_moved}))


def cmd_retag(exercise, muscles, bodyweight=False):
    c = conn()
    exercise = exercise.strip().lower()
    muscles = clean_muscles(muscles)
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
    if field == "status" and value not in ("open", "done", "rest"):
        sys.exit("status must be open, done or rest")
    c = conn()
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
    day = date.fromisoformat(datestr).isoformat()
    c = conn()
    wrows = c.execute("SELECT * FROM workouts WHERE date = ? ORDER BY id", (day,)).fetchall()
    out = []
    for w in wrows:
        sets = c.execute("SELECT * FROM sets WHERE workout_id = ? ORDER BY id", (w["id"],)).fetchall()
        out.append({"workout": dict(w), "sets": attach_muscles(c, sets)})
    print(json.dumps({"date": day, "workouts": out}, indent=2))


def cmd_range(fromstr, tostr):
    d0 = date.fromisoformat(fromstr).isoformat()
    d1 = date.fromisoformat(tostr).isoformat()
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
            "SELECT weight, reps, weight * (1 + reps / 30.0) AS e1rm FROM sets WHERE exercise = ? ORDER BY e1rm DESC LIMIT 1", (r["exercise"],)
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
         "| stats | export | rename <old> <new> | context [n] | weigh <kg> [note] | sync [force] | restore | audit | rest [yyyy-mm-dd] [note]"
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
        cmd_restore()
    elif cmd == "audit":
        cmd_audit()
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
