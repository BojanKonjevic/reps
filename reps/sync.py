import json
import os
import re
import sqlite3
import urllib.error
import urllib.request
from datetime import datetime

from . import db
from .db import SCHEMA, conn
from .errors import RepsError
from .models import HistoryStatesPayload, validate_snapshot
from .snapshot import build_views, history_states_view


def build_snapshot(c=None):
    """Full dashboard payload (v2 views). A build failure fails loudly:
    missing tables never default, the snapshot always validates or raises."""
    c = c or conn()
    return build_views(c)


def build_snapshot_validated(c=None) -> dict:
    """Build the dashboard payload and validate it against SnapshotModel
    before publication. Raises SnapshotValidationError on defect: the sync
    layer must not publish an arbitrary dict that happens to match the
    frontend's expectations."""
    snap = build_snapshot(c)
    validate_snapshot(snap)
    return snap


def export_snapshot():
    return build_snapshot_validated()


def build_history_states(c=None):
    """Unvalidated per-date historical states (validate via export_history_states)."""
    return history_states_view(c or conn())


def export_history_states():
    """On-demand historical states payload, validated before publication."""
    from pydantic import ValidationError as _ValidationError

    from .models import SnapshotValidationError, first_error
    payload = history_states_view(conn())
    try:
        HistoryStatesPayload.model_validate(payload)
    except _ValidationError as e:
        raise SnapshotValidationError(f"history states invalid: {first_error(e)}")
    return payload


def push_snapshot(force=False):
    try:
        cfg = json.load(open(db.CFG))
        url, secret = cfg["url"], cfg["secret"]
    except (OSError, KeyError, ValueError):
        raise RepsError("no sync config, expected url and secret in " + db.CFG)
    c = conn()
    # Integrity check before sync
    integrity = c.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok":
        raise RepsError("database integrity check failed: " + integrity)
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
            raise RepsError("sync pull-first failed: " + str(e))
    payload = json.dumps({"snapshot": build_snapshot_validated(c),
                            "history_states": export_history_states()}).encode()
    headers = {"Content-Type": "application/json", "Authorization": "Bearer " + secret,
               "User-Agent": "reps-sync/1"}
    if base_etag:
        headers["If-Match"] = base_etag
    if force:
        headers["X-Sync-Force"] = "1"
    req = urllib.request.Request(url + "/sync", data=payload, method="PUT", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            reply = json.loads(res.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 412:
            try:
                detail = json.loads(e.read().decode())
            except ValueError:
                detail = {}
            server_etag = detail.get("etag") or e.headers.get("ETag")
            raise RepsError(f"sync rejected: snapshot changed since pull (server {server_etag}), another session pushed first. "
                            "Reconcile, then sync_push with force true to overwrite deliberately.")
        raise RepsError("sync failed: " + str(e))
    except OSError as e:
        raise RepsError("sync failed: " + str(e))

    # Dump SQL for git history
    sql_file = os.path.join(os.path.dirname(db.DB), "workouts.sql")
    with open(sql_file, 'w') as f:
        for line in c.iterdump():
            f.write(f"{line}\n")
    return {"synced": True, "bytes": len(payload), "reply": reply, "dumped": sql_file}


def dump_sql():
    c = conn()
    sql_file = os.path.join(os.path.dirname(os.path.abspath(db.DB)), "workouts.sql")
    with open(sql_file, 'w') as f:
        for line in c.iterdump():
            f.write(f"{line}\n")
    return {"dumped": sql_file}


def restore_sql(force=False):
    if not force:
        try:
            rc = sqlite3.connect(db.DB)
            row = rc.execute("SELECT id FROM workouts WHERE status = 'open' ORDER BY id DESC LIMIT 1").fetchone()
            rc.close()
            if row:
                raise RepsError(f"workout {row[0]} is still open; end or delete it before restore, or use restore force")
        except sqlite3.Error:
            pass
    sql_file = os.path.join(os.path.dirname(db.DB), "workouts.sql")
    if not os.path.exists(sql_file):
        raise RepsError("no workouts.sql found, cannot restore")
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
            raise RepsError(f"dump failed to load ({e}), live DB untouched")
        if t.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RepsError("restored DB failed integrity check, live DB untouched")
        tables = {r[0] for r in t.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        expected = set(re.findall(r"CREATE TABLE IF NOT EXISTS (\w+)", SCHEMA))
        if tables != expected:
            raise RepsError(f"dump is missing tables (has {sorted(tables)}, expected {sorted(expected)}), live DB untouched")
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
            raise RepsError(f"restore failed to replace live DB ({e}), live DB untouched")
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
    return {"restored": True, "from": sql_file}
