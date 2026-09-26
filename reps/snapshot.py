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
                      lift_muscles, parse_active_split_days, read_priorities,
                      read_split, recent_average, rules_with_confirm, volume_block)
from .progression import format_target, latest as latest_progression, top_e1rm_by_date
from .records import personal_records
from .sessions import break_threshold, last_done, session_duration_min
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
        muscles = lift_muscles(c, ex) or []
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
        recent = recent_average(weekly)
        out.append({
            "muscle": muscle,
            "bands": {"mev": entry.mev, "mav": list(entry.mav) if entry.mav else None,
                      "mrv": entry.mrv},
            "weekly": weekly, "status": volume[muscle]["status"],
            "tier": priorities.get(muscle, {}).get("tier", "maintain"),
            "grouped": sorted(autoreg.get("grouped", {}).get(muscle, [])),
            "lift_share": share,
            "trained_weeks": sum(1 for n in weekly if n > 0),
            "avg_recent": round(recent, 1),
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
                    "slot_label": match["day"], "notes": w["notes"], "exercises": exercises,
                    "duration_min": session_duration_min([s["created"] for s in rows])})
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
    from .program import slot_rows as _slot_rows
    day_rows: dict = {}
    for r in _slot_rows(c, "active"):
        day_rows.setdefault(r["day"], []).append(r)
    order = [d for d in rotation if d in day_rows] + sorted(d for d in day_rows if d not in rotation)
    days = []
    for day in order:
        slots = []
        seen: list[str] = []
        for r in sorted(day_rows[day], key=lambda x: x["slot"]):
            moves = r["moves"]
            uniq: list[str] = []
            for m in moves:
                for mu in lift_muscles(c, m) or []:
                    if mu not in uniq:
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


def _fmt_num(v):
    if v is None:
        return "unset"
    return str(round(v)) if v >= 100 else f"{v:.1f}"


def _human_name(name):
    return (name or "").title()


def _out(title, summary, exercises=None, muscles=None, days=None):
    return {"title": title, "summary": summary,
            "affects_exercises": exercises or [], "affects_muscles": muscles or [],
            "affects_days": days or []}


def _describe_program(event, c):
    from .program import lift_muscles, parse_movements

    subject, before, after = event["subject"], event["before"], event["after"]
    day = subject.partition(":")[2] or subject
    b_slots = {s["slot"]: s for s in before.get("slots") or []}
    a_slots = {s["slot"]: s for s in after.get("slots") or []}
    diffs = [_slot_diff_text(b_slots.get(k), a_slots.get(k))
             for k in sorted(set(b_slots) | set(a_slots))]
    diffs = [d for d in diffs if d]
    summary = "; ".join(diffs[:2]) + ("; ..." if len(diffs) > 2 else "") \
        or "no slot changes"
    exercises = sorted({m for s in list(b_slots.values()) + list(a_slots.values())
                        for m in parse_movements(s["movements"])})
    muscles = sorted({mu for m in exercises for mu in lift_muscles(c, m) or []})
    return _out(f"{day} changed", summary, exercises, muscles, [day])


def _describe_priority(event, c):
    subject, before, after = event["subject"], event["before"], event["after"]
    before_t = before.get("tier") or "unset"
    after_t = after.get("tier") or "cleared"
    return _out(f"{_human_name(subject)} priority changed",
                f"{before_t} -> {after_t}", muscles=[subject])


def _describe_goal(event, c):
    from .program import lift_muscles

    subject, before, after = event["subject"], event["before"], event["after"]
    exercise = after.get("exercise") or before.get("exercise") or subject
    action = after.get("action") or "changed"
    muscles = lift_muscles(c, exercise) or []
    if action == "add":
        summary = (f"target {_fmt_num(after.get('target_e1rm'))} e1RM"
                   + (f" by {_fmt_d(after['deadline'])}" if after.get("deadline") else ""))
        return _out(f"{_human_name(exercise)} goal set", summary, [exercise], muscles)
    if action == "drop":
        summary = (f"was {_fmt_num(before.get('target_e1rm'))} e1RM"
                   + (f" by {_fmt_d(before['deadline'])}" if before.get("deadline") else ""))
        return _out(f"{_human_name(exercise)} goal dropped", summary, [exercise], muscles)
    parts = []
    if before.get("target_e1rm") != after.get("target_e1rm"):
        parts.append(f"{_fmt_num(before.get('target_e1rm'))} -> "
                     f"{_fmt_num(after.get('target_e1rm'))} e1RM")
    if before.get("deadline") != after.get("deadline"):
        old = _fmt_d(before["deadline"]) if before.get("deadline") else "unset"
        new = _fmt_d(after["deadline"]) if after.get("deadline") else "unset"
        parts.append(f"by {old} -> by {new}")
    if action == "rewrite" and not parts:
        parts.append("trajectory recut")
    return _out(f"{_human_name(exercise)} goal revised", "; ".join(parts),
                [exercise], muscles)


def _describe_deload(event, c):
    from .program import day_movements, lift_muscles

    subject, after = event["subject"], event["after"]
    scope, _, name = subject.partition(":")
    if scope == "lift":
        out = _out("", "", [name], lift_muscles(c, name) or [], [])
    else:
        moves = day_movements(name) or []
        muscles = sorted({mu for m in moves for mu in lift_muscles(c, m) or []})
        out = _out("", "", moves, muscles, [name])
    if after.get("action") == "clear":
        return {**out, "title": f"{_human_name(name)} deload cleared",
                "summary": "full volume resumed"}
    return {**out, "title": f"{_human_name(name)} deload started",
            "summary": "training volume down until cleared"}


