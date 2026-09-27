# SSOT owner: destructive-op audit log (timestamped force/delete/restore/constants_set record).
# Consumers: MCP destructive/force handlers via log_destructive(). File stays local, untracked.

"""Append-only audit log for destructive/force operations (F42, log-only policy).

Every force/delete/restore/constants_set invocation lands here with a
timestamp and args. Read path: tail the JSONL file. Never blocks the
operation; a logging failure is swallowed after a stderr warning.
"""

import json
import os
from datetime import datetime

from .db import ROOT

AUDIT_LOG = os.environ.get("REPS_AUDIT_LOG", os.path.join(ROOT, "audit.log"))


def log_destructive(tool, args):
    import sys as _sys
    entry = {"at": datetime.now().isoformat(timespec="seconds"),
             "tool": tool, "args": args}
    try:
        with open(AUDIT_LOG, 'a') as f:
            f.write(json.dumps(entry, sort_keys=True, default=str) + "\n")
    except OSError as e:
        _sys.stderr.write(f"reps audit log failed ({e})\n")
    return entry
