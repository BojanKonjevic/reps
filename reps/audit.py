import os
import re
from datetime import date

from .errors import RepsError

from . import db
from .adherence import parse_anchor
from .constants import load_constants
from .db import SCHEMA, conn
from .goals import goal_progress
from .muscles import _levenshtein
from .program import (count_bad_weeks, get_rotation, read_priorities)


def run_audit():
    """Run deterministic audit checks. Returns flags plus a readable report."""
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
               e1rm(s.weight, s.reps) as e1rm
        FROM sets s JOIN workouts w ON w.id = s.workout_id
        WHERE s.weight > 0 ORDER BY s.exercise, w.date, s.id
    """).fetchall()

    by_ex = {}
    for s in sets:
        by_ex.setdefault(s["exercise"], []).append(s)

    constants = load_constants()
    explained = tuple(constants.explained_keywords)
    thresholds = constants.thresholds
    drop_pct = thresholds.progression_drop_pct
    dup_dist = thresholds.duplicate_name_distance
    vol_weeks = thresholds.volume_window_weeks
    vol_bad = thresholds.volume_bad_weeks

    def jump_bound(reps):
        for band in constants.rep_bands:
            if band.max_reps is None:
                return None
            if reps <= band.max_reps:
                return band.jump_pct
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
            flags.append({"check": "duplicate_names", "severity": "low", "evidence": f"'{a}' vs '{b}' (Levenshtein <= {dup_dist})", "fix": "muscle_rename the duplicate into the canonical name"})

    # Check 7: Stale open workouts (one staleness definition, owned by sessions).
    from .sessions import staleness as _staleness
    for w in c.execute("SELECT * FROM workouts WHERE status = 'open'").fetchall():
        if _staleness(dict(w))["is_stale"]:
            flags.append({"check": "stale_workout", "severity": "high",
                          "evidence": f"workout {w['id']} from {w['date']} still open",
                          "fix": "session_end with note, or delete the workout if empty"})

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
                              "fix": f"goal_rewrite {g['id']}, or extend the deadline conversation"})
        if prog["slippage"]:
            flags.append({"check": "goal_slippage", "severity": "medium",
                          "evidence": f"goal {g['id']} ({g['exercise']}): {prog['remaining']} sessions left "
                                      f"but split frequency fits fewer before {g['deadline']}",
                          "fix": f"extend the deadline or compress jumps, never silently"})

    # Check 8: Volume vs MEV, rolling window from constants (current week + back).
    # Bad weeks count over the trained span only: weeks before the first
    # logged sets (any muscle) are absent, per-muscle leading zeros after
    # that are absent too, and a span never training the muscle counts only
    # when long enough to judge. A good week in between does not reset
    # anything. Bucketing is owned by reps/weeks.py; per-muscle counts by
    # weekly_volume; the span rules by span_start/trim_leading_zeros.
    from .program import weekly_volume as _weekly_volume, span_start as _span_start
    from .weeks import week_starts as _week_starts
    starts = [date.fromisoformat(s) for s in _week_starts(vol_weeks)]
    mev_bounds = {m: e.mev for m, e in constants.muscles.items()}
    priorities = read_priorities(c)
    span_weeklies = {m: _weekly_volume(c, m, starts) for m in mev_bounds}
    gstart = _span_start(list(span_weeklies.values()))
    for muscle, mev in mev_bounds.items():
        weekly = span_weeklies[muscle][gstart:]
        counts = "[" + ", ".join(str(n) for n in weekly) + "]"
        zero_weeks, low_weeks = count_bad_weeks(weekly, mev, vol_bad)
        # A muscle explicitly marked deprioritize is intentionally held back:
        # its flags still stand (listed, never silently dropped) but drop one
        # severity level and carry the reason, so the audit reads as explained.
        deprioritized = priorities.get(muscle, {}).get("tier") == "deprioritize"
        suffix = " (priority: deprioritize, intentional)" if deprioritized else ""
        if zero_weeks >= vol_bad:
            flags.append({"check": "volume_zero", "severity": "medium" if deprioritized else "high",
                          "evidence": f"{muscle}: 0 sets in {zero_weeks} of last {len(weekly)} weeks {counts} (MEV {mev}){suffix}",
                          "fix": "add volume, or add Active rule explaining"})
        if low_weeks >= vol_bad:
            flags.append({"check": "volume_low", "severity": "low" if deprioritized else "medium",
                          "evidence": f"{muscle}: below MEV in {low_weeks} of last {len(weekly)} weeks {counts} (MEV {mev}){suffix}",
                          "fix": "add volume, or add Active rule explaining"})

    lines = [f"Audit complete: {len(flags)} flags (checks 2, 3, 6 are structurally impossible, see docs/AUDIT.md)"]
    for i, f in enumerate(flags, 1):
        lines.append(f"{i}. [{f['check']}] - {f['severity'].upper()}")
        lines.append(f"   Evidence: {f['evidence']}")
        lines.append(f"   Fix: {f['fix']}")
    return {"flags": flags, "report": lines}


def run_doctor():
    """Structural check: constants, DB, and dashboard agree. Non-correlated.

    Referential checks deleted here are subsumed by FKs (each has a test that
    attempts the violation and expects a Refusal): sets/lift mapping,
    split/lift mapping, progression/workout linkage, rotation/split linkage.
    """
    problems = []
    try:
        constants = load_constants()
    except RepsError as e:
        raise RepsError(f"constants_parse: {e}")
    c = conn()
    known_muscles = set(constants.muscles) | set(constants.untracked)
    stray = [r["muscle"] for r in c.execute("SELECT DISTINCT muscle FROM lift_muscle").fetchall()
             if r["muscle"] not in known_muscles]
    for muscle in stray:
        problems.append({"check": "muscle_coverage",
                         "fix": f"logged muscle '{muscle}' is neither tracked nor untracked in constants.json"})
    rotation = get_rotation(c)
    anchor_row = c.execute("SELECT anchor_date, position FROM rotation_anchor WHERE id = 1").fetchone()
    if anchor_row is not None:
        _, problem = parse_anchor({"date": anchor_row["anchor_date"], "index": anchor_row["position"]},
                                  rotation)
        if problem:
            problems.append({"check": "rotation_anchor", "fix": problem})
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
                                    f"{sorted(expected)}; run maintenance_dump"})
    if problems:
        return {"ok": False, "problems": problems}
    return {"ok": True, "muscles": len(constants.muscles)}
