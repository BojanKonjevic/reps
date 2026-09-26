# SSOT owner: state-change history (shared append-only record of meaningful
# training-system transitions, plus reconstruction at a point in time).
# Consumers: MCP history_* tools, observe program_activity, future UI.
# Autoreg keeps its own ledger by sanctioned exception (see docs/SSOT.md).

"""Shared state-change history across domains.

One table, domain expressed as data (a closed HistoryDomain vocabulary),
payload shapes per domain validated on read through the Pydantic
discriminated models in reps/models.py. Original rows are never rewritten;
a reversal is a new row with reverses pointing back, and the old tip row
gets superseded_by set when it had none.

Two deliberate deviations from the spec's Part II defaults, both required by
Part I invariants: history_state exists alongside the three named tools
because reconstructing state at an arbitrary point (Part I section 11) is
not achievable by listing transitions and folding them agent-side, which is
exactly the bookkeeping the spec moves out of the LLM. And all six domains
land together because the shared mechanism makes each one a payload shape
plus thin wiring; shipping two now and four later is how per-domain revert
semantics drift apart, the failure Part II section 25 names explicitly.
"""

import json
from datetime import date, datetime

from .db import conn
from .errors import RepsError
from .vocab import HistoryDomain, values


def _check_domain(domain):
    if domain not in values(HistoryDomain):
        raise RepsError(f"domain must be one of {', '.join(values(HistoryDomain))}")
    return domain


def _check_day(day):
    try:
        return date.fromisoformat(day).isoformat()
    except (ValueError, TypeError):
        raise RepsError("date must be YYYY-MM-DD")


def record_change(c, domain, subject, before, after, evidence="", reverses=None):
    """Append one state transition. before/after are per-domain dicts."""
    _check_domain(domain)
    subject = (subject or "").strip()
    if not isinstance(before, dict) or not isinstance(after, dict):
        raise RepsError("history payloads must be objects")
    now = datetime.now().isoformat(timespec="seconds")
    today = date.today().isoformat()
    seq = c.execute("SELECT COUNT(*) n FROM state_change WHERE domain = ? AND subject = ? AND date = ?",
                    (domain, subject, today)).fetchone()["n"]
    cur = c.execute(
        "INSERT INTO state_change (domain, subject, date, created, before_json, after_json, "
        "evidence, reverses, sequence) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (domain, subject, today, now,
         json.dumps(before, sort_keys=True), json.dumps(after, sort_keys=True),
         evidence or "", reverses, seq))
    return {"change_id": cur.lastrowid}


def backfill_change(domain, subject, before, after, day, evidence=""):
    """Append one backdated transition for user-reported past state.

    Effective date is explicit (never today by default): the row is active
    for queries on that date and thereafter until superseded, exactly like a
    contemporaneous record. Envelopes validate against the domain shape at
    write time, so a malformed backfill fails loudly instead of poisoning
    the trail. Never invents state: before/after come from the caller (the
    user report), and future dates are refused. Touches history only, never
    live tables; set live state through the owning domain operation.
    """
    from .models import validate_history_payload

    _check_domain(domain)
    subject = (subject or "").strip()
    if not subject:
        raise RepsError("backfill needs a subject (unscoped rows cannot fold)")
    if not isinstance(before, dict) or not isinstance(after, dict):
        raise RepsError("history payloads must be objects")
    day = _check_day(day)
    if day > date.today().isoformat():
        raise RepsError("backfill date must not be in the future")
    try:
        validate_history_payload(domain, before)
        validate_history_payload(domain, after)
    except ValueError as e:
        raise RepsError(f"history payload invalid: {e}")
    c = conn()
    now = datetime.now().isoformat(timespec="seconds")
    seq = c.execute("SELECT COUNT(*) n FROM state_change WHERE domain = ? AND subject = ? AND date = ?",
                    (domain, subject, day)).fetchone()["n"]
    cur = c.execute(
        "INSERT INTO state_change (domain, subject, date, created, before_json, after_json, "
        "evidence, reverses, sequence) VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?)",
        (domain, subject, day, now,
         json.dumps(before, sort_keys=True), json.dumps(after, sort_keys=True),
         evidence or "", seq))
    c.commit()
    return {"change_id": cur.lastrowid}


