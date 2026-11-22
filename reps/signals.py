"""Coach notes: deterministic warning signs as plain sentences.

No judgment is generated here, only presentation. Every line restates a
computed fact (volume classification, goal trajectory, autoreg streaks,
adherence drift, deload, break) that already exists elsewhere. Worst first.
"""

from datetime import date

from .adherence import adherence_block
from .autoreg import autoreg_block
from .blocks import current_block
from .constants import load_constants
from .db import conn
from .goals import goal_progress
from .history import list_changes, value_at
from .program import active_deloads, read_priorities, read_split, volume_block
from .sessions import break_threshold, last_done

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2, "info": 3}


def _ordered(signals):
    return sorted(signals, key=lambda e: (SEVERITY_ORDER[e["severity"]], e["text"]))


def _volume_signals(volume, constants, tiers):
    days = volume["rotation_days"]
    windows = len(volume["starts"])
    thresholds = constants.thresholds
    out = []
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

    return out


def _drop_signal(exercise, drops, cap):
    return {"severity": "high",
            "text": f"{exercise}: e1RM down {abs(drops[0]):.1f}% then "
                    f"{abs(drops[1]):.1f}% back to back (3 counting sessions, "
                    f"reps <= {cap}; normal variation can mimic this)"}


def block_signals(c, block, comparisons, rotation):
    """Review a finished block using only its logged volume and lift trends."""
    constants = load_constants()
    end = block["end_date"]
    volume = volume_block(c, date.fromisoformat(end), since=block["start_date"],
                          rotation=rotation, completed_only=True)
    history = {}
    for change in list_changes("priority", c=c):
        history.setdefault(change["subject"], []).append(change)
    tiers = {m: value_at(changes, end, "tier") for m, changes in history.items()}
    out = _volume_signals(volume, constants, tiers)
    for exercise, trend in comparisons.items():
        if trend["slipping"]:
            out.append(_drop_signal(exercise, trend["slipping"], constants.thresholds.e1rm_cap_reps))
        elif trend["stalling"]:
            out.append({"severity": "medium",
                        "text": f"{exercise}: estimated 1RM stalled at block end"})
    return _ordered(out)


def build_signals(c=None, *, auto=None):
    """Live warning signs for the active block, worst first."""
    c = c or conn()
    today = date.today()
    block = current_block(c, today.isoformat())
    if block is None:
        return []
    constants = load_constants()
    thresholds = constants.thresholds
    start = block["start_date"]
    volume = volume_block(c, today, since=start, completed_only=True, include_plan=True)
    days = volume["rotation_days"]
    windows = len(volume["starts"])
    tiers = {m: p.get("tier") for m, p in read_priorities(c).items()}
    out = _volume_signals(volume, constants, tiers)
    if windows < thresholds.volume_bad_rotations:
        out.append({"severity": "info",
                    "text": f"not enough history for volume reads yet ({windows} complete "
                            f"{days}-day windows in this block)"})
    if read_split("active", c=c):
        for muscle, v in volume["muscles"].items():
            if v["planned_below_mev"]:
                demoted = tiers.get(muscle) == "deprioritize"
                intent = " (priority: deprioritize, intentional)" if demoted else ""
                out.append({"severity": "low" if demoted else "medium",
                            "text": f"{muscle}: current split programs {v['planned_sets']} sets per {days} days "
                                    f"(under MEV {v['mev']:.2f}){intent}"})

    for g in c.execute("SELECT * FROM goals WHERE status = 'active' ORDER BY id").fetchall():
        prog = goal_progress(c, dict(g))
        misses = min(prog["consecutive_misses"], sum(a["date"] >= start for a in prog["actuals"]))
        if misses >= 2:
            out.append({"severity": "high",
                        "text": f"{g['exercise']}: off trajectory {misses} "
                                f"sessions running (goal {g['id']} to {g['target_e1rm']} by {g['deadline']})"})
        if prog["slippage"]:
            out.append({"severity": "medium",
                        "text": f"{g['exercise']}: {prog['remaining']} sessions left but the split "
                                f"fits fewer before {g['deadline']}"})

    auto = autoreg_block(c) if auto is None else auto
    for d in auto["drop_watch"]:
        out.append(_drop_signal(d["exercise"], d["drops_pct"], thresholds.e1rm_cap_reps))
    for m in auto["miss_streaks"]:
        out.append({"severity": "medium",
                    "text": f"{m['exercise']}: {m['streak']} misses running"})

    adherence = adherence_block(c, since=start)
    if adherence is not None and adherence["drift"]:
        out.append({"severity": "medium",
                    "text": f"adherence drift: {adherence['drift_days']} non-done days, "
                            f"consider re-anchoring the rotation"})

    for d in active_deloads(c):
        out.append({"severity": "info", "text": f"deloading {d['scope']} {d['subject']}"})

    last = last_done(c)
    if last and last["date"] >= start:
        gap = (today - date.fromisoformat(last["date"])).days
        if gap >= break_threshold():
            out.append({"severity": "medium",
                        "text": f"{gap}d since last session, no PR attempts until back"})

    return _ordered(out)
