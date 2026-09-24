# SSOT owner: snapshot views (derived facts emitted for the dashboard).
# Consumers: sync.build_snapshot, dashboard (generated schemas only).
# Every classification here is computed in Python and tested with literal
# oracles; TS only selects, filters by UI state, formats, and lays out.

from datetime import date, datetime

from .adherence import adherence_snapshot, classify_date
from .autoreg import autoreg_block
from .constants import load_constants
from .models import SNAPSHOT_SCHEMA_VERSION
from .e1rm import e1rm
from .program import (active_deloads, deload_covers, get_rotation,
                      lift_muscles_csv, parse_active_split_days, read_priorities,
                      read_split, rules_with_confirm, volume_block)
from .progression import format_target, latest as latest_progression, top_e1rm_by_date
from .records import personal_records
from .sessions import last_done
from .signals import build_signals
from .slots import next_slot, slot_of_session
from .trends import is_slipping, is_stalling
from .weeks import week_start_of, week_starts

NOTE_HOT_KEYWORDS = ("pain", "sleep", "sore", "injury")


def _pr_flags(c):
    """set id -> is_pr across the whole history, per exercise in (created, id) order."""
    flags: dict = {}
    for r in c.execute("SELECT DISTINCT exercise FROM sets").fetchall():
        rows = c.execute(
            "SELECT id, weight, reps, created FROM sets WHERE exercise = ? ORDER BY created, id",
            (r["exercise"],)).fetchall()
        flags.update(personal_records([dict(s) for s in rows]))
    return flags


def _set_dates(c):
    return {r["id"]: r["date"] for r in
            c.execute("SELECT s.id, w.date FROM sets s JOIN workouts w ON w.id = s.workout_id").fetchall()}


def lifts_view(c, as_of, constants, prog, goals_by_ex, autoreg, priorities):
    t = constants.thresholds.model_dump()
    lifts = []
    for r in c.execute("SELECT exercise, COUNT(*) n FROM sets GROUP BY exercise ORDER BY exercise").fetchall():
        ex = r["exercise"]
        rows = c.execute(
            "SELECT s.id, s.weight, s.reps, s.created, w.date, w.id AS workout_id FROM sets s "
            "JOIN workouts w ON w.id = s.workout_id WHERE s.exercise = ? ORDER BY s.created, s.id",
            (ex,)).fetchall()
        hist = [dict(s) for s in rows]
        pr = personal_records(hist)
        by_day: dict = {}
        for s in hist:
            ev = e1rm(s["weight"], s["reps"])
            d = s["date"]
            if d not in by_day or ev > by_day[d]["e1rm"]:
                by_day[d] = {"date": d, "workout_id": s["workout_id"], "weight": s["weight"],
                             "reps": s["reps"], "e1rm": round(ev, 1), "set_id": s["id"]}
        sessions = []
        running = None
        for d in sorted(by_day):
            b = by_day[d]
            sessions.append({"date": d, "workout_id": b["workout_id"], "weight": b["weight"],
                             "reps": b["reps"], "e1rm": b["e1rm"], "is_pr": pr.get(b["set_id"], False),
                             "delta_e1rm": round(b["e1rm"] - running, 1) if running is not None else None})
            running = max(running, b["e1rm"]) if running is not None else b["e1rm"]
        series = [s["e1rm"] for s in sessions]
        best_row = max(hist, key=lambda s: e1rm(s["weight"], s["reps"]))
        best_ev = e1rm(best_row["weight"], best_row["reps"])
        last_row = hist[-1]
        last_pr = next((s["date"] for s in reversed(hist) if pr.get(s["id"])), None)
        csv = lift_muscles_csv(c, ex) or ""
        muscles = [m for m in csv.split(",") if m]  # sanctioned: validated read-model split
        notes = [n["note"] for n in c.execute(
            "SELECT note FROM movement_note WHERE exercise = ? ORDER BY id", (ex,)).fetchall()]
        p = prog.get(ex)
        tags: list[str] = []
        marks: list[dict] = []
        if ex in goals_by_ex:
            tags.append("goal")
            marks.append({"kind": "goal", "payload": {"goal_id": goals_by_ex[ex]}})
        slipping = is_slipping(series, t)
        if slipping:
            tags.append("slipping")
            marks.append({"kind": "slipping", "payload": {"drops_pct": ",".join(
                str(v) for v in slipping["drops_pct"])}})
        elif is_stalling(series, t):
            tags.append("stalling")
            marks.append({"kind": "stalling", "payload": {}})
        focus_muscles = [m for m in muscles
                         if priorities.get(m, {}).get("tier") == "priority"]
        if focus_muscles:
            tags.append("focus")
            marks.append({"kind": "focus", "payload": {"muscles": ",".join(sorted(focus_muscles))}})
        auto_reason = ("miss" if any(m["exercise"] == ex for m in autoreg.get("miss_streaks", []))
                       else "drop" if any(d["exercise"] == ex for d in autoreg.get("drop_watch", []))
                       else None)
        if auto_reason:
            tags.append("autoreg")
            marks.append({"kind": "autoreg", "payload": {"reason": auto_reason}})
        grouped_muscles = sorted(mu for mu, members in autoreg.get("grouped", {}).items()
                                 if ex in members)
        if grouped_muscles:
            tags.append("grouped")
            marks.append({"kind": "grouped", "payload": {"muscles": ",".join(grouped_muscles)}})
        lifts.append({
            "exercise": ex, "muscles": muscles, "notes": notes, "sessions": sessions,
            "best": {"weight": best_row["weight"], "reps": best_row["reps"],
                     "e1rm": round(best_ev, 1), "date": best_row["date"]},
            "last": {"weight": last_row["weight"], "reps": last_row["reps"],
                     "date": last_row["date"]},
            "last_pr_date": last_pr,
            "days_since_pr": (date.fromisoformat(as_of) - date.fromisoformat(last_pr)).days
            if last_pr else None,
            "progression": {"verdict": p["verdict"], "next": format_target(p["next_weight"], p["next_reps"]),
                            "next_weight": p["next_weight"], "next_reps": p["next_reps"],
                            "next_e1rm": round(e1rm(p["next_weight"], p["next_reps"]), 1),
                            "direction": p["direction"], "note": p["note"]} if p else None,
            "goal_id": goals_by_ex.get(ex),
            "tags": tags, "marks": marks,
            "sets_count": r["n"],
        })
    by_sets = sorted(lifts, key=lambda l: (-l.pop("sets_count"), l["exercise"]))
    for i, l in enumerate(by_sets):
        l["rank_default"] = i
    order = {"goal": 0, "slipping": 1, "stalling": 2, "autoreg": 3, "focus": 4}
    for i, l in enumerate(sorted(
            lifts, key=lambda l: (min([order[t] for t in l["tags"] if t in order], default=5),
                                  l["rank_default"]))):
        l["rank_attention"] = i
    return sorted(lifts, key=lambda l: l["exercise"])


