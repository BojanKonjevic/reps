import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def tmp_db(monkeypatch):
    """Create a temporary SQLite DB for each test."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    monkeypatch.setenv("REPS_DB", path)
    # Force reimport of log module to pick up new DB
    import importlib
    import log
    importlib.reload(log)
    yield path
    try:
        os.unlink(path)
    except OSError:
        pass


@pytest.fixture
def log_module(tmp_db):
    """Return reloaded log module with tmp DB."""
    import log
    import importlib
    return importlib.reload(log)


def close_session(log, note="done"):
    """End the open workout the Phase 2 way: baseline progression for every
    trained-but-unjudged exercise, then close. Tests use this wherever the
    writeback itself is not under test."""
    c = log.conn()
    w = log.open_workout(c)
    if w:
        trained = {r["exercise"] for r in c.execute(
            "SELECT DISTINCT exercise FROM sets WHERE workout_id = ?", (w["id"],)).fetchall()}
        judged = {r["exercise"] for r in c.execute(
            "SELECT DISTINCT exercise FROM progression WHERE workout_id = ?", (w["id"],)).fetchall()}
        for ex in sorted(trained - judged):
            log.cmd_progression_set(ex, "baseline", "test", "flat")
    return log.cmd_end(note)
