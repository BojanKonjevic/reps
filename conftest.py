import os
import tempfile
import pytest


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
