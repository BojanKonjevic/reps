import json
import os
import re
import sqlite3
import sys
import urllib.error
import urllib.request
from datetime import datetime

from . import db
from .adherence import adherence_snapshot
from .autoreg import autoreg_block
from .constants import load_constants
from .models import validate_snapshot
from .signals import build_signals
from .db import SCHEMA, conn
from .goals import goal_progress
from .muscles import attach_muscles
from .program import (active_deloads, parse_rotation, read_priorities,
                    read_split, rules_with_confirm, volume_block)


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
                                       "direction": r["direction"], "workout_id": r["workout_id"],
                                       "note": r["note"]}
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
    try:
        adherence = adherence_snapshot(c)
    except (sqlite3.Error, SystemExit):
        adherence = None
    try:
        signals = build_signals(c)
    except (sqlite3.Error, SystemExit):
        signals = []
    try:
        autoreg = autoreg_block(c)
    except (sqlite3.Error, SystemExit):
        autoreg = None
    try:
        changes = [dict(r) for r in c.execute(
            "SELECT id, date, action, day, slot, before_movements, before_sets, "
            "after_movements, after_sets, evidence, reverted_on FROM autoreg_changes "
            "ORDER BY id DESC LIMIT 20").fetchall()]
    except sqlite3.Error:
        changes = []
    try:
        volume = volume_block(c)
    except (sqlite3.Error, SystemExit):
        volume = {}
    return {"exported": datetime.now().isoformat(timespec="seconds"), "workouts": workouts, "sets": sets,
            "bodyweight": bw, "split_active": split_active, "rotation": rotation, "constants": constants,
            "progression": progression, "goals": goals, "priority": priority, "deload": deload,
            "rules": rules, "flags": flags, "mapping": mapping, "movement_notes": movement_notes,
            "adherence": adherence, "signals": signals, "autoreg": autoreg,
            "autoreg_changes": changes, "volume": volume}


def build_snapshot_validated(c=None) -> dict:
    """Build the dashboard payload and validate it against SnapshotModel
    before publication. Raises SnapshotValidationError on defect: the sync
    layer must not publish an arbitrary dict that happens to match the
    frontend's expectations."""
    snap = build_snapshot(c)
    validate_snapshot(snap)
    return snap


def export():
    print(json.dumps(build_snapshot_validated(), indent=2))


def sync(force=False):
    try:
        cfg = json.load(open(db.CFG))
        url, secret = cfg["url"], cfg["secret"]
    except (OSError, KeyError, ValueError):
        sys.exit("no sync config, expected url and secret in " + db.CFG)
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
    payload = json.dumps(build_snapshot_validated(c)).encode()
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
                     "Reconcile, then sync_push with force true to overwrite deliberately.")
        sys.exit("sync failed: " + str(e))
    except OSError as e:
        sys.exit("sync failed: " + str(e))

    # Dump SQL for git history
    sql_file = os.path.join(os.path.dirname(db.DB), "workouts.sql")
    with open(sql_file, 'w') as f:
        for line in c.iterdump():
            f.write(f"{line}\n")
    print(f"dumped SQL to {sql_file}")


def dump():
    c = conn()
    sql_file = os.path.join(os.path.dirname(os.path.abspath(db.DB)), "workouts.sql")
    with open(sql_file, 'w') as f:
        for line in c.iterdump():
            f.write(f"{line}\n")
    print(json.dumps({"dumped": sql_file}))


def restore(force=False):
    if not force:
        try:
            rc = sqlite3.connect(db.DB)
            row = rc.execute("SELECT id FROM workouts WHERE status = 'open' ORDER BY id DESC LIMIT 1").fetchone()
            rc.close()
            if row:
                sys.exit(f"workout {row[0]} is still open; end or delete it before restore, or use restore force")
        except sqlite3.Error:
            pass
    sql_file = os.path.join(os.path.dirname(db.DB), "workouts.sql")
    if not os.path.exists(sql_file):
        sys.exit("no workouts.sql found, cannot restore")
    # Build into a temp file first so a malformed dump can never empty the
    # live DB: the live file is only replaced after the restore verifies.
    import tempfile
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(db.DB)), suffix=".restore.db")
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
            live = sqlite3.connect(db.DB)
            live.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
            live.close()
        except sqlite3.Error:
            pass
        try:
            os.replace(tmp, db.DB)
        except OSError as e:
            sys.exit(f"restore failed to replace live DB ({e}), live DB untouched")
        for suffix in ("-wal", "-shm", "-journal"):
            try:
                os.remove(db.DB + suffix)
            except OSError:
                pass
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass
    print(json.dumps({"restored": True, "from": sql_file}))
