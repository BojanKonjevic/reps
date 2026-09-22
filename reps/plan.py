import json
from datetime import date, datetime

from .adherence import adherence_block, expectation_context
from .autoreg import autoreg_block
from .constants import load_constants
from .db import conn, open_workout
from .goals import goal_progress
from .program import (active_deloads, compaction_due,
                    parse_active_split_days, parse_movements, parse_rotation,
                    priority_needs_confirm, read_priorities, read_split,
                    rules_with_confirm, volume_block)


def cmd_plan(slot=None, verbose=False):
    from datetime import timedelta
    c = conn()
    constants = load_constants()
    thresholds = constants["thresholds"]
    today = date.today()
    today_iso = today.isoformat()

    w = open_workout(c)
    rest_row = c.execute("SELECT * FROM workouts WHERE date = ? AND status = 'rest' ORDER BY id", (today_iso,)).fetchone()
    stale = None
    if w:
        try:
            age_days = (today - date.fromisoformat(w["date"])).days
        except ValueError:
            age_days = 0
        last = c.execute("SELECT created FROM sets WHERE workout_id = ? ORDER BY id DESC LIMIT 1", (w["id"],)).fetchone()
        last_created = last["created"] if last else None
        gap_over = False
        if last_created:
            try:
                gap_over = (datetime.now() - datetime.fromisoformat(last_created)).total_seconds() > thresholds["stale_workout_hours"] * 3600
            except ValueError:
                gap_over = False
        is_stale = w["date"] != today_iso or age_days >= thresholds["stale_workout_days"] or gap_over
        stale = {"is_stale": is_stale, "age_days": age_days, "last_set_created": last_created}
    last_done = c.execute(
        "SELECT date FROM workouts WHERE status = 'done' "
        "AND EXISTS (SELECT 1 FROM sets s WHERE s.workout_id = workouts.id) "
        "ORDER BY date DESC, id DESC LIMIT 1").fetchone()
    last_session = last_done["date"] if last_done else None
    gap_days = (today - date.fromisoformat(last_session)).days if last_session else None
    on_break = gap_days is not None and gap_days >= thresholds["break_days"] + 1

    days = parse_active_split_days(c)
    rotation = parse_rotation(c)
    slot_guess = {"day": None, "basis": "no history", "confidence": "low"}
    if slot:
        slot_guess = {"day": slot, "basis": "explicit --slot", "confidence": "high"}
    else:
        last_with_sets = c.execute(
            "SELECT w.date, w.id FROM workouts w WHERE w.status = 'done' "
            "AND EXISTS (SELECT 1 FROM sets s WHERE s.workout_id = w.id) "
            "ORDER BY w.date DESC, w.id DESC LIMIT 1").fetchone()
        if last_with_sets and days:
            trained = {r["exercise"] for r in c.execute(
                "SELECT DISTINCT exercise FROM sets WHERE workout_id = ?", (last_with_sets["id"],)).fetchall()}
            best_score = 0
            best_days = []
            for day, moves in days.items():
                score = len(trained & set(moves))
                if score > best_score:
                    best_score, best_days = score, [day]
                elif score == best_score and score > 0:
                    best_days.append(day)
            if len(best_days) > 1:
                slot_guess = {"day": None, "basis": f"last session matches {', '.join(best_days)} equally", "confidence": "low"}
                best_day = None
            else:
                best_day = best_days[0] if best_days else None
            if best_day and rotation:
                try:
                    idx = rotation.index(best_day)
                except ValueError:
                    idx = None
                if idx is not None:
                    skipped = []
                    j = (idx + 1) % len(rotation)
                    while rotation[j].lower() == "rest":
                        skipped.append(rotation[j])
                        j = (j + 1) % len(rotation)
                    nxt = rotation[j]
                    basis = f"last trained {best_day} ({last_with_sets['date']}), rotation {best_day}->{nxt}"
                    if skipped:
                        basis += " (rest day sits between)"
                    slot_guess = {"day": nxt, "basis": basis,
                                  "confidence": "high" if best_score == len(trained) else "medium"}
            elif best_day:
                slot_guess = {"day": None, "basis": f"last trained {best_day}, rotation unparseable", "confidence": "low"}

    adherence = adherence_block(c)
    if adherence is not None:
        # Second basis: what the rotation prescribed for today, regardless of
        # what the last session implies. The agent states the assumption either
        # way; the user confirms or overrides.
        ctx = expectation_context(c, rotation, adherence["anchor"], today_iso)
        slot_guess["expected"] = ctx
        second = f"expected today: {ctx['day']}"
        detail = []
        if ctx["last_done"]:
            detail.append(f"last done: {ctx['last_done']['day']} {ctx['last_done']['date']}")
        if ctx["missed"]:
            detail.append("missed " + ", ".join(f"{m['day']} {m['date']}" for m in ctx["missed"]))
        if detail:
            second += " (" + "; ".join(detail) + ")"
        slot_guess["basis"] += "; " + second

    volume = volume_block(c)

    retention = thresholds["ledger_retention_days"]
    cutoff = (today - timedelta(days=retention - 1)).isoformat()
    ledger = {}
    for muscle in constants["muscles"]:
        rows = c.execute("""
            SELECT w.date as day, COUNT(*) as sets
            FROM sets s
            JOIN workouts w ON w.id = s.workout_id
            JOIN set_muscles sm ON sm.set_id = s.id
            WHERE sm.muscle = ? AND date(w.date) >= ?
            GROUP BY day ORDER BY day
        """, (muscle, cutoff)).fetchall()
        ledger[muscle] = {"sessions": len(rows), "sets": sum(r["sets"] for r in rows),
                          "last_hit": rows[-1]["day"] if rows else None}

    lifts = []
    for r in c.execute("SELECT exercise, COUNT(*) n FROM sets GROUP BY exercise ORDER BY exercise").fetchall():
        top = c.execute(
            "SELECT weight, reps, CASE WHEN reps = 1 THEN weight ELSE weight * (1 + reps / 30.0) END AS e1rm "
            "FROM sets WHERE exercise = ? ORDER BY e1rm DESC LIMIT 1", (r["exercise"],)).fetchone()
        last = c.execute(
            "SELECT s.weight, s.reps FROM sets s JOIN workouts w ON w.id = s.workout_id "
            "WHERE s.exercise = ? ORDER BY w.date DESC, s.id DESC LIMIT 1", (r["exercise"],)).fetchone()
        lifts.append({"exercise": r["exercise"], "sets": r["n"],
                      "best_e1rm": round(top["e1rm"], 1) if top else None,
                      "last": dict(last) if last else None})

    progression = {r["exercise"]: {"verdict": r["verdict"], "next": r["next_target"],
                                                "direction": r["direction"], "workout_id": r["workout_id"]}
                   for r in c.execute(
                       "SELECT p.* FROM progression p JOIN (SELECT exercise, MAX(workout_id) m FROM progression "
                       "GROUP BY exercise) l ON l.exercise = p.exercise AND l.m = p.workout_id").fetchall()}
    priorities = read_priorities(c)
    deload = [dict(r) for r in active_deloads(c)]
    # Reading never consumes: consumption happens at `end` (flags touching the
    # closed session) or via explicit `flag consume`. Re-running plan is free.
    unconsumed = [dict(r) for r in c.execute("SELECT * FROM flags WHERE consumed_at IS NULL ORDER BY id").fetchall()]

    split_day = slot or slot_guess.get("day")
    split_section = None
    if split_day and read_split("active", split_day, c=c):
        slots = []
        for r in read_split("active", split_day, c=c):
            moves = parse_movements(r["movements"])
            entry = {"slot": r["slot"], "movements": moves, "sets": r["sets"],
                     "progression": {m: progression.get(m) for m in moves},
                     "flags": [f for f in unconsumed if f["subject"] in moves],
                     "goal": None, "notes": [], "muscles": []}
            for m in moves:
                entry["notes"].extend(n["note"] for n in c.execute(
                    "SELECT note FROM movement_notes WHERE exercise = ? ORDER BY id", (m,)).fetchall())
                mapping = c.execute("SELECT muscles FROM lift_muscle_map WHERE exercise = ?", (m,)).fetchone()
                if mapping:
                    entry["muscles"].extend(mu for mu in mapping["muscles"].split(",") if mu not in entry["muscles"])
            slots.append(entry)
        split_section = {"day": split_day, "slots": slots}

    goals = []
    by_exercise = {}
    for g in c.execute("SELECT * FROM goals WHERE status = 'active' ORDER BY deadline").fetchall():
        prog = goal_progress(c, dict(g))
        by_exercise[g["exercise"]] = {"id": g["id"], "next_checkpoint": prog["next_checkpoint"]}
        goals.append({"id": g["id"], "exercise": g["exercise"], "target_e1rm": g["target_e1rm"],
                      "deadline": g["deadline"], "next_checkpoint": prog["next_checkpoint"],
                      "on_track": prog["on_track"], "slippage": prog["slippage"],
                      "completed": prog["completed"]})
    if split_section:
        for slot_entry in split_section["slots"]:
            for m in slot_entry["movements"]:
                if m in by_exercise:
                    slot_entry["goal"] = by_exercise[m]
                    break

    rules = rules_with_confirm(c)
    needs_confirm = ([{"type": "rule", "id": r["id"], "subject": r["subject"], "expiry": r["expiry"]}
                      for r in rules if r["needs_confirm"]]
                     + priority_needs_confirm(c))

    autoreg = autoreg_block(c)

    bundle = {
        "today": {"open": w is not None,
                  "workout": {"id": w["id"], "date": w["date"], "status": w["status"]} if w else None,
                  "rest": bool(rest_row), "stale": stale,
                  "last_session": last_session, "gap_days": gap_days, "break": on_break},
        "slot_guess": slot_guess,
        "split": split_section,
        "goals": goals,
        "rules": {"active": rules, "needs_confirm": needs_confirm},
        "volume": volume,
        "ledger": ledger,
        "lifts": lifts,
        "progression": progression,
        "flags": unconsumed,
        "priority": priorities,
        "deload": deload if deload else None,
        "autoreg": autoreg,
        "adherence": adherence,
        "compaction": compaction_due(),
    }
    if verbose:
        lines = []
        if w:
            flag = "STALE" if stale["is_stale"] else "open"
            lines.append(f"workout {w['id']} {flag} (age {stale['age_days']}d, last set {stale['last_set_created']})")
        elif rest_row:
            lines.append("today is marked rest")
        else:
            lines.append("no open workout")
        lines.append(f"last session {last_session} ({gap_days}d ago)" + (" BREAK, no PR attempts" if on_break else ""))
        lines.append(f"slot guess: {slot_guess['day']} ({slot_guess['basis']}, {slot_guess['confidence']})")
        below = [m for m, v in volume.items() if v["status"] == "below_mev"]
        over = [m for m, v in volume.items() if v["status"] == "above_mrv"]
        lines.append(f"below MEV: {', '.join(below) if below else 'none'}")
        if over:
            lines.append(f"above MRV: {', '.join(over)}")
        if autoreg["permitted"] and (autoreg["miss_streaks"] or autoreg["drop_watch"]):
            parts = ([f"{m['exercise']} {m['streak']}xmiss" for m in autoreg["miss_streaks"]]
                     + [f"{d['exercise']} dropping" for d in autoreg["drop_watch"]])
            lines.append(f"autoreg signals: {', '.join(parts)}")
        if adherence is not None and adherence["drift"]:
            lines.append(f"adherence drift: {adherence['drift_days']} non-done days, "
                         f"consider rotation anchor <date> <day>")
        if bundle["compaction"]["due"]:
            lines.append("compaction due")
        print("\n".join(lines))
    else:
        print(json.dumps(bundle, indent=2))
