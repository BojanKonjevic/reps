import os
import sqlite3


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


DB = os.environ.get("REPS_DB", os.path.join(ROOT, "workouts.db"))


CFG = os.path.join(os.path.expanduser("~"), ".config", "reps", "config.json")


SCHEMA_VERSION = 2


def _check_lists():
    from .vocab import (AdherenceStatus, AutoregAction, DeloadScope,
                        GoalStatus, PriorityTier, RuleStatus, SplitVariant,
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
  next_weight REAL,
  next_reps INTEGER,
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
"""


SCHEMA = build_schema()


AUTOREG_HOLD_COLS = {"id", "day", "movements", "action", "set_on", "hold_until", "reason"}


AUTOREG_CHANGE_COLS = {"id", "date", "action", "day", "slot", "before_movements",
                       "before_sets", "after_movements", "after_sets", "evidence", "reverted_on"}


def conn():
    from .e1rm import e1rm as _e1rm

    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA foreign_keys=ON")
    c.create_function("e1rm", 2, lambda w, r: _e1rm(w, r), deterministic=True)
    c.executescript(SCHEMA)
    row = c.execute("SELECT version FROM schema_version").fetchone()
    if row is None:
        c.execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))
        c.commit()
    elif row["version"] != SCHEMA_VERSION:
        c.close()
        raise RuntimeError(
            f"schema version {row['version']} != code {SCHEMA_VERSION}; "
            "run scripts/migrate_v2.py, there is no auto-migrate path")
    return c


def placeholders(n):
    return ",".join("?" * max(1, n))


def open_workout(c):
    row = c.execute("SELECT * FROM workouts WHERE status = 'open' ORDER BY id DESC LIMIT 1").fetchone()
    return row
