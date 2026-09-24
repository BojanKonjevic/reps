#!/bin/sh
# Single Python test entrypoint. Everything (pre-commit, CI, docs) calls this.
# Uses the frozen lockfile when uv is available, system python otherwise.
set -eu
ROOT="$(dirname "$0")"
cd "$ROOT/.."
if [ "$#" -eq 0 ]; then
  set -- tests/ -q
fi
if command -v uv >/dev/null 2>&1 && [ -f uv.lock ]; then
  exec uv run --frozen pytest "$@"
else
  exec python3 -m pytest "$@"
fi