def muscles_view(c, constants, priorities, autoreg, volume, starts):
    cutoff = starts[0]
    per_ex_muscle: dict = {}
    for r in c.execute(
            "SELECT s.exercise, sm.muscle, COUNT(*) n FROM sets s "
            "JOIN workouts w ON w.id = s.workout_id JOIN set_muscle sm ON sm.set_id = s.id "
            "WHERE date(w.date) >= ? GROUP BY s.exercise, sm.muscle", (cutoff,)).fetchall():
        per_ex_muscle.setdefault(r["muscle"], []).append((r["exercise"], r["n"]))
    out = []
    for muscle, entry in constants.muscles.items():
        weekly = volume[muscle]["weekly"]
        total = sum(n for _, n in per_ex_muscle.get(muscle, []))
        share = [{"exercise": ex, "sets": n, "share": round(n / total, 3) if total else 0.0}
                 for ex, n in sorted(per_ex_muscle.get(muscle, []), key=lambda e: -e[1])]
        recent = weekly[-4:] if len(weekly) >= 4 else weekly
        out.append({
            "muscle": muscle,
            "bands": {"mev": entry.mev, "mav": list(entry.mav) if entry.mav else None,
                      "mrv": entry.mrv},
            "weekly": weekly, "status": volume[muscle]["status"],
            "tier": priorities.get(muscle, {}).get("tier", "maintain"),
            "grouped": sorted(autoreg.get("grouped", {}).get(muscle, [])),
            "lift_share": share,
            "trained_weeks": sum(1 for n in weekly if n > 0),
            "avg_recent": round(sum(recent) / len(recent), 1) if recent else 0,
        })
    return out


