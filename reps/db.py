import os
import sqlite3


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


DB = os.environ.get("REPS_DB", os.path.join(ROOT, "workouts.db"))


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
-- meta has no dedicated writer: plan reads last_compacted, the compaction flow writes it.
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


def open_workout(c):
    row = c.execute("SELECT * FROM workouts WHERE status = 'open' ORDER BY id DESC LIMIT 1").fetchone()
    return row
