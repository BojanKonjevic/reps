#!/bin/sh
# Single Python test entrypoint. Everything (pre-commit, CI, docs) calls this.
# Uses the frozen lockfile when uv is available, system python otherwise.
set -eu
ROOT="$(dirname "$0")/.."
if command -v uv >/dev/null 2>&1 && [ -f "$ROOT/uv.lock" ]; then
  exec uv run --frozen pytest tests/ -q "$@"
else
  exec python3 -m pytest tests/ -q "$@"
fi