def sessions_view(c, days, flags):
    out = []
    history = [dict(r) for r in
               c.execute("SELECT scope, subject, set_on, cleared_on FROM deload_state").fetchall()]
    for w in c.execute("SELECT * FROM workouts ORDER BY date, id").fetchall():
        rows = c.execute("SELECT * FROM sets WHERE workout_id = ? ORDER BY id", (w["id"],)).fetchall()
        ex_order: list[str] = []
        by_ex: dict = {}
        for s in rows:
            by_ex.setdefault(s["exercise"], []).append(s)
            if s["exercise"] not in ex_order:
                ex_order.append(s["exercise"])
        match = slot_of_session(ex_order, days)
        exercises = []
        at_date = [d for d in history
                   if d["set_on"] <= w["date"]
                   and (d["cleared_on"] is None or d["cleared_on"] > w["date"])]
        for n0, ex in enumerate(ex_order):
            sets = []
            for i, s in enumerate(by_ex[ex], 1):
                ev = e1rm(s["weight"], s["reps"])
                sets.append({"n": i, "w": s["weight"], "r": s["reps"],
                             "e": round(ev, 1), "pr": bool(flags.get(s["id"], False)),
                             "note": s["note"]})
            exercises.append({"exercise": ex,
                              "deload": bool(deload_covers(at_date, ex, days)),
                              "sets": sets})
        out.append({"date": w["date"], "workout_id": w["id"], "status": w["status"],
                    "slot_label": match["day"], "notes": w["notes"], "exercises": exercises})
    return out


def status_view(sessions, as_of, break_threshold):
    today = [s for s in sessions if s["date"] == as_of]
    trained = sorted(s["date"] for s in sessions if s["exercises"])
    last = trained[-1] if trained else None
    gap = (date.fromisoformat(as_of) - date.fromisoformat(last)).days if last else None
    on_break = bool(gap is not None and gap >= break_threshold)
    return {"open_today": any(s["status"] == "open" for s in today),
            "rest_today": bool(today) and all(s["status"] == "rest" for s in today),
            "last_trained": last, "break_days": gap if on_break else None,
            "on_break": on_break}


def calendar_view(c, sessions, as_of, rotation, anchor, break_threshold):
    trained_dates = sorted({s["date"] for s in sessions if s["exercises"]})
    rest_dates = {r["date"] for r in
                  c.execute("SELECT date FROM workouts WHERE status = 'rest'").fetchall()}
    if not trained_dates and not rest_dates:
        return []
    first = min((trained_dates + sorted(rest_dates)) or [as_of])
    days = []
    d0 = date.fromisoformat(first)
    d1 = date.fromisoformat(as_of)
    by_date = {s["date"]: s for s in sessions if s["exercises"]}
    step = d0
    while step <= d1:
        iso = step.isoformat()
        sess = by_date.get(iso)
        status = expected = None
        if anchor and rotation:
            verdict = classify_date(c, rotation, anchor, iso)
            status, expected = verdict["status"], verdict["expected"]
        if sess:
            kind = "trained"
        elif iso in rest_dates:
            kind = "rest"
        elif status == "missed":
            kind = "missed"
        else:
            kind = "empty"
        prev = next((t for t in reversed(trained_dates) if t < iso), None)
        gap = (step - date.fromisoformat(prev)).days if prev else 0
        lines: list[str] = []
        if sess:
            shown = 0
            for ex in sess["exercises"]:
                for s in ex["sets"]:
                    if shown < 8:
                        lines.append(f"{ex['exercise']} {s['w']:g}x{s['r']}"
                                     + (" (PR)" if s["pr"] else ""))
                        shown += 1
            total = sum(len(ex["sets"]) for ex in sess["exercises"])
            if total > shown:
                lines.append(f"+{total - shown} more sets")
        elif kind == "missed":
            lines.append(f"expected {expected}, nothing logged")
        elif kind == "rest":
            lines.append("rest")
        days.append({"date": iso, "kind": kind,
                     "slot_label": sess["slot_label"] if sess else None,
                     "has_pr": bool(sess and any(s["pr"] for ex in sess["exercises"]
                                              for s in ex["sets"])),
                     "break_after_gap": prev is not None and gap >= break_threshold,
                     "adherence_status": status, "expected": expected,
                     "hover": {"lines": lines}})
        step = date.fromordinal(step.toordinal() + 1)
    return days


def bodyweight_view(c, avg_days, gap_days):
    rows = c.execute("SELECT date, kg FROM bodyweight ORDER BY date, id").fetchall()
    out = []
    prev = None
    for r in rows:
        d = date.fromisoformat(r["date"])
        win = [q["kg"] for q in rows
               if 0 <= (d - date.fromisoformat(q["date"])).days < avg_days]
        gap_before = (d - date.fromisoformat(prev)).days if prev else None
        out.append({"date": r["date"], "kg": r["kg"],
                    "avg7": round(sum(win) / len(win), 1) if win else None,
                    "gap_before": gap_before,
                    "gap": bool(gap_before is not None and gap_before > gap_days)})
        prev = r["date"]
    return out


