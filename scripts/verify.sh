#!/usr/bin/env bash
# One verify entrypoint: gen check + ssot_check + py tests + dashboard checks + doctor.
set -euo pipefail
ROOT="$(dirname "$0")/.."
cd "$ROOT"
fail=0
run() {
  echo "== $*"
  if ! "$@"; then
    echo "FAIL: $*"
    fail=1
  fi
}
run scripts/gen-check.sh
run python3 scripts/sync_docs.py --check
run python3 scripts/ssot_check.py
run scripts/test-py.sh
run pnpm --dir dashboard run lint
run pnpm --dir dashboard run typecheck
run pnpm --dir dashboard run test
run scripts/doctor.sh
if [ "$fail" -ne 0 ]; then
  echo "verify.sh: $fail step(s) failed"
  exit 1
fi
echo "verify.sh: all green"
