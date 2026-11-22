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
from .program import active_deloads, read_priorities, volume_block
from .sessions import break_threshold, last_done

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2, "info": 3}


def build_signals(c=None, volume=None):
    """Warning signs in words, worst first. Empty means all clear."""
    c = c or conn()
    constants = load_constants()
    thresholds = constants.thresholds
    today = date.today()
    out = []

    volume = volume if volume is not None else volume_block(c, today)
    days = volume["rotation_days"]
    windows = len(volume["starts"])
    if windows < 2:
        out.append({"severity": "info",
                    "text": f"not enough history for volume reads yet ({windows} "
                            f"{days}-day windows)"})
    tiers = {m: p.get("tier") for m, p in read_priorities(c).items()}
    for muscle, v in volume["muscles"].items():
        if v["status"] == "below_mev":
            demoted = tiers.get(muscle) == "deprioritize"
            intent = " (priority: deprioritize, intentional)" if demoted else ""
            if v["zero_rotations"] >= thresholds.volume_bad_rotations:
                evidence = f"0 sets in {v['zero_rotations']} of {windows}"
                tier = constants.muscles[muscle].tier
                if tier != "settled":
                    intent = f" (MEV tier: {tier})" + intent
                severity = "medium" if demoted else "high"
            else:
                evidence = f"under MEV in {v['low_rotations']} of {windows}"
                severity = "low" if demoted else "medium"
            out.append({"severity": severity,
                        "text": f"{muscle}: {evidence} {days}-day windows "
                                f"(MEV {v['mev']:.1f} sets per {days} days){intent}"})
        elif v["status"] == "above_mrv":
            out.append({"severity": "medium",
                        "text": f"{muscle}: averaging {v['avg_recent']:.1f} sets per {days} days "
                                f"(MRV {v['mrv']:.1f})"})

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