def _describe_rule(event, c):
    from .program import lift_muscles

    before, after = event["before"], event["after"]
    action = after.get("action") or "changed"
    text = after.get("text") or before.get("text") or ""
    summary = text if len(text) <= 80 else text[:77] + "..."
    subj = (after.get("subject") or "").lower()
    exercises = [r["exercise"] for r in c.execute("SELECT exercise FROM lift").fetchall()]
    if subj in exercises:
        out = _out("", summary, [subj], lift_muscles(c, subj) or [])
    else:
        from .constants import load_constants
        out = _out("", summary, [], [subj] if subj in load_constants().muscles else [])
    titles = {"add": "Rule added", "archive": "Rule archived", "extend": "Rule extended"}
    return {**out, "title": titles.get(action, f"Rule {action}")}


def _describe_rotation(event, c):
    _ = c
    subject, before, after = event["subject"], event["before"], event["after"]
    if subject == "anchor":
        pos = after.get("position")
        when = _fmt_d(after["anchor_date"]) if after.get("anchor_date") else "unset"
        return _out("Schedule re-anchored", f"position {pos} from {when}")
    fmt = lambda rot: " / ".join(d if d is not None else "rest" for d in rot or [])
    if not before.get("rotation"):
        return _out("Rotation changed", f"set to {fmt(after.get('rotation'))}")
    return _out("Rotation changed",
                f"{fmt(before.get('rotation'))} -> {fmt(after.get('rotation'))}")


def describe_change(event, c):
    """Read-model projection of one state transition: human title, one-line
    before/after summary, and affected lifts/muscles/days for chart relevance.
    Titles and summaries render verbatim in the dashboard; the envelopes stay
    available for the expandable detail. One describer per domain, dispatched
    like history's revert appliers; names stay lowercase except display titles.
    """
    describer = {"program": _describe_program, "priority": _describe_priority,
                 "goal": _describe_goal, "deload": _describe_deload,
                 "rule": _describe_rule, "rotation": _describe_rotation}[event["domain"]]
    return describer(event, c)


def _slot_diff_text(b, a):
    if b is None:
        return f"slot {a['slot']} added: {a['movements']} x{a['sets']}"
    if a is None:
        return f"slot {b['slot']} removed: {b['movements']}"
    moves_changed = b["movements"] != a["movements"]
    sets_changed = b["sets"] != a["sets"]
    if moves_changed and sets_changed:
        return f"{b['movements']} {b['sets']} sets -> {a['movements']} {a['sets']} sets"
    if moves_changed:
        return f"slot {b['slot']}: {b['movements']} -> {a['movements']}"
    if sets_changed:
        return f"{b['movements']}: {b['sets']} sets -> {a['sets']} sets"
    return ""


def history_view(c):
    """Dashboard read model over state_change: described events (oldest
    first), one folded training state per event date, and coverage dates.
    The Worker serves this verbatim; the frontend selects, never folds."""
    from .history import coverage, list_changes, training_state_at
    from .observations import observation_defs
    from .vocab import HistoryDomain, values

    events = []
    for domain in values(HistoryDomain):
        events.extend(list_changes(domain))
    events.sort(key=lambda e: (e["date"], e["sequence"], e["id"]))
    described = []
    for e in events:
        described.append({**e, **describe_change(e, c)})
    states = [training_state_at(d) for d in sorted({e["date"] for e in events})]
    return {"events": described, "states": states, "coverage": coverage(),
            "defs": observation_defs()}


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


def _split_moves(text):
    # History rows (autoreg holds/changes) store the slot content as an
    # immutable TEXT fact; the live relation owner is split_slot_lift.
    # Splitting here is a sanctioned read-model projection for the snapshot.
    return [m.strip().lower() for m in text.split("/") if m.strip()]  # sanctioned: history read-model split


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
    gap_threshold = break_threshold()
    goals = goals_view(c, prog)
    hist = history_view(c)
    snap = {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "exported": datetime.now().isoformat(timespec="seconds"),
        "as_of": as_of,
        "constants": constants.model_dump(),
        "lifts": lifts_view(c, as_of, constants, prog, goals_by_ex, autoreg, priorities),
        "muscles": muscles_view(c, constants, priorities, autoreg, volume, starts),
        "sessions": sessions,
        "calendar": calendar_view(c, sessions, as_of, rotation, anchor, gap_threshold),
        "status": status_view(sessions, as_of, gap_threshold),
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
        "autoreg": {**autoreg, "holds": [
            {**h, "moves": _split_moves(h["movements"])} for h in autoreg.get("holds", [])]},
        "autoreg_changes": [{
            **dict(r),
            "before_moves": _split_moves(r["before_movements"]),
            "after_moves": _split_moves(r["after_movements"])} for r in c.execute(
            "SELECT id, date, action, day, slot, before_movements, before_sets, "
            "after_movements, after_sets, evidence, reverted_on FROM autoreg_changes "
            "ORDER BY id DESC LIMIT 20").fetchall()],
        "history": hist["events"],
        "history_states": hist["states"],
        "history_coverage": hist["coverage"],
        "observation_defs": hist["defs"],
    }
    return snap
