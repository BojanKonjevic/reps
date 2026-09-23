#!/bin/sh
# doctor hook: validate the committed dump when no live DB exists (CI),
# otherwise validate the live DB. Either way the same checks run.
if [ ! -f workouts.db ] && [ -f workouts.sql ]; then
  export REPS_DB
  REPS_DB="$(mktemp /tmp/reps-doctor-XXXX.db)"
  sqlite3 "$REPS_DB" < workouts.sql
  trap 'rm -f "$REPS_DB"' EXIT INT TERM
fi
# reps needs pydantic/mcp (see pyproject.toml). Prefer system python3 when
# it has them (CI installs via pip, dev venvs), else run through uv's cache.
if python3 -c "import pydantic, mcp" 2>/dev/null; then
  python3 log.py doctor
elif command -v uv >/dev/null 2>&1; then
  uv run --no-project --with pydantic --with "mcp>=2" -- python log.py doctor
else
  python3 log.py doctor
fi
