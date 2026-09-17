#!/usr/bin/env python3
"""Dump SQLite DB to SQL text for version control."""
import os
import sqlite3
import sys

DB = os.environ.get("REPS_DB", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "workouts.db"))
SQL_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "workouts.sql")

def main():
    if not os.path.exists(DB):
        print(f"DB not found: {DB}", file=sys.stderr)
        return 1
    
    conn = sqlite3.connect(DB)
    with open(SQL_FILE, 'w') as f:
        for line in conn.iterdump():
            f.write(f"{line}\n")
    
    conn.close()
    print(f"Dumped {DB} -> {SQL_FILE}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
