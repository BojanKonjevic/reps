#!/usr/bin/env python3
"""reps maintenance entry. NOT the agent interface (that is MCP: reps.mcp).

Local recovery and development only: rebuild the live DB from the SQL
backup, re-write the backup from the live DB, print the dashboard payload,
or run the consistency check. Agents operate Reps through MCP tools;
nothing here is a second application interface.
"""

import sys

from reps.audit import doctor
from reps.sync import dump, export, restore


def usage():
    sys.exit("usage: log.py doctor | dump | restore [force] | export")


def main():
    args = sys.argv[1:]
    if args == ["doctor"]:
        doctor()
    elif args == ["dump"]:
        dump()
    elif args == ["export"]:
        export()
    elif args[:1] == ["restore"]:
        restore(len(args) > 1 and args[1] == "force")
    else:
        usage()


if __name__ == "__main__":
    main()
