#!/usr/bin/env python3
"""reps maintenance entry. NOT the agent interface (that is MCP: reps.mcp).

Local recovery and development only: rebuild the live DB from the SQL
backup, re-write the backup from the live DB, print the dashboard payload,
or run the consistency check. Agents operate Reps through MCP tools;
nothing here is a second application interface.

This is the single place where domain results become process output:
results print as JSON, domain refusals (RepsError) print to stderr with a
nonzero exit. No other module prints or exits.
"""

import json
import sys
from typing import Any, NoReturn

from reps.audit import run_doctor
from reps.errors import RepsError
from reps.sync import dump_sql, export_snapshot, restore_sql


def usage() -> NoReturn:
    sys.exit("usage: log.py doctor | dump | restore [force] | export")


def emit(result: Any) -> None:
    if isinstance(result, str):
        print(result)
    else:
        print(json.dumps(result, indent=2))
    if isinstance(result, dict) and result.get("ok") is False:
        sys.exit(1)


def main() -> None:
    args = sys.argv[1:]
    try:
        if args == ["doctor"]:
            emit(run_doctor())
        elif args == ["dump"]:
            emit(dump_sql())
        elif args == ["export"]:
            emit(export_snapshot())
        elif args[:1] == ["restore"]:
            emit(restore_sql(len(args) > 1 and args[1] == "force"))
        else:
            usage()
    except RepsError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
