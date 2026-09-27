import os
import sqlite3
from contextlib import contextmanager


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


DB = os.environ.get("REPS_DB", os.path.join(ROOT, "workouts.db"))


CFG = os.path.join(os.path.expanduser("~"), ".config", "reps", "config.json")


SCHEMA_VERSION = 3


def _check_lists():
    from .vocab import (AdherenceStatus, AutoregAction, DeloadScope,
                        GoalStatus, HistoryDomain, PriorityTier, RuleStatus, SplitVariant,
                        Verdict, Direction, WorkoutStatus, values)
    return {
        "workout_status": ", ".join(f"'{v}'" for v in values(WorkoutStatus)),
        "verdict": ", ".join(f"'{v}'" for v in values(Verdict)),
        "direction": ", ".join(f"'{v}'" for v in values(Direction)),
        "priority_tier": ", ".join(f"'{v}'" for v in values(PriorityTier)),
        "deload_scope": ", ".join(f"'{v}'" for v in values(DeloadScope)),
        "split_variant": ", ".join(f"'{v}'" for v in values(SplitVariant)),
        "autoreg_action": ", ".join(f"'{v}'" for v in values(AutoregAction)),
        "rule_status": ", ".join(f"'{v}'" for v in values(RuleStatus)),
        "goal_status": ", ".join(f"'{v}'" for v in values(GoalStatus)),
        "adherence_status": ", ".join(f"'{v}'" for v in values(AdherenceStatus)),
        "history_domain": ", ".join(f"'{v}'" for v in values(HistoryDomain)),
    }