def _shape(row):
    from .models import validate_history_payload

    entry = {"id": row["id"], "domain": row["domain"], "subject": row["subject"],
             "date": row["date"], "created": row["created"],
             "evidence": row["evidence"], "superseded_by": row["superseded_by"],
             "reverses": row["reverses"], "sequence": row["sequence"]}
    try:
        entry["before"] = validate_history_payload(row["domain"], json.loads(row["before_json"]))
        entry["after"] = validate_history_payload(row["domain"], json.loads(row["after_json"]))
    except ValueError as e:
        raise RepsError(f"history row {row['id']} failed payload validation: {e}")
    return entry


def list_changes(domain, subject="", since="", until=""):
    """Transitions for a domain (optionally one subject) in a date range, oldest first."""
    _check_domain(domain)
    c = conn()
    q = "SELECT * FROM state_change WHERE domain = ?"
    args: list = [domain]
    if subject:
        q += " AND subject = ?"
        args.append(subject.strip())
    if since:
        q += " AND date >= ?"
        args.append(_check_day(since))
    if until:
        q += " AND date <= ?"
        args.append(_check_day(until))
    q += " ORDER BY date, sequence, id"
    return [_shape(r) for r in c.execute(q, args).fetchall()]


def get_change(change_id):
    """One transition with parsed before/after payloads."""
    try:
        change_id = int(change_id)
    except (TypeError, ValueError):
        raise RepsError("no such change")
    c = conn()
    row = c.execute("SELECT * FROM state_change WHERE id = ?", (change_id,)).fetchone()
    if not row:
        raise RepsError("no such change")
    return _shape(row)


def state_at(domain, subject="", at=""):
    """Reconstruct domain state as of a date by folding recorded transitions.

    Dates before the first recorded change for this subject are not
    reconstructible (pre-history edits left no record): the answer is an
    explicit unknown, not a guess. Priority is the exception: absence means
    maintain, so pre-history state is well-defined.
    """
    _check_domain(domain)
    subject = (subject or "").strip()
    if not subject:
        raise RepsError("history_state needs a subject (program 'active:Day', muscle, exercise, "
                        "rule id, 'rotation' or 'anchor')")
    at = _check_day(at) if at else date.today().isoformat()
    all_changes = list_changes(domain, subject)
    if not all_changes:
        if domain == "priority":
            return {"domain": domain, "subject": subject, "at": at,
                    "reconstructible": True, "as_of_change_id": None,
                    "state": {"tier": "maintain", "since": None, "until": None}}
        return {"domain": domain, "subject": subject, "at": at,
                "reconstructible": False, "as_of_change_id": None,
                "reason": "no recorded history for this subject"}
    changes = [ch for ch in all_changes if ch["date"] <= at]
    if not all_changes:
        if domain == "priority":
            return {"domain": domain, "subject": subject, "at": at,
                    "reconstructible": True, "as_of_change_id": None,
                    "state": {"tier": "maintain", "since": None, "until": None}}
        return {"domain": domain, "subject": subject, "at": at,
                "reconstructible": False, "as_of_change_id": None,
                "reason": "no recorded history for this subject"}
    first = all_changes[0]["date"]
    if not changes:
        if domain == "priority":
            return {"domain": domain, "subject": subject, "at": at,
                    "reconstructible": True, "as_of_change_id": None,
                    "state": {"tier": "maintain", "since": None, "until": None}}
        return {"domain": domain, "subject": subject, "at": at,
                "reconstructible": False, "as_of_change_id": None,
                "reason": f"no recorded history before {first}"}
    state = _fold(domain, subject, changes)
    return {"domain": domain, "subject": subject, "at": at,
            "reconstructible": True, "as_of_change_id": changes[-1]["id"],
            "state": state}


