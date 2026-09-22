import json
import os
import re
import sys

from . import db
from .constants import load_constants
from .db import ROOT, SCHEMA, conn
from .goals import goal_progress
from .muscles import _levenshtein
from .program import (count_bad_weeks, day_movements, read_priorities,
                      split_day_order)


def cmd_audit():
    """Run deterministic audit checks and output flagged items."""
    c = conn()
    import itertools

    flags = []

    # Checks 2 (missing muscle tags) and 3 (mapping drift) are structurally
    # impossible: the mapping is authoritative at log time, per-set overrides
    # are refused, and the end gate requires every set to carry muscles.

    # Check 4: Implausible progression jumps
    # Rep-band thresholds (same scale as the planning confidence bands): a +1
    # rep gain is always 2.2%+ e1RM, so flat science-rate bounds would flag
    # every routine rep PR. Band is read off the current session best's reps;
    # above 15 reps e1RM is informational only and never flags.
    # Jumps explained by set/workout notes are skipped.
    sets = c.execute("""
        SELECT s.id, s.exercise, s.weight, s.reps, w.date, s.note AS set_note, w.notes AS workout_notes,
               CASE WHEN s.reps = 1 THEN s.weight ELSE s.weight * (1 + s.reps / 30.0) END as e1rm
        FROM sets s JOIN workouts w ON w.id = s.workout_id
        WHERE s.weight > 0 ORDER BY s.exercise, w.date, s.id
    """).fetchall()

    by_ex = {}
    for s in sets:
        by_ex.setdefault(s["exercise"], []).append(s)

    constants = load_constants()
    explained = tuple(constants.get("explained_keywords", ["deload", "return", "program change", "injury", "technique", "sick", "travel"]))
    thresholds = constants.get("thresholds", {})
    drop_pct = thresholds.get("progression_drop_pct", -50)
    dup_dist = thresholds.get("duplicate_name_distance", 2)
    stale_hours = thresholds.get("stale_workout_hours", 8)
    vol_weeks = thresholds.get("volume_window_weeks", 8)
    vol_bad = thresholds.get("volume_bad_weeks", 4)

    def jump_bound(reps):
        for band in constants.get("rep_bands", []):
            max_reps = band.get("max_reps")
            if max_reps is None:
                return None
            if reps <= max_reps:
                return band.get("jump_pct")
        return None

    for ex, ex_sets in by_ex.items():
        by_date = {}
        notes_by_date = {}
        for s in ex_sets:
            d = s["date"]
            if d not in by_date or s["e1rm"] > by_date[d][0]:
                by_date[d] = (s["e1rm"], s["reps"])
            blob = ((s["set_note"] or "") + " " + (s["workout_notes"] or "")).lower()
            notes_by_date[d] = (notes_by_date.get(d, "") + " " + blob).strip()
        dates = sorted(by_date.keys())
        for i in range(1, len(dates)):
            prev, _ = by_date[dates[i-1]]
            curr, reps = by_date[dates[i]]
            bound = jump_bound(reps)
            if bound is None:
                continue
            if prev > 0:
                pct = (curr - prev) / prev * 100
                if pct > bound:
                    if any(k in notes_by_date.get(dates[i-1], "") or k in notes_by_date.get(dates[i], "") for k in explained):
                        continue
                    flags.append({"check": "progression_jump", "severity": "high", "evidence": f"{ex}: {prev:.1f} -> {curr:.1f} e1RM ({pct:.1f}% jump, bound {bound}%) on {dates[i]}", "fix": "verify data entry, add explanatory note, or update weight/reps"})
                elif pct < drop_pct:
                    if any(k in notes_by_date.get(dates[i-1], "") or k in notes_by_date.get(dates[i], "") for k in explained):
                        continue
                    flags.append({"check": "progression_drop", "severity": "medium", "evidence": f"{ex}: {prev:.1f} -> {curr:.1f} e1RM ({pct:.1f}% drop) on {dates[i]}", "fix": "verify data entry, or add deload/return note if intentional"})

    # Check 1: Exercise name duplicates
    exercises = [r["exercise"] for r in c.execute("SELECT DISTINCT exercise FROM sets").fetchall()]
    for a, b in itertools.combinations(exercises, 2):
        if _levenshtein(a, b) <= dup_dist:
            flags.append({"check": "duplicate_names", "severity": "low", "evidence": f"'{a}' vs '{b}' (Levenshtein <= {dup_dist})", "fix": "rename <old> <new>"})

    # Check 7: Stale open workouts
    stale = c.execute("""
        SELECT w.id, w.date FROM workouts w
        WHERE w.status = 'open'
          AND (date(w.date) < date('now') OR
               (SELECT MAX(created) FROM sets WHERE workout_id = w.id) < datetime('now', ?))
    """, (f"-{stale_hours} hours",)).fetchall()
    for s in stale:
        flags.append({"check": "stale_workout", "severity": "high", "evidence": f"workout {s['id']} from {s['date']} still open", "fix": "end with note, or delete-workout if empty"})

    # Check 5: Goal trajectory divergence (deterministic).
    for g in c.execute("SELECT * FROM goals WHERE status = 'active' ORDER BY id").fetchall():
        prog = goal_progress(c, dict(g))
        if prog["consecutive_misses"] >= 2:
            slippage_notes = c.execute(
                "SELECT DISTINCT w.id FROM workouts w JOIN sets s ON s.workout_id = w.id "
                "WHERE s.exercise = ? AND date(w.date) >= date(?) AND (w.notes LIKE '%slippage%' "
                "OR w.notes LIKE '%extend%' OR w.notes LIKE '%compress%' OR s.note LIKE '%slippage%')",
                (g["exercise"], g["created"][:10])).fetchall()
            if not slippage_notes:
                flags.append({"check": "goal_divergence", "severity": "high",
                              "evidence": f"goal {g['id']} ({g['exercise']} -> {g['target_e1rm']} by {g['deadline']}): "
                                          f"{prog['consecutive_misses']} consecutive sessions off trajectory",
                              "fix": f"goal rewrite {g['id']}, or extend the deadline conversation"})
        if prog["slippage"]:
            flags.append({"check": "goal_slippage", "severity": "medium",
                          "evidence": f"goal {g['id']} ({g['exercise']}): {prog['remaining']} sessions left "
                                      f"but split frequency fits fewer before {g['deadline']}",
                          "fix": f"extend the deadline or compress jumps, never silently"})

    # Check 8: Volume vs MEV, rolling window from constants (current week + back).
    # Every week in the window counts: weeks with no logged sets are 0, not
    # absent. Zero and low volume are separate flags; bad weeks are counted
    # across the whole window, a good week in between does not reset anything.
    from datetime import date, timedelta
    today = date.today()
    week_starts = [today - timedelta(days=today.weekday() + 7 * i) for i in range(vol_weeks - 1, -1, -1)]
    base = week_starts[0].isoformat()
    mev_bounds = {m: e["mev"] for m, e in constants["muscles"].items()}
    priorities = read_priorities(c)
    for muscle, mev in mev_bounds.items():
        rows = c.execute("""
            SELECT date(w.date) as day, COUNT(*) as sets
            FROM sets s
            JOIN workouts w ON w.id = s.workout_id
            JOIN set_muscles sm ON sm.set_id = s.id
            WHERE sm.muscle = ? AND date(w.date) >= ?
            GROUP BY day
        """, (muscle, base)).fetchall()
        per_day = {r["day"]: r["sets"] for r in rows}
        weekly = []
        for ws in week_starts:
            we = ws + timedelta(days=7)
            total = sum(n for d, n in per_day.items() if ws.isoformat() <= d < we.isoformat())
            weekly.append(total)
        counts = "[" + ", ".join(str(n) for n in weekly) + "]"
        zero_weeks, low_weeks = count_bad_weeks(weekly, mev)
        # A muscle explicitly marked deprioritize is intentionally held back:
        # its flags still stand (listed, never silently dropped) but drop one
        # severity level and carry the reason, so the audit reads as explained.
        deprioritized = priorities.get(muscle, {}).get("tier") == "deprioritize"
        suffix = " (priority: deprioritize, intentional)" if deprioritized else ""
        if zero_weeks >= vol_bad:
            flags.append({"check": "volume_zero", "severity": "medium" if deprioritized else "high",
                          "evidence": f"{muscle}: 0 sets in {zero_weeks} of last {vol_weeks} weeks {counts} (MEV {mev}){suffix}",
                          "fix": "add volume, or add Active rule explaining"})
        if low_weeks >= vol_bad:
            flags.append({"check": "volume_low", "severity": "low" if deprioritized else "medium",
                          "evidence": f"{muscle}: below MEV in {low_weeks} of last {vol_weeks} weeks {counts} (MEV {mev}){suffix}",
                          "fix": "add volume, or add Active rule explaining"})

    # Output report
    print(f"Audit complete: {len(flags)} flags (checks 2, 3, 6 are structurally impossible, see docs/AUDIT.md)")
    for i, f in enumerate(flags, 1):
        print(f"{i}. [{f['check']}] - {f['severity'].upper()}")
        print(f"   Evidence: {f['evidence']}")
        print(f"   Fix: {f['fix']}")
    print(json.dumps({"flags": flags, "skipped": []}))