def build_schema():
    """Assemble SCHEMA with enum CHECK lists generated from reps/vocab.py.

    One enum definition drives SQL, Pydantic, MCP schemas, and Zod.
    Small f-string assembly, no framework. The e1rm() UDF must never appear
    in a view, trigger, index, or CHECK: workouts.sql is restored through the
    sqlite3 CLI and a schema object referencing an app-defined function
    breaks there.
    """
    ck = _check_lists()
    return f"""
CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS workouts (
  id INTEGER PRIMARY KEY,
  date TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ({ck['workout_status']})),
  notes TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS sets (
  id INTEGER PRIMARY KEY,
  workout_id INTEGER NOT NULL REFERENCES workouts(id) ON DELETE CASCADE,
  exercise TEXT NOT NULL REFERENCES lift(exercise) ON UPDATE CASCADE,
  weight REAL NOT NULL,
  reps INTEGER NOT NULL CHECK (reps > 0),
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
CREATE TABLE IF NOT EXISTS lift (
  exercise TEXT PRIMARY KEY,
  is_bodyweight_only INTEGER NOT NULL CHECK (is_bodyweight_only IN (0, 1))
);
CREATE TABLE IF NOT EXISTS lift_muscle (
  exercise TEXT NOT NULL REFERENCES lift(exercise) ON UPDATE CASCADE ON DELETE CASCADE,
  muscle TEXT NOT NULL,
  PRIMARY KEY (exercise, muscle)
);
CREATE VIEW IF NOT EXISTS set_muscle AS
  SELECT s.id AS set_id, lm.muscle AS muscle FROM sets s JOIN lift_muscle lm USING (exercise);
CREATE TABLE IF NOT EXISTS movement_note (
  id INTEGER PRIMARY KEY,
  exercise TEXT NOT NULL REFERENCES lift(exercise) ON UPDATE CASCADE,
  note TEXT NOT NULL,
  created TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS progression (
  id INTEGER PRIMARY KEY,
  workout_id INTEGER NOT NULL REFERENCES workouts(id) ON DELETE CASCADE,
  exercise TEXT NOT NULL REFERENCES lift(exercise) ON UPDATE CASCADE,
  verdict TEXT NOT NULL CHECK (verdict IN ({ck['verdict']})),
  next_weight REAL NOT NULL,
  next_reps INTEGER NOT NULL,
  direction TEXT NOT NULL CHECK (direction IN ({ck['direction']})),
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
  tier TEXT NOT NULL CHECK (tier IN ({ck['priority_tier']})),
  since TEXT NOT NULL,
  until TEXT
);
CREATE TABLE IF NOT EXISTS deload_state (
  id INTEGER PRIMARY KEY,
  scope TEXT NOT NULL CHECK (scope IN ({ck['deload_scope']})),
  subject TEXT NOT NULL,
  set_on TEXT NOT NULL,
  cleared_on TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_deload_active ON deload_state(scope, subject) WHERE cleared_on IS NULL;
CREATE TABLE IF NOT EXISTS split_day (
  name TEXT PRIMARY KEY
);
CREATE TABLE IF NOT EXISTS split_slot (
  id INTEGER PRIMARY KEY,
  variant TEXT NOT NULL CHECK (variant IN ({ck['split_variant']})),
  day TEXT NOT NULL REFERENCES split_day(name) ON UPDATE CASCADE ON DELETE CASCADE,
  slot INTEGER NOT NULL,
  sets INTEGER NOT NULL,
  UNIQUE (variant, day, slot)
);
CREATE TABLE IF NOT EXISTS split_slot_lift (
  slot_id INTEGER NOT NULL REFERENCES split_slot(id) ON DELETE CASCADE,
  position INTEGER NOT NULL,
  exercise TEXT NOT NULL REFERENCES lift(exercise) ON UPDATE CASCADE,
  PRIMARY KEY (slot_id, position)
);
CREATE TABLE IF NOT EXISTS rotation (
  position INTEGER PRIMARY KEY,
  day TEXT NULL REFERENCES split_day(name) ON UPDATE CASCADE ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS rotation_anchor (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  anchor_date TEXT NOT NULL,
  position INTEGER NOT NULL REFERENCES rotation(position)
);
CREATE TABLE IF NOT EXISTS compaction (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  last_compacted TEXT NULL,
  postponed_until TEXT NULL
);
CREATE TABLE IF NOT EXISTS rules (
  id INTEGER PRIMARY KEY,
  subject TEXT NOT NULL,
  text TEXT NOT NULL,
  start_date TEXT NOT NULL,
  expiry TEXT,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ({ck['rule_status']})),
  created TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS goals (
  id INTEGER PRIMARY KEY,
  exercise TEXT NOT NULL REFERENCES lift(exercise) ON UPDATE CASCADE,
  target_e1rm REAL NOT NULL,
  target_desc TEXT NOT NULL,
  deadline TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ({ck['goal_status']})),
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
  action TEXT NOT NULL CHECK (action IN ({ck['autoreg_action']})),
  set_on TEXT NOT NULL,
  hold_until TEXT NOT NULL,
  reason TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS autoreg_changes (
  id INTEGER PRIMARY KEY,
  date TEXT NOT NULL,
  action TEXT NOT NULL CHECK (action IN ({ck['autoreg_action']})),
  day TEXT NOT NULL,
  slot INTEGER NOT NULL,
  before_movements TEXT NOT NULL,
  before_sets INTEGER NOT NULL,
  after_movements TEXT NOT NULL,
  after_sets INTEGER NOT NULL,
  evidence TEXT NOT NULL DEFAULT '',
  reverted_on TEXT
);
-- Shared state-change history (docs/observe spec, Part II section 25.1).
-- Append-only: reversals are new rows pointing back via reverses, never
-- rewrites. before/after are per-domain JSON envelopes validated on read
-- through the Pydantic discriminated union in reps/models.py. Autoreg keeps
-- its own structured ledger by sanctioned exception, it is not migrated here.
CREATE TABLE IF NOT EXISTS state_change (
  id INTEGER PRIMARY KEY,
  domain TEXT NOT NULL CHECK (domain IN ({ck['history_domain']})),
  subject TEXT NOT NULL DEFAULT '',
  date TEXT NOT NULL,
  created TEXT NOT NULL,
  before_json TEXT NOT NULL DEFAULT '{{}}',
  after_json TEXT NOT NULL DEFAULT '{{}}',
  evidence TEXT NOT NULL DEFAULT '',
  superseded_by INTEGER REFERENCES state_change(id),
  reverses INTEGER REFERENCES state_change(id),
  sequence INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_state_change_domain_subject_date
  ON state_change(domain, subject, date, created, id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_state_change_sequence
  ON state_change(domain, subject, date, sequence);
"""


SCHEMA = build_schema()


AUTOREG_HOLD_COLS = {"id", "day", "movements", "action", "set_on", "hold_until", "reason"}


AUTOREG_CHANGE_COLS = {"id", "date", "action", "day", "slot", "before_movements",
                       "before_sets", "after_movements", "after_sets", "evidence", "reverted_on"}


