import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import reps
import reps.db
import reps.memory


@pytest.fixture
def tmp_db(monkeypatch, tmp_path):
    """Create a temporary SQLite DB for each test."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    monkeypatch.setenv("REPS_DB", path)
    # Domain modules read the DB path global at call time, so pointing the
    # live global at the tmp DB is enough (undone automatically on teardown).
    monkeypatch.setattr(reps.db, "DB", path)
    # Memory writeback (clear_deload) must never touch the real docs/MEMORY.md.
    mem = tmp_path / "MEMORY.md"
    mem.write_text("# memory\n\n## State\n\n## Other\n")
    monkeypatch.setattr(reps.memory, "MEMORY_FILE", str(mem))
    yield path
    try:
        os.unlink(path)
    except OSError:
        pass


@pytest.fixture
def log_module(tmp_db):
    """Return the reps domain package bound to the tmp DB.

    Tests invoke domain operations directly (reps is the application layer);
    agents use the same operations through MCP tools.
    """
    return reps


def close_session(log, note="done"):
    """End the open workout the way the agent must: baseline progression for
    every trained-but-unjudged exercise, reconcile new exercises into the
    active split, then close. Tests use this wherever the writeback itself
    is not under test."""
    c = log.conn()
    w = log.open_workout(c)
    if w:
        trained = {r["exercise"] for r in c.execute(
            "SELECT DISTINCT exercise FROM sets WHERE workout_id = ?", (w["id"],)).fetchall()}
        judged = {r["exercise"] for r in c.execute(
            "SELECT DISTINCT exercise FROM progression WHERE workout_id = ?", (w["id"],)).fetchall()}
        for ex in sorted(trained - judged):
            log.set_progression(ex, "baseline", 80, 5, "flat")
        new = sorted(set(trained) - log.split_all_movements("active"))
        if new:
            days = log.split_day_order("active")
            day = log.best_split_day(trained) or (days[0] if days else None)
            if day is None:
                for i, ex in enumerate(sorted(trained), 1):
                    log.set_split("Test", i, ex, 2)
            else:
                log.reconcile_split(day)
    return log.end_workout(note)


def seed_split(log, day, *movesets):
    """Seed an active split day: seed_split(log, 'Upper A', ('bench', 3), ('row', 2)).
    Exercises must already have mappings (log a set or map set first)."""
    for i, (move, sets) in enumerate(movesets, 1):
        log.set_split(day, i, move, sets)


def seed_lift(c, exercise, muscles=None, bodyweight_only=0):
    """Seed lift registry rows for raw-SQL set inserts that bypass domain validation.

    Tests inserting sets by hand must still satisfy the lift FK; the set_muscle
    view derives from these rows. Pass muscles=None to simulate a lift with no
    mapping (missing-muscle premises).
    """
    c.execute("INSERT OR IGNORE INTO lift (exercise, is_bodyweight_only) VALUES (?, ?)",
              (exercise, bodyweight_only))
    if muscles:
        for mu in muscles.split(","):
            mu = mu.strip()
            if mu:
                c.execute("INSERT OR IGNORE INTO lift_muscle (exercise, muscle) VALUES (?, ?)",
                          (exercise, mu))
    c.commit()
