#!/usr/bin/env python3
"""reps: dumb store for workout logs. No domain logic, agent owns meaning."""

import json
import os
import sqlite3
import sys
import urllib.request
from datetime import date, datetime

DB = os.environ.get("REPS_DB", os.path.join(os.path.dirname(os.path.abspath(__file__)), "workouts.db"))
CFG = os.path.join(os.path.expanduser("~"), ".config", "reps", "config.json")

SCHEMA = """
CREATE TABLE IF NOT EXISTS workouts (
  id INTEGER PRIMARY KEY,
  date TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open',
  notes TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS sets (
  id INTEGER PRIMARY KEY,
  workout_id INTEGER NOT NULL REFERENCES workouts(id),
  exercise TEXT NOT NULL,
  weight REAL NOT NULL,
  reps INTEGER NOT NULL,
  rpe REAL,
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
"""


def conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.executescript(SCHEMA)
    return c


def open_workout(c):
    row = c.execute("SELECT * FROM workouts WHERE status = 'open' ORDER BY id DESC LIMIT 1").fetchone()
    return row


def cmd_start(note):
    c = conn()
    existing = open_workout(c)
    if existing:
        print(json.dumps({"workout_id": existing["id"], "reused": True, "date": existing["date"]}))
        return
    today = date.today().isoformat()
    cur = c.execute("INSERT INTO workouts (date, status, notes) VALUES (?, 'open', ?)", (today, note))
    c.commit()
    print(json.dumps({"workout_id": cur.lastrowid, "reused": False, "date": today}))


def cmd_log(exercise, weight, reps, rpe, note):
    c = conn()
    w = open_workout(c)
    if not w:
        today = date.today().isoformat()
        cur = c.execute("INSERT INTO workouts (date, status, notes) VALUES (?, 'open', '')", (today,))
        wid = cur.lastrowid
    else:
        wid = w["id"]
    created = datetime.now().isoformat(timespec="seconds")
    cur = c.execute(
        "INSERT INTO sets (workout_id, exercise, weight, reps, rpe, note, created) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (wid, exercise.strip().lower(), float(weight), int(reps), rpe, note, created),
    )
    c.commit()
    print(json.dumps({"set_id": cur.lastrowid, "workout_id": wid}))


def cmd_update(set_id, field, value):
    allowed = {"weight", "reps", "rpe", "exercise", "note"}
    if field not in allowed:
        sys.exit("field must be one of weight reps rpe exercise note")
    c = conn()
    if field == "exercise":
        value = value.strip().lower()
    if field == "weight" or field == "rpe":
        value = float(value) if value != "" else None
    if field == "reps":
        value = int(value)
    c.execute(f"UPDATE sets SET {field} = ? WHERE id = ?", (value, int(set_id)))
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


def cmd_sync():
    try:
        cfg = json.load(open(CFG))
        url, secret = cfg["url"], cfg["secret"]
    except (OSError, KeyError, ValueError):
        sys.exit("no sync config, expected url and secret in " + CFG)
    c = conn()
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


def cmd_rename(old, new):
    c = conn()
    cur = c.execute("UPDATE sets SET exercise = ? WHERE exercise = ?", (new.strip().lower(), old.strip().lower()))
    c.commit()
    print(json.dumps({"renamed": cur.rowcount}))


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
            "SELECT weight, reps, rpe FROM sets WHERE exercise = ? ORDER BY id DESC LIMIT 1", (r["exercise"],)
        ).fetchone()
        best.append({"exercise": r["exercise"], "sets": r["n"], "max_weight": r["max_w"], "last": dict(last) if last else None})
    totals = c.execute("SELECT COUNT(*) w FROM workouts").fetchone()
    bw = [dict(r) for r in c.execute("SELECT date, kg, note FROM bodyweight ORDER BY date DESC, id DESC LIMIT 5").fetchall()]
    print(json.dumps({"recent": recent, "lifts": best, "workouts_total": totals["w"], "bodyweight_last": bw}, indent=2))


def usage():
    sys.exit(
        "usage: log.py start [note] | log <exercise> <weight> <reps> [rpe=N] [note] "
        "| update <id> <field> <value> | end [note] | today | exercises | history <ex> [limit] "
        "| stats | export | rename <old> <new> | context [n] | weigh <kg> [note] | sync"
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
        rpe = None
        note_parts = []
        for tok in rest[3:]:
            if tok.startswith("rpe="):
                rpe = float(tok.split("=", 1)[1])
            else:
                note_parts.append(tok)
        cmd_log(exercise, weight, reps, rpe, " ".join(note_parts))
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
    elif cmd == "context":
        lim = rest[0] if len(rest) > 0 else "3"
        cmd_context(lim)
    elif cmd == "weigh" and len(rest) >= 1:
        cmd_weigh(rest[0], " ".join(rest[1:]))
    elif cmd == "sync":
        cmd_sync()
    else:
        usage()


if __name__ == "__main__":
    main()
