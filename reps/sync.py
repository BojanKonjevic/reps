import json
import logging
import os
import re
import sqlite3
import urllib.error
import urllib.request
from datetime import datetime

from . import db
from .db import SCHEMA, SCHEMA_VERSION, active_paths, conn
from .errors import RepsError
from .models import HistoryStatesPayload, validate_snapshot
from .snapshot import build_views, history_states_view

log = logging.getLogger("reps.sync")
SYNC_TIMEOUT = float(os.environ.get("REPS_SYNC_TIMEOUT", "30"))


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
        with open(db.CFG) as _cfg:
            cfg = json.load(_cfg)
        url, secret = cfg["url"], cfg["secret"]
    except (OSError, KeyError, ValueError):
        raise RepsError("no sync config, expected url and secret in " + db.CFG)
    try:
        st = os.stat(db.CFG)
        if st.st_mode & 0o077:
            log.warning("sync config %s is group/world-readable (mode %o); restrict to 0600", db.CFG, st.st_mode & 0o777)
    except OSError:
        pass
    log.warning("sync active paths: %s", active_paths())
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
        # One retry for the idempotent pull-first GET (writes never retry).
        last_err = None
        for _ in range(2):
            try:
                with urllib.request.urlopen(get_req, timeout=SYNC_TIMEOUT) as res:
                    base_etag = res.headers.get("ETag")
                last_err = None
                break
            except urllib.error.HTTPError as e:
                raise RepsError(f"sync pull-first refused (HTTP {e.code}); not overwriting without a base ETag")
            except OSError as e:
                last_err = e
        if last_err is not None:
            raise RepsError("sync pull-first failed (network): " + str(last_err))
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
        with urllib.request.urlopen(req, timeout=SYNC_TIMEOUT) as res:
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
        # Status-preserving prefix so callers can distinguish server refusals.
        raise RepsError(f"sync failed (HTTP {e.code}): {e}")
    except OSError as e:
        raise RepsError("sync failed (network): " + str(e))

    # Dump SQL for git history (atomic replace: a crash never leaves a truncated backup).
    _dump_sql_atomic(c)
    sql_file = os.path.join(os.path.dirname(os.path.abspath(db.DB)), "workouts.sql")
    return {"synced": True, "bytes": len(payload), "reply": reply, "dumped": sql_file}


def _dump_sql_atomic(c):
    import tempfile
    sql_file = os.path.join(os.path.dirname(os.path.abspath(db.DB)), "workouts.sql")
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(sql_file)), suffix=".sql")
    try:
        with os.fdopen(fd, 'w') as f:
            for line in c.iterdump():
                f.write(f"{line}\n")
        os.replace(tmp, sql_file)
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass
    return sql_file


def dump_sql():
    c = conn()
    return {"dumped": _dump_sql_atomic(c)}


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
    sql_file = os.path.join(os.path.dirname(os.path.abspath(db.DB)), "workouts.sql")
    if not os.path.exists(sql_file):
        raise RepsError("no workouts.sql found, cannot restore")
    # Build into a temp file first so a malformed dump can never empty the
    # live DB: the live file is only replaced after the restore verifies.
    import tempfile
    _dir = os.path.dirname(os.path.abspath(db.DB)) or "."
    fd, tmp = tempfile.mkstemp(dir=_dir, suffix=".restore.db")
    os.close(fd)
    try:
        try:
            t = sqlite3.connect(tmp)
            # NOTE: the dump loads with FK enforcement OFF on purpose:
            # iterdump emits each table's CREATE+INSERTs before later
            # tables exist, so enforcement at load time fails at prepare
            # time ("no such table") on valid dumps. Violations are still
            # caught by foreign_key_check below before the live DB is touched.
            t.execute("PRAGMA foreign_keys=OFF")
            with open(sql_file, 'r') as f:
                t.executescript(f.read())
            t.commit()
        except sqlite3.Error as e:
            raise RepsError(f"dump failed to load ({e}), live DB untouched")
        if t.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RepsError("restored DB failed integrity check, live DB untouched")
        # FK enforcement check: a dump that loads with FKs off but violates
        # them must never replace the live DB.
        try:
            bad = t.execute("PRAGMA foreign_key_check").fetchall()
        except sqlite3.Error as e:
            raise RepsError(f"restored DB FK check failed ({e}), live DB untouched")
        if bad:
            raise RepsError(f"restored DB has {len(bad)} foreign-key violation(s), live DB untouched")
        tables = {r[0] for r in t.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        expected = set(re.findall(r"CREATE TABLE IF NOT EXISTS (\w+)", SCHEMA))
        if tables != expected:
            raise RepsError(f"dump is missing tables (has {sorted(tables)}, expected {sorted(expected)}), live DB untouched")
        ver = t.execute("SELECT version FROM schema_version").fetchone()
        if ver is None or ver[0] != SCHEMA_VERSION:
            raise RepsError(f"dump schema version {ver[0] if ver else None} != code {SCHEMA_VERSION}, live DB untouched (refusing to migrate)")
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
