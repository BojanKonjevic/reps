#!/bin/sh
# One verify entrypoint: gen check + ssot_check + py tests + dashboard checks + doctor.
set -eu
ROOT="$(dirname "$0")/.."
cd "$ROOT"
scripts/gen-check.sh
python3 scripts/ssot_check.py
scripts/test-py.sh
pnpm --dir dashboard run lint
pnpm --dir dashboard run typecheck
pnpm --dir dashboard run test
scripts/doctor.sh