def _fold(domain, subject, changes):
    """Fold a chain of transitions (oldest first) into the state at the tip.

    Every after-envelope is a complete domain state (never a delta), so the
    tip's after is the fold, except for goal: successive goals share one
    exercise subject, so scope the chain to the tip's goal_id.
    """
    if domain == "goal":
        gid = changes[-1]["after"].get("goal_id")
        chain = [ch for ch in changes
                 if ch["after"].get("goal_id") == gid or ch["before"].get("goal_id") == gid]
        return chain[-1]["after"] if chain else changes[-1]["after"]
    return changes[-1]["after"]


def value_at(change_list, day_iso, key):
    """State value in effect on a date: fold history to that date, else the
    earliest recorded before-image (stable under later changes, flagged as
    pre-history by the caller via coverage dates), else None."""
    past = [ch for ch in change_list if ch["date"] <= day_iso]
    if past:
        return past[-1]["after"].get(key)
    if change_list:
        return change_list[0]["before"].get(key)
    return None


def split_map_at(prog_hist, day_iso, c):
    """Active split daymap in effect on a date: per-day snapshots folded from
    program history (earliest before-image before history starts), current
    days for never-recorded days. Never today's edited split."""
    from .program import parse_active_split_days, parse_movements

    by_subject: dict = {}
    for ch in prog_hist:
        if ch["subject"].startswith("active:"):
            by_subject.setdefault(ch["subject"], []).append(ch)
    covered = {sub.partition(":")[2] for sub in by_subject}
    daymap: dict = {}
    for sub, changes in by_subject.items():
        dayname = sub.partition(":")[2]
        past = [ch for ch in changes if ch["date"] <= day_iso]
        snap = (past[-1]["after"] if past else changes[0]["before"])["slots"]
        moves = []
        for s in snap:
            moves.extend(parse_movements(s["movements"]))
        if moves:
            daymap[dayname] = moves
    for dayname, moves in parse_active_split_days(c).items():
        if dayname not in covered:
            daymap[dayname] = moves
    return daymap


def coverage():
    """Earliest recorded date per (domain, subject): the UI reads this to
    say 'historical state unavailable before X' instead of guessing."""
    c = conn()
    return [{"domain": r["domain"], "subject": r["subject"], "first_date": r["first_date"]}
            for r in c.execute("SELECT domain, subject, MIN(date) AS first_date FROM state_change "
                               "GROUP BY domain, subject ORDER BY domain, subject").fetchall()]