def program_view(c, rotation, anchor, priorities):
    focus = {m for m, p in priorities.items() if p.get("tier") == "priority"}
    day_rows: dict = {}
    for r in read_split("active", c=c):
        day_rows.setdefault(r["day"], []).append(r)
    order = [d for d in rotation if d in day_rows] + sorted(d for d in day_rows if d not in rotation)
    days = []
    for day in order:
        slots = []
        seen: list[str] = []
        for r in sorted(day_rows[day], key=lambda x: x["slot"]):
            from .program import parse_movements
            moves = parse_movements(r["movements"])
            uniq: list[str] = []
            for m in moves:
                csv = lift_muscles_csv(c, m) or ""
                for mu in csv.split(","):  # sanctioned: validated read-model split
                    if mu and mu not in uniq:
                        uniq.append(mu)
            slots.append({"slot": r["slot"], "moves": moves, "sets": r["sets"],
                          "muscles": uniq, "focus": [m for m in uniq if m in focus]})
            for m in uniq:
                if m not in seen:
                    seen.append(m)
        days.append({"day": day, "muscles": seen, "slots": slots})
    return {"rotation": rotation,
            "anchor": {"date": anchor["date"], "index": anchor["index"]} if anchor else None,
            "days": days}


def next_up_view(c, prog):
    last = last_done(c)
    if not last:
        return {"day": None, "basis": "no history", "rows": [],
                "empty": "log a session and the next slot appears here"}
    days = parse_active_split_days(c)
    trained = [r["exercise"] for r in c.execute(
        "SELECT DISTINCT exercise FROM sets WHERE workout_id = ?", (last["id"],)).fetchall()]
    match = slot_of_session(trained, days)
    if match["day"] is None:
        return {"day": None, "basis": "last session is ambiguous", "rows": [],
                "empty": "log a session and the next slot appears here"}
    rotation = get_rotation(c)
    nxt = next_slot(match["day"], rotation)
    if nxt["day"] is None or not days.get(nxt["day"]):
        if not days:
            return {"day": None, "basis": nxt["basis"], "rows": [],
                    "empty": "no program synced yet"}
        return {"day": None, "basis": nxt["basis"], "rows": [],
                "empty": "log a session and the next slot appears here"}
    rows = []
    for m in days[nxt["day"]]:
        last_hit = c.execute(
            "SELECT s.weight, s.reps, w.date FROM sets s JOIN workouts w ON w.id = s.workout_id "
            "WHERE s.exercise = ? ORDER BY w.date DESC, s.id DESC LIMIT 1", (m,)).fetchone()
        p = prog.get(m)
        rows.append({"movement": m,
                     "last": {"weight": last_hit["weight"], "reps": last_hit["reps"],
                              "date": last_hit["date"]} if last_hit else None,
                     "target": format_target(p["next_weight"], p["next_reps"]) if p else None})
    return {"day": nxt["day"], "basis": nxt["basis"], "rows": rows, "empty": None}


def goals_view(c, prog):
    from .goals import goal_progress
    out = []
    for g in c.execute("SELECT * FROM goals WHERE status = 'active' ORDER BY deadline").fetchall():
        gd = dict(g)
        p = goal_progress(c, gd)
        actuals = p["actuals"]
        percent = None
        if actuals and p["checkpoints"]:
            span = g["target_e1rm"] - p["checkpoints"][0]
            if span > 0:
                percent = max(0.0, min(100.0, round(
                    (actuals[-1]["e1rm"] - p["checkpoints"][0]) / span * 100, 1)))
        tops: dict = {}
        for day, ev, _notes, _created in top_e1rm_by_date(c, g["exercise"]):
            row = c.execute(
                "SELECT s.weight, s.reps FROM sets s JOIN workouts w ON w.id = s.workout_id "
                "WHERE s.exercise = ? AND w.date = ? ORDER BY e1rm(s.weight, s.reps) DESC LIMIT 1",
                (g["exercise"], day)).fetchone()
            if row:
                tops[day] = {"weight": row["weight"], "reps": row["reps"]}
        out.append({"id": g["id"], "exercise": g["exercise"], "target_e1rm": g["target_e1rm"],
                    "target_desc": g["target_desc"], "deadline": g["deadline"],
                    "status": g["status"], "created": g["created"],
                    "checkpoints": p["checkpoints"], "completed": p["completed"],
                    "actuals": p["actuals"], "consecutive_misses": p["consecutive_misses"],
                    "on_track": p["on_track"], "remaining": p["remaining"],
                    "slippage": p["slippage"], "next_checkpoint": p["next_checkpoint"],
                    "percent": percent, "top_by_date": tops})
    _ = prog
    return out


