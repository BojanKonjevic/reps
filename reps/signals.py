"""Coach notes: deterministic warning signs as plain sentences.

No judgment is generated here, only presentation. Every line restates a
computed fact (volume classification, goal trajectory, autoreg streaks,
adherence drift, deload, break) that already exists elsewhere. Worst first.
"""

from datetime import date, timedelta

from .adherence import adherence_block
from .autoreg import autoreg_block
from .constants import load_constants
from .db import conn
from .goals import goal_progress
from .program import (active_deloads, classify_volume, count_bad_weeks,
                      recent_average)
from .sessions import break_threshold, last_done

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2, "info": 3}


def build_signals(c=None):
    """Warning signs in words, worst first. Empty means all clear."""
    c = c or conn()
    constants = load_constants()
    thresholds = constants.thresholds
    today = date.today()
    out = []

    vol_weeks = thresholds.volume_window_weeks
    from .weeks import week_starts as _week_starts
    week_starts = [date.fromisoformat(s) for s in _week_starts(vol_weeks)]
    sessions = c.execute(
        "SELECT COUNT(DISTINCT w.date) n FROM sets s "
        "JOIN workouts w ON w.id = s.workout_id WHERE date(w.date) >= ?",
        (week_starts[0].isoformat(),)).fetchone()["n"]
    if sessions < 2:
        out.append({"severity": "info",
                    "text": f"not enough history for volume reads yet ({sessions} sessions "
                            f"in {vol_weeks} weeks)"})
    else:
        vol_bad = thresholds.volume_bad_weeks
        from .program import span_start, weekly_volumes
        span_weeklies = weekly_volumes(c, list(constants.muscles), week_starts)
        gstart = span_start(list(span_weeklies.values()))
        from .program import read_priorities as _priorities
        tiers = {m: p.get("tier") for m, p in _priorities(c).items()}
        for muscle, entry in constants.muscles.items():
            weekly = span_weeklies[muscle][gstart:]
            status = classify_volume(weekly, entry.mev, entry.mrv, vol_bad)
            if status == "below_mev":
                zero_weeks, low_weeks = count_bad_weeks(weekly, entry.mev, vol_bad)
                tier_note = f" (MEV tier: {entry.tier})" if entry.tier != "settled" else ""
                # Parity with audit check 8: a deprioritize muscle still
                # reads, one severity lower and annotated, never silenced.
                demoted = tiers.get(muscle) == "deprioritize"
                intent = " (priority: deprioritize, intentional)" if demoted else ""
                if zero_weeks >= vol_bad:
                    out.append({"severity": "medium" if demoted else "high",
                                "text": f"{muscle}: 0 sets in {zero_weeks} of last {len(weekly)} "
                                        f"weeks (MEV {entry.mev}){tier_note}{intent}"})
                else:
                    out.append({"severity": "low" if demoted else "medium",
                                "text": f"{muscle}: under MEV in {low_weeks} of last {len(weekly)} "
                                        f"weeks (MEV {entry.mev}){intent}"})
            elif status == "above_mrv":
                avg = recent_average(weekly)
                out.append({"severity": "medium",
                            "text": f"{muscle}: averaging {avg:.1f}/wk over MRV {entry.mrv}"})

    for g in c.execute("SELECT * FROM goals WHERE status = 'active' ORDER BY id").fetchall():
        prog = goal_progress(c, dict(g))
        if prog["consecutive_misses"] >= 2:
            out.append({"severity": "high",
                        "text": f"{g['exercise']}: off trajectory {prog['consecutive_misses']} "
                                f"sessions running (goal {g['id']} to {g['target_e1rm']} by {g['deadline']})"})
        if prog["slippage"]:
            out.append({"severity": "medium",
                        "text": f"{g['exercise']}: {prog['remaining']} sessions left but the split "
                                f"fits fewer before {g['deadline']}"})

    auto = autoreg_block(c)
    for d in auto["drop_watch"]:
        out.append({"severity": "high",
                    "text": f"{d['exercise']}: e1RM down {abs(d['drops_pct'][0]):.1f}% then "
                            f"{abs(d['drops_pct'][1]):.1f}% back to back (3 counting sessions, "
                            f"reps <= {thresholds.e1rm_cap_reps}; normal variation can mimic this)"})
    for m in auto["miss_streaks"]:
        out.append({"severity": "medium",
                    "text": f"{m['exercise']}: {m['streak']} misses running"})

    adherence = adherence_block(c)
    if adherence is not None and adherence["drift"]:
        out.append({"severity": "medium",
                    "text": f"adherence drift: {adherence['drift_days']} non-done days, "
                            f"consider re-anchoring the rotation"})

    for d in active_deloads(c):
        out.append({"severity": "info", "text": f"deloading {d['scope']} {d['subject']}"})

    last = last_done(c)
    if last:
        gap = (today - date.fromisoformat(last["date"])).days
        if gap >= break_threshold():
            out.append({"severity": "medium",
                        "text": f"{gap}d since last session, no PR attempts until back"})

    out.sort(key=lambda e: (SEVERITY_ORDER[e["severity"]], e["text"]))
    return out
