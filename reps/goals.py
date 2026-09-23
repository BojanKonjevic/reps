import json
import sys
from datetime import date, datetime

from .constants import load_constants
from .db import conn
from .program import day_movements, parse_rotation, split_day_order
from .progression import top_e1rm_by_date


def goal_exercise_days(c, exercise):
    return [day for day in split_day_order("active", c=c) if exercise in day_movements(day, c=c)]


def sessions_possible_before(c, exercise, deadline):
    days_left = (date.fromisoformat(deadline) - date.today()).days
    if days_left < 0:
        return 0
    # One rotation slot counts as one calendar day (rest entries included),
    # so cycle length already prices in rest days.
    rotation = parse_rotation(c)
    cycle_days = len(rotation) if rotation else 7
    per_cycle = len(goal_exercise_days(c, exercise))
    return int(days_left / cycle_days * per_cycle + 0.5)


def build_checkpoints(start, target, n):
    # Session 1 is the already-logged baseline, so it checkpoints at start.
    if n <= 1:
        return [round(target, 1)]
    return [round(start + (target - start) * i / (n - 1), 1) for i in range(n)]


def goal_sessions(c, goal):
    """Post-goal training dates with the last pre-goal date as session-1 anchor.

    Same-day rows count as post-goal only if their sets were logged after the
    goal was created (set created timestamps vs goal created timestamp).
    """
    all_sessions = top_e1rm_by_date(c, goal["exercise"])
    created_day = goal["created"][:10]
    prior = [s for s in all_sessions if s[0] < created_day
             or (s[0] == created_day and (s[3] or "") < goal["created"])]
    current = [s for s in all_sessions if s not in prior and s[0] >= created_day]
    return (prior[-1:] + current) if prior or current else []


def goal_progress(c, goal):
    checkpoints = [r["target_e1rm"] for r in c.execute(
        "SELECT target_e1rm FROM goal_checkpoints WHERE goal_id = ? ORDER BY session_no", (goal["id"],)).fetchall()]
    sessions = goal_sessions(c, goal)
    completed = min(len(sessions), len(checkpoints))
    divergence = load_constants().thresholds.goal_divergence_pct
    consecutive_misses = 0
    for i in range(completed):
        _, actual, notes, _ = sessions[i]
        if "deload" in (notes or "").lower():
            consecutive_misses = 0
            continue
        # One-sided: only shortfall misses. Overperformance is signal, not failure.
        if (checkpoints[i] - actual) / checkpoints[i] * 100 > divergence:
            consecutive_misses += 1
        else:
            consecutive_misses = 0
    remaining = len(checkpoints) - completed
    slippage = remaining > sessions_possible_before(c, goal["exercise"], goal["deadline"])
    return {"checkpoints": checkpoints, "completed": completed,
            "actuals": [{"date": d, "e1rm": round(e, 1)} for d, e, _, _ in sessions[:completed]],
            "consecutive_misses": consecutive_misses, "on_track": consecutive_misses < 2,
            "remaining": remaining, "slippage": slippage,
            "next_checkpoint": checkpoints[completed] if completed < len(checkpoints) else None}