def adherence_view(c):
    snap = adherence_snapshot(c)
    if not snap:
        return None
    weeks: dict = {}
    for d in snap["days"]:
        key = week_start_of(d["date"])
        w = weeks.setdefault(key, {"week_start": key, "trained": 0, "expected": 0})
        if d["expected"].lower() != "rest":
            w["expected"] += 1
        if d["status"] in ("done", "swapped"):
            w["trained"] += 1
    snap["weeks"] = [weeks[k] for k in sorted(weeks)]
    return snap


def _fmt_d(dstr):
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return f"{months[int(dstr[5:7]) - 1]} {int(dstr[8:10])}"


def recent_notes_view(c, count):
    noted: dict = {}
    for w in c.execute("SELECT date, notes FROM workouts WHERE notes != '' ORDER BY date, id").fetchall():
        noted[w["date"]] = w["notes"]
    set_dates = _set_dates(c)
    for s in c.execute("SELECT id, exercise, note FROM sets WHERE note != '' ORDER BY created, id").fetchall():
        d = set_dates.get(s["id"], "")
        if d:
            noted[d] = (noted[d] + " / " if d in noted else "") + f"{s['exercise']}: {s['note'].strip()}"
    out = []
    for d in sorted(noted)[-count:]:
        low = noted[d].lower()
        out.append({"date": d, "text": _fmt_d(d) + ": " + noted[d],
                    "hot": any(k in low for k in NOTE_HOT_KEYWORDS)})
    return out


def build_views(c):
    """Assemble the full v2 snapshot payload (unvalidated)."""
    constants = load_constants()
    as_of = date.today().isoformat()
    rotation = get_rotation(c)
    anchor = None
    try:
        from .adherence import get_anchor
        anchor = get_anchor(c)
    except Exception:
        anchor = None
    prog = latest_progression(c)
    goals_active = [dict(g) for g in
                    c.execute("SELECT * FROM goals WHERE status = 'active' ORDER BY deadline").fetchall()]
    goals_by_ex = {g["exercise"]: g["id"] for g in goals_active}
    priorities = read_priorities(c)
    autoreg = autoreg_block(c)
    volume = volume_block(c)
    starts = week_starts(constants.thresholds.volume_window_weeks)
    days = parse_active_split_days(c)
    flags = _pr_flags(c)
    sessions = sessions_view(c, days, flags)
    break_threshold = constants.thresholds.break_days + 1
    goals = goals_view(c, prog)
    snap = {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "exported": datetime.now().isoformat(timespec="seconds"),
        "as_of": as_of,
        "constants": constants.model_dump(),
        "lifts": lifts_view(c, as_of, constants, prog, goals_by_ex, autoreg, priorities),
        "muscles": muscles_view(c, constants, priorities, autoreg, volume, starts),
        "sessions": sessions,
        "calendar": calendar_view(c, sessions, as_of, rotation, anchor, break_threshold),
        "status": status_view(sessions, as_of, break_threshold),
        "volume_history": {"week_starts": starts,
                           "by_muscle": {m: volume[m]["weekly"] for m in volume}},
        "bodyweight": bodyweight_view(c, constants.thresholds.bodyweight_avg_days,
                                       constants.thresholds.bodyweight_gap_days),
        "program": program_view(c, rotation, anchor, priorities),
        "next_up": next_up_view(c, prog),
        "goals": goals,
        "adherence": adherence_view(c),
        "signals": [dict(s) for s in build_signals(c)],
        "recent_notes": recent_notes_view(c, constants.thresholds.recent_notes_count),
        "rules": rules_with_confirm(c),
        "flags": [dict(r) for r in
                  c.execute("SELECT * FROM flags WHERE consumed_at IS NULL ORDER BY id").fetchall()],
        "deload": [dict(r) for r in active_deloads(c)],
        "priority": priorities,
        "autoreg": autoreg,
        "autoreg_changes": [dict(r) for r in c.execute(
            "SELECT id, date, action, day, slot, before_movements, before_sets, "
            "after_movements, after_sets, evidence, reverted_on FROM autoreg_changes "
            "ORDER BY id DESC LIMIT 20").fetchall()],
    }
    return snap