def training_state_at(day_iso):
    """Whole training-system state in effect on a date, folded from history.

    Temporal rule (the single interpretation of "as of", shared with every
    consumer): a state change with effective date D is active for queries on
    D and thereafter, until superseded by another applicable change. So a
    Sep 01 change followed by Sep 10 means Sep 01-09 read the first state,
    Sep 10 onward reads the second. Folding is per subject: the latest change
    at or before the date wins (goal chains scope to the tip's goal_id).

    Every section carries its own known flag: recorded subjects fold to the
    date, never-recorded ones report unknown (never today's live state),
    priority defaults to maintain by backend rule (absence means maintain).
    The dashboard read model embeds one bundle per event date and selects
    the bundle at the latest event date at or before the requested as-of
    date; equivalence with a direct fold is proven by test, so the selection
    is transport, never a second folding implementation.
    """
    from .program import parse_active_split_days

    at = _check_day(day_iso)
    c = conn()
    cov = {(e["domain"], e["subject"]): e["first_date"] for e in coverage()}

    def _first(domain, subject):
        return cov.get((domain, subject))

    prog_hist = list_changes("program")
    recorded_days = sorted({ch["subject"].partition(":")[2] for ch in prog_hist
                            if ch["subject"].startswith("active:")})
    current_days = sorted(parse_active_split_days(c))
    program = []
    for day in sorted(set(recorded_days) | set(current_days)):
        st = state_at("program", f"active:{day}", at)
        if st["reconstructible"]:
            program.append({"day": day, "slots": st["state"]["slots"], "known": True,
                            "first_date": _first("program", f"active:{day}")})
        else:
            program.append({"day": day, "slots": [], "known": False,
                            "first_date": _first("program", f"active:{day}")})

    goal_subjects = sorted({ch["subject"] for ch in list_changes("goal")}
                           | {r["exercise"] for r in
                              c.execute("SELECT exercise FROM goals WHERE status = 'active'").fetchall()})
    goals = []
    for ex in goal_subjects:
        st = state_at("goal", ex, at)
        if st["reconstructible"]:
            s = st["state"]
            goals.append({"exercise": ex, "goal_id": s.get("goal_id"),
                          "target_e1rm": s.get("target_e1rm"), "deadline": s.get("deadline"),
                          "status": s.get("status"), "checkpoints": s.get("checkpoints"),
                          "known": True, "first_date": _first("goal", ex)})
        else:
            goals.append({"exercise": ex, "goal_id": None, "target_e1rm": None,
                          "deadline": None, "status": None, "checkpoints": None,
                          "known": False, "first_date": _first("goal", ex)})

    from .constants import load_constants
    priorities = []
    for muscle in sorted(load_constants().muscles):
        st = state_at("priority", muscle, at)
        first = _first("priority", muscle)
        if st["reconstructible"] and first is not None and first <= at:
            s = st["state"]
            priorities.append({"muscle": muscle, "tier": s.get("tier"),
                               "since": s.get("since"), "until": s.get("until"),
                               "known": True, "first_date": first})
        else:
            # Absence means maintain by rule, but nothing was recorded:
            # the default reads honestly, never as a recorded tier.
            priorities.append({"muscle": muscle, "tier": "maintain",
                               "since": None, "until": None,
                               "known": False, "first_date": first})

    rot = state_at("rotation", "rotation", at)
    anch = state_at("rotation", "anchor", at)
    rotation = rot["state"].get("rotation") if rot["reconstructible"] else None
    anchor_date = anch["state"].get("anchor_date") if anch["reconstructible"] else None
    anchor_position = anch["state"].get("position") if anch["reconstructible"] else None

    rule_ids = sorted({ch["subject"] for ch in list_changes("rule")}
                      | {str(r["id"]) for r in c.execute("SELECT id FROM rules").fetchall()},
                      key=lambda x: (0, int(x)) if x.isdigit() else (1, x))
    rules = []
    for rid in rule_ids:
        st = state_at("rule", rid, at)
        if st["reconstructible"]:
            s = st["state"]
            rules.append({"rule_id": s.get("rule_id"), "text": s.get("text"),
                          "status": s.get("status"), "known": True,
                          "first_date": _first("rule", rid)})
        else:
            rules.append({"rule_id": int(rid) if rid.isdigit() else None, "text": None,
                          "status": None, "known": False, "first_date": _first("rule", rid)})

    deload_subjects = sorted({ch["subject"] for ch in list_changes("deload")}
                             | {f"{r['scope']}:{r['subject']}" for r in
                                c.execute("SELECT scope, subject FROM deload_state").fetchall()})
    deloads = []
    for sub in deload_subjects:
        scope, _, name = sub.partition(":")
        st = state_at("deload", sub, at)
        if st["reconstructible"]:
            s = st["state"]
            deloads.append({"scope": s.get("scope"), "subject": s.get("subject"),
                            "active": s.get("active"), "known": True,
                            "first_date": _first("deload", sub)})
        else:
            deloads.append({"scope": scope or None, "subject": name or None,
                            "active": None, "known": False,
                            "first_date": _first("deload", sub)})

    return {"date": at, "program": program, "goals": goals, "priorities": priorities,
            "rotation": rotation, "rotation_known": rot["reconstructible"],
            "rotation_first_date": _first("rotation", "rotation"),
            "anchor_date": anchor_date, "anchor_position": anchor_position,
            "anchor_known": anch["reconstructible"],
            "anchor_first_date": _first("rotation", "anchor"),
            "deloads": deloads, "rules": rules}


