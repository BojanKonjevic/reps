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
                      recent_average, weekly_volume)
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
    week_starts = [today - timedelta(days=today.weekday() + 7 * i)
                   for i in range(vol_weeks - 1, -1, -1)]
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
        for muscle, entry in constants.muscles.items():
            weekly = weekly_volume(c, muscle, week_starts)
            status = classify_volume(weekly, entry.mev, entry.mrv, vol_bad)
            if status == "below_mev":
                zero_weeks, low_weeks = count_bad_weeks(weekly, entry.mev)
                if zero_weeks >= vol_bad:
                    out.append({"severity": "high",
                                "text": f"{muscle}: 0 sets in {zero_weeks} of last {vol_weeks} "
                                        f"weeks (MEV {entry.mev})"})
                else:
                    out.append({"severity": "medium",
                                "text": f"{muscle}: under MEV in {low_weeks} of last {vol_weeks} "
                                        f"weeks (MEV {entry.mev})"})
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
                            f"{abs(d['drops_pct'][1]):.1f}% back to back"})
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
