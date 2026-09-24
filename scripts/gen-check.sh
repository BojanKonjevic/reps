#!/bin/sh
# Pre-commit/CIT entry for the generator check. Fails on any drift between
# reps/models.py (plus scenarios) and the committed generated files.
set -eu
ROOT="$(dirname "$0")"
cd "$ROOT/.."
if command -v uv >/dev/null 2>&1 && [ -f uv.lock ]; then
  exec uv run --frozen python scripts/gen.py --check
else
  exec python3 scripts/gen.py --check
fi