def revert_change(change_id, evidence=""):
    """Create the inverse transition of a recorded change, if currently valid.

    Never rewrites history: the original row is untouched except for
    superseded_by (set only when it had none), and the inverse is a new row
    with reverses pointing back.
    """
    original = get_change(change_id)
    if original["superseded_by"] is not None:
        raise RepsError(f"change {change_id} was already superseded by change "
                        f"{original['superseded_by']}, revert that one instead")
    c = conn()
    domain, subject = original["domain"], original["subject"]
    before, after = original["before"], original["after"]
    applier = {"program": _revert_program, "priority": _revert_priority,
               "goal": _revert_goal, "deload": _revert_deload,
               "rule": _revert_rule, "rotation": _revert_rotation}[domain]
    inverse_after = applier(c, subject, before, after)
    out = record_change(c, domain, subject, after, inverse_after,
                        evidence or f"revert of change {change_id}", reverses=change_id)
    c.execute("UPDATE state_change SET superseded_by = ? WHERE id = ? AND superseded_by IS NULL",
              (out["change_id"], change_id))
    c.commit()
    out["reverses"] = change_id
    return out


def _revert_program(c, subject, before, after):
    from .program import _day_snapshot, _restore_day_snapshot

    variant, _, day = subject.partition(":")
    if not variant or not day:
        raise RepsError(f"change has malformed program subject '{subject}'")
    current = [{"slot": r["slot"], "movements": r["movements"], "sets": r["sets"]}
               for r in _day_snapshot(c, variant, day)["slots"]]
    if current != after.get("slots"):
        raise RepsError("program day moved since this change, revert would clobber newer edits; "
                        "revert the later change first")
    _restore_day_snapshot(c, variant, day, before.get("slots") or [])
    return dict(before)


def _revert_priority(c, subject, before, after):
    from .program import _priority_image

    muscle = subject
    current = c.execute("SELECT * FROM priority WHERE muscle = ?", (muscle,)).fetchone()
    if _priority_image(dict(current) if current else None) != after:
        raise RepsError("priority moved since this change, revert would clobber newer edits; "
                        "revert the later change first")
    if before.get("tier") is None:
        c.execute("DELETE FROM priority WHERE muscle = ?", (muscle,))
        return {"tier": None, "since": None, "until": None}
    c.execute("INSERT INTO priority (muscle, tier, since, until) VALUES (?, ?, ?, ?) "
              "ON CONFLICT (muscle) DO UPDATE SET tier = excluded.tier, since = excluded.since, "
              "until = excluded.until",
              (muscle, before["tier"], before["since"], before["until"]))
    return dict(before)


def _revert_goal(c, subject, before, after):
    action = after.get("action")
    gid = after.get("goal_id")
    goal = c.execute("SELECT * FROM goals WHERE id = ?", (gid,)).fetchone()
    if not goal:
        raise RepsError(f"goal {gid} is gone, nothing to revert")
    goal = dict(goal)
    if action == "rewrite":
        from .goals import _checkpoint_list

        if _checkpoint_list(c, gid) != after.get("checkpoints"):
            raise RepsError("goal trajectory moved since this change, revert would clobber newer "
                            "edits; revert the later change first")
        if goal["status"] != after.get("status"):
            raise RepsError("goal moved since this change, revert would clobber newer edits; "
                            "revert the later change first")
        for i, cp in enumerate(before.get("checkpoints") or [], 1):
            c.execute("UPDATE goal_checkpoints SET target_e1rm = ? WHERE goal_id = ? AND session_no = ?",
                      (cp, gid, i))
        return dict(before)
    if action == "add":
        if goal["status"] != "active":
            raise RepsError("goal moved since this change, revert would clobber newer edits; "
                            "revert the later change first")
        c.execute("UPDATE goals SET status = 'dropped' WHERE id = ?", (gid,))
        return {"goal_id": gid, "exercise": after.get("exercise"), "action": "drop",
                "checkpoints": after.get("checkpoints"), "target_e1rm": after.get("target_e1rm"),
                "deadline": after.get("deadline"), "status": "dropped",
                "target_desc": after.get("target_desc")}
    if action == "drop":
        if goal["status"] != "dropped":
            raise RepsError("goal moved since this change, revert would clobber newer edits; "
                            "revert the later change first")
        rival = c.execute("SELECT id FROM goals WHERE exercise = ? AND status = 'active' AND id != ?",
                          (after.get("exercise"), gid)).fetchone()
        if rival:
            raise RepsError(f"goal {rival['id']} already covers '{after.get('exercise')}' "
                            f"(rewrite or drop it first)")
        c.execute("UPDATE goals SET status = ? WHERE id = ?", (before.get("status") or "active", gid))
        return dict(before)
    raise RepsError(f"goal change with action '{action}' has no defined inverse")


