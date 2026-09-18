#!/usr/bin/env bash
set -euo pipefail
if grep -rnF '\' dashboard/src/ --include='*.ts' --include='*.html' | grep -v '__tests__'; then
  echo 'ERROR: Backslash escapes found in dashboard source'
  exit 1
fi
