#!/usr/bin/env python3
"""Repo-hygiene check: MEMORY.md plan state tracks the latest done session.

The agent must update Progression state and the Muscle load ledger at every
session end. This test fails when the most recent done workout's lifts are
missing from them, so a skipped writeback gets caught by the suite instead
of relying on anyone remembering the prose instruction.

Reads the real working tree (not a tmp DB); skips when no done sessions
exist in this checkout.
"""

import os
import re
import sqlite3

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "workouts.db")
MEMORY = os.path.join(ROOT, "MEMORY.md")


def _section(text, name):
    m = re.search(r"^## " + re.escape(name) + r"\s*$", text, re.MULTILINE)
    if not m:
        return None
    rest = text[m.end():]
    nxt = re.search(r"^## ", rest, re.MULTILINE)
    return rest[:nxt.start()] if nxt else rest


def test_plan_state_covers_latest_done_session():
    if not os.path.exists(DB):
        pytest.skip("no live database in this checkout")
    c = sqlite3.connect(DB)
    try:
        rows = c.execute(
            "SELECT w.date, w.id FROM workouts w WHERE w.status = 'done' "
            "AND EXISTS (SELECT 1 FROM sets s WHERE s.workout_id = w.id) "
            "ORDER BY w.date DESC, w.id DESC LIMIT 1"
        ).fetchall()
        if not rows:
            pytest.skip("no closed sessions with sets yet")
        day, wid = rows[0]
        lifts = sorted({r[0] for r in c.execute(
            "SELECT DISTINCT exercise FROM sets WHERE workout_id = ?", (wid,)).fetchall()})
    finally:
        c.close()
    with open(MEMORY) as f:
        text = f.read()
    prog = _section(text, "Progression state")
    assert prog is not None and "None yet" not in prog, \
        "Progression state is empty despite closed sessions"
    missing = [li for li in lifts
               if not re.search(r"^[-*]\s*" + re.escape(li) + r"\s*:", prog, re.MULTILINE)]
    assert not missing, \
        f"latest done session ({day}) lifts missing from Progression state: {missing}"
    ledger = _section(text, "Muscle load (7d retention)")
    assert ledger is not None and "None yet" not in ledger, \
        "Muscle load ledger is empty despite closed sessions"