def cmd_doctor():
    """Structural check: constants, DB, and dashboard agree. Non-correlated."""
    problems = []
    try:
        constants = load_constants()
    except SystemExit as e:
        print(json.dumps({"ok": False, "problems": [{"check": "constants_parse", "fix": str(e)}]}))
        sys.exit(1)
    root = ROOT
    charts = os.path.join(root, "dashboard", "src", "charts.ts")
    try:
        with open(charts) as f:
            charts_text = f.read()
        if "constants.json" not in charts_text:
            problems.append({"check": "dashboard_palette",
                             "fix": "dashboard/src/charts.ts must derive MC/GROUPS from ../../constants.json"})
    except OSError:
        problems.append({"check": "dashboard_palette", "fix": f"{charts} unreadable"})
    c = conn()
    for check, exercises in (
            ("sets_mapping", [r["exercise"] for r in c.execute(
                "SELECT DISTINCT exercise FROM sets WHERE exercise NOT IN (SELECT exercise FROM lift_muscle_map)").fetchall()]),
            ("split_mapping", sorted({m for d in split_day_order("active", c=c) for m in day_movements(d, c=c)
                                      if not c.execute("SELECT exercise FROM lift_muscle_map WHERE exercise = ?",
                                                       (m,)).fetchone()}))):
        for ex in exercises:
            problems.append({"check": check, "fix": f"map set \"{ex}\" <muscles>"})
    known_muscles = set(constants["muscles"]) | set(constants.get("untracked", []))
    stray = [r["muscle"] for r in c.execute("SELECT DISTINCT muscle FROM set_muscles").fetchall()
             if r["muscle"] not in known_muscles]
    for muscle in stray:
        problems.append({"check": "muscle_coverage",
                         "fix": f"logged muscle '{muscle}' is neither tracked nor untracked in constants.json"})
    rotation_row = c.execute("SELECT value FROM meta WHERE key = 'rotation'").fetchone()
    try:
        rotation = json.loads(rotation_row["value"]) if rotation_row else None
    except ValueError:
        rotation = None
    if not isinstance(rotation, list) or not rotation or not all(isinstance(d, str) for d in rotation):
        problems.append({"check": "rotation",
                         "fix": "meta.rotation must be a non-empty JSON array of day names (see meta show)"})
    else:
        split_days = {r["day"].lower() for r in c.execute("SELECT DISTINCT day FROM splits").fetchall()}
        for day in rotation:
            if day.lower() != "rest" and day.lower() not in split_days:
                problems.append({"check": "rotation",
                                 "fix": f"rotation day '{day}' matches no splits.day value (see split show)"})
    orphan_prog = c.execute(
        "SELECT workout_id, exercise FROM progression WHERE workout_id NOT IN (SELECT id FROM workouts)").fetchall()
    for r in orphan_prog:
        problems.append({"check": "progression_workout",
                         "fix": f"progression for '{r['exercise']}' points at missing workout {r['workout_id']}"})
    expected = set(re.findall(r"CREATE TABLE IF NOT EXISTS (\w+)", SCHEMA))
    live = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    if live != expected:
        problems.append({"check": "schema_drift",
                         "fix": f"live tables {sorted(live)} differ from SCHEMA {sorted(expected)}"})
    dump_file = os.path.join(os.path.dirname(os.path.abspath(db.DB)), "workouts.sql")
    try:
        with open(dump_file) as f:
            dump_text = f.read()
    except OSError:
        dump_text = None
    if dump_text is not None:
        dump_tables = set(re.findall(r"CREATE TABLE (?:IF NOT EXISTS )?(\w+)", dump_text))
        if dump_tables != expected:
            problems.append({"check": "dump_drift",
                             "fix": f"workouts.sql tables {sorted(dump_tables)} differ from SCHEMA "
                                    f"{sorted(expected)}; run log.py dump"})
    if problems:
        print(json.dumps({"ok": False, "problems": problems}, indent=2))
        sys.exit(1)
    print(json.dumps({"ok": True, "muscles": len(constants["muscles"])}))