def _revert_deload(c, subject, before, after):
    from datetime import date as _date

    today = _date.today().isoformat()
    action = after.get("action")
    if action == "set":
        row = c.execute("SELECT id FROM deload_state WHERE scope = ? AND subject = ? "
                        "AND cleared_on IS NULL",
                        (after.get("scope"), after.get("subject"))).fetchone()
        if not row:
            raise RepsError("deload is no longer active, nothing to revert")
        c.execute("UPDATE deload_state SET cleared_on = ? WHERE id = ?", (today, row["id"]))
        return {"scope": after.get("scope"), "subject": after.get("subject"),
                "action": "clear", "active": False}
    if action == "clear":
        existing = c.execute("SELECT id FROM deload_state WHERE scope = ? AND subject = ? "
                             "AND cleared_on IS NULL",
                             (after.get("scope"), after.get("subject"))).fetchone()
        if existing:
            raise RepsError("deload is already active, revert would duplicate it")
        c.execute("INSERT INTO deload_state (scope, subject, set_on, cleared_on) VALUES (?, ?, ?, NULL)",
                  (after.get("scope"), after.get("subject"), today))
        return {"scope": after.get("scope"), "subject": after.get("subject"),
                "action": "set", "active": True}
    raise RepsError(f"deload change with action '{action}' has no defined inverse")


def _revert_rule(c, subject, before, after):
    try:
        rid = int(subject)
    except ValueError:
        raise RepsError(f"change has malformed rule subject '{subject}'")
    row = c.execute("SELECT * FROM rules WHERE id = ?", (rid,)).fetchone()
    if not row:
        raise RepsError(f"rule {rid} is gone, nothing to revert")
    row = dict(row)
    current = {"text": row["text"], "expiry": row["expiry"], "status": row["status"]}
    wanted = {"text": after.get("text"), "expiry": after.get("expiry"), "status": after.get("status")}
    if current != wanted:
        raise RepsError("rule moved since this change, revert would clobber newer edits; "
                        "revert the later change first")
    action = after.get("action")
    if action == "add":
        c.execute("UPDATE rules SET status = 'archived' WHERE id = ?", (rid,))
        return {"rule_id": rid, "action": "archive", "text": after.get("text"),
                "subject": after.get("subject"), "expiry": after.get("expiry"),
                "status": "archived"}
    c.execute("UPDATE rules SET text = ?, expiry = ?, status = ? WHERE id = ?",
              (before.get("text"), before.get("expiry"), before.get("status") or "active", rid))
    return dict(before)


def _revert_rotation(c, subject, before, after):
    if subject == "anchor":
        return _revert_anchor(c, subject, before, after)
    from .program import _restore_rotation, _rotation_image, get_rotation

    current = _rotation_image(get_rotation(c))
    if current != after.get("rotation"):
        raise RepsError("rotation moved since this change, revert would clobber newer edits; "
                        "revert the later change first")
    entries = [None if d is None else d for d in (before.get("rotation") or [])]
    _restore_rotation(c, entries)
    return dict(before)


def _revert_anchor(c, subject, before, after):
    from .adherence import _restore_anchor, get_anchor

    current = get_anchor(c)
    current_image = {"rotation": None,
                     "anchor_date": current["date"] if current else None,
                     "position": current["index"] if current else None}
    wanted = {"rotation": None, "anchor_date": after.get("anchor_date"),
              "position": after.get("position")}
    if current_image != wanted:
        raise RepsError("anchor moved since this change, revert would clobber newer edits; "
                        "revert the later change first")
    _restore_anchor(c, before.get("anchor_date"), before.get("position"))
    return dict(before)
