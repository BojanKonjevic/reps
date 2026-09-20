#!/bin/sh
# doctor hook: validate the committed dump when no live DB exists (CI),
# otherwise validate the live DB. Either way the same checks run.
if [ ! -f workouts.db ] && [ -f workouts.sql ]; then
  export REPS_DB
  REPS_DB="$(mktemp /tmp/reps-doctor-XXXX.db)"
  sqlite3 "$REPS_DB" < workouts.sql
  trap 'rm -f "$REPS_DB"' EXIT INT TERM
fi
python3 log.py doctor