# Open-connection registry: every conn() registers here. sqlite3.Connection
# does not support weak references, so this is a strong set: entries live
# until close_all() (MCP edge, test teardown) or closing_conn() exit.
# Request-scoped owners close explicitly; close_all() is the backstop, never
# a substitute for closing inside long-lived loops.
_OPEN: set = set()


def conn():
    import logging as _logging
    from .e1rm import e1rm as _e1rm

    c = sqlite3.connect(DB, timeout=30.0)
    c.row_factory = sqlite3.Row
    _OPEN.add(c)
    try:
        c.execute("PRAGMA busy_timeout = 30000")
    except sqlite3.Error:
        pass
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA foreign_keys=ON")

    def _e1rm_udf(w, r):
        # Corrupt rows (reps<=0, non-finite weight) return NULL instead of
        # raising through SQLite as OperationalError. Aggregates skip NULL,
        # so one bad row cannot poison MAX(e1rm) for the lift.
        try:
            return _e1rm(w, r)
        except Exception:
            return None

    c.create_function("e1rm", 2, _e1rm_udf, deterministic=True)
    tables = {r[0] for r in c.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    if "schema_version" not in tables:
        legacy = {"meta", "lift_muscle_map", "splits", "movement_notes", "set_muscles"} & tables
        if legacy:
            c.close()
            raise RuntimeError(
                f"legacy v1 tables present ({sorted(legacy)}); "
                "migrate the database, there is no auto-migrate path")
        c.executescript(SCHEMA)
        c.execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))
        c.commit()
        return c
    row = c.execute("SELECT version FROM schema_version").fetchone()
    if row is None:
        # Schema created but never stamped (fresh executescript): stamp it.
        c.execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))
        c.commit()
        return c
    if row["version"] != SCHEMA_VERSION:
        c.close()
        raise RuntimeError(
            f"schema version {row['version']} != code {SCHEMA_VERSION}; "
            "refusing to migrate automatically (policy: refuse + restore). "
            "Restore a matching workouts.sql dump or reconcile the schema manually")
    # Version matches: tables exist (they are stamped only after creation),
    # so skip the redundant DDL pass. It reparsed the whole schema and took
    # a lock on every open; pragmas and the UDF above are per-connection and
    # stay. Fresh databases still build through the executescript path above.
    return c


# Open-connection registry lives above conn() (single definition).


def close_all() -> int:
    """Close every tracked connection. Returns the count closed."""
    conns = list(_OPEN)
    _OPEN.clear()
    n = 0
    for c in conns:
        try:
            c.close()
            n += 1
        except Exception:
            pass
    return n


@contextmanager
def closing_conn():
    """Request-scoped connection: use as `with closing_conn() as c:`."""
    c = conn()
    try:
        yield c
    finally:
        _OPEN.discard(c)
        try:
            c.close()
        except Exception:
            pass


def active_paths() -> dict:
    """Which DB/constants/config paths are active (for env-divergence diagnostics)."""
    from .constants import CONSTANTS_FILE as _CF
    return {"db": DB, "constants": _CF, "config": CFG}


def placeholders(n):
    if n <= 0:
        from .errors import RepsError
        raise RepsError("internal error: empty placeholder list (refusing to build ambiguous SQL)")
    return ",".join("?" * n)


# Central allowlist for the few places that interpolate table/column names
# into SQL (string assembly is allowlist-safe today, fragile tomorrow: every
# future interpolation must go through here so a typo cannot become injection).
_TABLE_ALLOWLIST = frozenset({
    "sets", "goals", "movement_note", "progression",
    "workouts", "bodyweight", "lift", "lift_muscle",
})


def check_table(name):
    if name not in _TABLE_ALLOWLIST:
        from .errors import RepsError
        raise RepsError(f"internal error: unexpected table '{name}' (allowlist refused)")
    return name


def open_workout(c):
    rows = c.execute("SELECT * FROM workouts WHERE status = 'open' ORDER BY id DESC LIMIT 2").fetchall()
    if len(rows) > 1:
        from .errors import RepsError
        raise RepsError(
            f"data corruption: {len(rows)}+ open workouts (ids {[r['id'] for r in rows]} and possibly more); "
            "run doctor, keep the newest, end or delete the rest before logging")
    return rows[0] if rows else None