def goal_add(exercise, target_e1rm, deadline, target_desc="", start_e1rm=None):
    c = conn()
    exercise = (exercise or "").strip().lower()
    if not exercise:
        sys.exit("goal exercise is required")
    if not c.execute("SELECT exercise FROM lift_muscle_map WHERE exercise = ?", (exercise,)).fetchone():
        sys.exit(f"'{exercise}' has no mapping (run muscle_map_set first)")
    try:
        target_e1rm = float(target_e1rm)
    except (TypeError, ValueError):
        sys.exit("target e1RM must be a number")
    if target_e1rm <= 0:
        sys.exit("target e1RM must be positive")
    try:
        deadline = date.fromisoformat(deadline).isoformat()
    except ValueError:
        sys.exit("deadline must be YYYY-MM-DD")
    if date.fromisoformat(deadline) <= date.today():
        sys.exit("deadline must be in the future")
    if start_e1rm is None:
        top = c.execute(
            "SELECT CASE WHEN reps = 1 THEN weight ELSE weight * (1 + reps / 30.0) END AS e1rm "
            "FROM sets WHERE exercise = ? ORDER BY e1rm DESC LIMIT 1", (exercise,)).fetchone()
        if not top:
            sys.exit(f"no logged sets for '{exercise}', pass start_e1rm to seed the trajectory")
        start_e1rm = top["e1rm"]
    else:
        try:
            start_e1rm = float(start_e1rm)
        except (TypeError, ValueError):
            sys.exit("start e1RM must be a number")
    existing = c.execute("SELECT id FROM goals WHERE exercise = ? AND status = 'active'",
                         (exercise,)).fetchone()
    if existing:
        sys.exit(f"goal {existing['id']} already covers '{exercise}' (rewrite or drop it first)")
    n = sessions_possible_before(c, exercise, deadline)
    if n < 1:
        sys.exit(f"no '{exercise}' sessions fit before {deadline} at the current split frequency")
    now = datetime.now().isoformat(timespec="seconds")
    cur = c.execute("INSERT INTO goals (exercise, target_e1rm, target_desc, deadline, status, created) "
                    "VALUES (?, ?, ?, ?, 'active', ?)",
                    (exercise, target_e1rm, target_desc, deadline, now))
    gid = cur.lastrowid
    for i, cp in enumerate(build_checkpoints(start_e1rm, target_e1rm, n), 1):
        c.execute("INSERT INTO goal_checkpoints (goal_id, session_no, target_e1rm) VALUES (?, ?, ?)", (gid, i, cp))
    c.commit()
    print(json.dumps({"goal_id": gid, "exercise": exercise, "sessions": n,
                      "start_e1rm": round(start_e1rm, 1), "target_e1rm": target_e1rm, "deadline": deadline}))


def goal_show(goal_id=None):
    c = conn()
    if goal_id is not None:
        try:
            goal_id = int(goal_id)
        except (TypeError, ValueError):
            sys.exit("no such goal")
        goals = [dict(r) for r in c.execute("SELECT * FROM goals WHERE id = ?", (goal_id,)).fetchall()]
        if not goals:
            sys.exit("no such goal")
    else:
        goals = [dict(r) for r in c.execute("SELECT * FROM goals WHERE status = 'active' ORDER BY deadline").fetchall()]
    out = []
    for g in goals:
        entry = dict(g)
        entry.update(goal_progress(c, g))
        out.append(entry)
    print(json.dumps(out, indent=2))


def goal_rewrite(goal_id):
    c = conn()
    try:
        goal_id = int(goal_id)
    except (TypeError, ValueError):
        sys.exit("no such goal")
    goal = c.execute("SELECT * FROM goals WHERE id = ?", (goal_id,)).fetchone()
    if not goal:
        sys.exit("no such goal")
    goal = dict(goal)
    prog = goal_progress(c, goal)
    if prog["remaining"] <= 0:
        sys.exit("goal trajectory is complete, nothing to rewrite")
    sessions = goal_sessions(c, goal)
    anchor = sessions[prog["completed"] - 1][1] if prog["completed"] > 0 else prog["checkpoints"][0]
    fresh = build_checkpoints(anchor, goal["target_e1rm"], prog["remaining"])
    for i, cp in enumerate(fresh, prog["completed"] + 1):
        c.execute("UPDATE goal_checkpoints SET target_e1rm = ? WHERE goal_id = ? AND session_no = ?",
                  (cp, goal_id, i))
    c.commit()
    print(json.dumps({"goal_id": goal_id, "rewritten_from_session": prog["completed"] + 1, "checkpoints": fresh}))


def goal_drop(goal_id):
    c = conn()
    try:
        goal_id = int(goal_id)
    except (TypeError, ValueError):
        sys.exit("no such goal")
    cur = c.execute("UPDATE goals SET status = 'dropped' WHERE id = ?", (goal_id,))
    if cur.rowcount == 0:
        sys.exit("no such goal")
    c.commit()
    print(json.dumps({"dropped": goal_id}))
