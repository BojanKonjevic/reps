# SSOT owner: lift registry, split slots, rotation, compaction, rules, flags, priorities, deloads.
# Consumers: plan, adherence, sessions gate, snapshot, MCP. Relationships are FKs;
# read models (movements "a / b" strings) are assembled on read, never stored.

import sqlite3
from datetime import date, datetime

from .errors import RepsError
from .vocab import AutoregAction, DeloadScope, PriorityTier, SplitVariant, values

from .constants import canon_muscle_name, load_constants
from .db import conn, open_workout, placeholders
from .history import record_change
from .memory import append_memory_state


def parse_movements(text):
    """Split an input movements cell ("a / b") into canonical names.

    Input-boundary parser for MCP args and read-model assembly. DB columns
    are never string-split: storage is split_slot_lift rows.
    """
    return [m.strip().lower() for m in text.split("/") if m.strip()]  # sanctioned: input-boundary parser


# --- lift registry (lift + lift_muscle own exercise existence and mapping) ---

def ensure_lift(c, exercise):
    """Insert the lift row if missing. Mapping rows are written separately."""
    c.execute("INSERT OR IGNORE INTO lift (exercise, is_bodyweight_only) VALUES (?, 0)",
              (exercise,))


def lift_muscles(c, exercise) -> list[str] | None:
    """Mapped muscles as a list, or None when unmapped. Single owner query."""
    rows = c.execute("SELECT muscle FROM lift_muscle WHERE exercise = ? ORDER BY muscle",
                     (exercise,)).fetchall()
    if not rows:
        return None
    return [r["muscle"] for r in rows]


def lift_muscles_csv(c, exercise):
    """Comma-joined mapped muscles, or None when unmapped.

    String form exists only for string boundaries (MCP mapping responses).
    Internal consumers use lift_muscles() and never round-trip through this.
    """
    muscles = lift_muscles(c, exercise)
    if muscles is None:
        return None
    return ",".join(muscles)


def set_lift_muscles(c, exercise, muscles_csv, is_bodyweight_only=0):
    """Replace a lift's muscle set (mapping authority writes here)."""
    ensure_lift(c, exercise)
    if is_bodyweight_only:
        c.execute("UPDATE lift SET is_bodyweight_only = 1 WHERE exercise = ?", (exercise,))
    c.execute("DELETE FROM lift_muscle WHERE exercise = ?", (exercise,))
    for mu in (muscles_csv or "").split(","):  # sanctioned: input-boundary parse of a validated arg
        mu = mu.strip()
        if mu:
            c.execute("INSERT INTO lift_muscle (exercise, muscle) VALUES (?, ?)", (exercise, mu))


def lift_is_bodyweight_only(c, exercise):
    row = c.execute("SELECT is_bodyweight_only FROM lift WHERE exercise = ?", (exercise,)).fetchone()
    return bool(row and row["is_bodyweight_only"])


def rename_lift(c, old, new):
    """Rename a lift: one UPDATE, FK cascades re-point every child row."""
    try:
        cur = c.execute("UPDATE lift SET exercise = ? WHERE exercise = ?", (new, old))
    except sqlite3.IntegrityError:
        raise RepsError(f"'{new}' already exists, merge instead of renaming")
    if cur.rowcount == 0:
        raise RepsError(f"no lift '{old}'")
    return cur.rowcount


def merge_lifts(c, old, new):
    """Merge old into an existing lift: re-point child rows, delete old.

    Refuses when the muscle sets conflict (retag one of them first).
    """
    old_m = lift_muscles(c, old)
    new_m = lift_muscles(c, new)
    if old_m is None:
        raise RepsError(f"no lift '{old}'")
    if new_m is None:
        raise RepsError(f"no lift '{new}'")
    if set(old_m) != set(new_m):
        raise RepsError(f"'{new}' maps to {new_m}, not {old_m}; retag one of them first, then merge")
    moved = c.execute("SELECT COUNT(*) n FROM sets WHERE exercise = ?", (old,)).fetchone()["n"]
    for table, col in [("sets", "exercise"), ("goals", "exercise"), ("movement_note", "exercise")]:
        c.execute(f"UPDATE {table} SET {col} = ? WHERE {col} = ?", (new, old))
    # Progression is unique per (workout, exercise): carry old verdicts only
    # where the survivor has none, drop the shadowed duplicates.
    c.execute("UPDATE progression SET exercise = ? WHERE exercise = ? AND NOT EXISTS ("
              "SELECT 1 FROM progression p2 WHERE p2.workout_id = progression.workout_id "
              "AND p2.exercise = ?)", (new, old, new))
    c.execute("DELETE FROM progression WHERE exercise = ?", (old,))
    for row in c.execute("SELECT slot_id, position FROM split_slot_lift WHERE exercise = ?",
                         (old,)).fetchall():
        taken = c.execute("SELECT 1 FROM split_slot_lift WHERE slot_id = ? AND exercise = ?",
                          (row["slot_id"], new)).fetchone()
        if taken:
            c.execute("DELETE FROM split_slot_lift WHERE slot_id = ? AND exercise = ?",
                      (row["slot_id"], old))
        else:
            c.execute("UPDATE split_slot_lift SET exercise = ? WHERE slot_id = ? AND exercise = ?",
                      (new, row["slot_id"], old))
    c.execute("DELETE FROM lift_muscle WHERE exercise = ?", (old,))
    c.execute("DELETE FROM lift WHERE exercise = ?", (old,))
    return {"merged": old, "into": new, "moved": moved}


# --- split days and slots (split_day / split_slot / split_slot_lift) ---

def _slot_moves(c, slot_id):
    return [r["exercise"] for r in c.execute(
        "SELECT exercise FROM split_slot_lift WHERE slot_id = ? ORDER BY position", (slot_id,)).fetchall()]


def slot_rows(c, variant="active", day=None):
    """Split slots with moves straight from split_slot_lift, no string form.

    Internal callers use this; the `"a / b"` movements string exists only as
    the read-model shape `read_split` returns to MCP/snapshot consumers.
    """
    q = ("SELECT s.day, s.slot, s.sets, l.exercise FROM split_slot s "
         "JOIN split_slot_lift l ON l.slot_id = s.id WHERE s.variant = ?")
    args: list = [variant]
    if day is not None:
        q += " AND s.day = ?"
        args.append(day)
    q += " ORDER BY s.day, s.slot, l.position"
    grouped: dict = {}
    for r in c.execute(q, args).fetchall():
        key = (r["day"], r["slot"])
        grouped.setdefault(key, {"day": r["day"], "slot": r["slot"],
                                 "sets": r["sets"], "moves": []})["moves"].append(r["exercise"])
    return [grouped[k] for k in sorted(grouped)]


def split_day_order(variant="active", c=None):
    """Day names in rotation order (rest entries excluded)."""
    c = c or conn()
    days = [r["name"] for r in c.execute(
        "SELECT name FROM split_day WHERE name IN "
        "(SELECT day FROM split_slot WHERE variant = ?) ORDER BY name", (variant,)).fetchall()]
    rotation = get_rotation(c)
    order = [d for d in rotation if d in days]
    return order + [d for d in sorted(days) if d not in order]


def read_split(variant="active", day=None, c=None):
    """Split rows as [{day, slot, movements, sets}], optionally one day.

    The movements string is a read model assembled from split_slot_lift
    in position order, never a stored column.
    """
    c = c or conn()
    if day:
        rows = c.execute("SELECT id, day, slot, sets FROM split_slot "
                         "WHERE variant = ? AND day = ? ORDER BY slot", (variant, day)).fetchall()
    else:
        rows = c.execute("SELECT id, day, slot, sets FROM split_slot "
                         "WHERE variant = ? ORDER BY day, slot", (variant,)).fetchall()
    return [{"day": r["day"], "slot": r["slot"],
             "movements": " / ".join(_slot_moves(c, r["id"])), "sets": r["sets"]} for r in rows]


def parse_active_split_days(c=None):
    """Active split as {day: [movement, ...]} with alternates flattened."""
    days = {}
    for r in slot_rows(c or conn(), "active"):
        days.setdefault(r["day"], []).extend(r["moves"])
    return days


def get_rotation(c=None):
    """Rotation order from the rotation table ("rest" for NULL rest entries)."""
    c = c or conn()
    return [r["day"] if r["day"] is not None else "rest"
            for r in c.execute("SELECT day FROM rotation ORDER BY position").fetchall()]


def parse_rotation(c=None):
    """Rotation order (kept name: plan/adherence/snapshot read through here)."""
    return get_rotation(c)


def _day_snapshot(c, variant, day):
    rows = read_split(variant, day, c=c)
    return {"variant": variant, "day": day,
            "slots": [{"slot": r["slot"], "movements": r["movements"], "sets": r["sets"]}
                      for r in rows]}


def _restore_day_snapshot(c, variant, day, slots):
    """Rewrite one day from a recorded snapshot (history revert path, no recording)."""
    c.execute("DELETE FROM split_slot WHERE variant = ? AND day = ?", (variant, day))
    for r in slots or []:
        _write_slot(c, variant, day, r["slot"], parse_movements(r["movements"]), r["sets"])


def _write_rotation(c, entries):
    """Replace rotation rows with anchor preservation. Returns anchor_cleared."""
    old_rotation = get_rotation(c)
    saved = c.execute("SELECT anchor_date, position FROM rotation_anchor WHERE id = 1").fetchone()
    c.execute("DELETE FROM rotation_anchor WHERE id = 1")
    c.execute("DELETE FROM rotation")
    for i, day in enumerate(entries):
        c.execute("INSERT INTO rotation (position, day) VALUES (?, ?)", (i, day))
    cleared = False
    if saved is not None:
        pos = saved["position"]

        def _norm(d):
            return None if d is None or str(d).lower() == "rest" else d
        same_day = (pos < len(entries) and pos < len(old_rotation)
                    and _norm(entries[pos]) == _norm(old_rotation[pos]))
        if same_day:
            c.execute("INSERT INTO rotation_anchor (id, anchor_date, position) VALUES (1, ?, ?)",
                      (saved["anchor_date"], pos))
        else:
            cleared = True
    return cleared


def _restore_rotation(c, entries):
    """Rewrite rotation from a recorded image (history revert path, no recording)."""
    _write_rotation(c, entries)


def _rotation_image(days):
    return [None if d is None or str(d).lower() == "rest" else d for d in days]


def _priority_image(row):
    if row is None:
        return {"tier": None, "since": None, "until": None}
    return {"tier": row["tier"], "since": row["since"], "until": row["until"]}


def set_rotation(days, evidence=""):
    """Replace the rotation order. Days must be split days; None means rest."""
    if not days:
        raise RepsError("rotation must be a non-empty day list")
    c = conn()
    known = [r["name"] for r in c.execute("SELECT name FROM split_day").fetchall()]
    entries = []
    for d in days:
        if d is None:
            entries.append(None)
            continue
        name = str(d).strip()
        if not name:
            raise RepsError("rotation entries must be day names or null (rest)")
        if name.lower() == "rest":
            entries.append(None)
            continue
        match = next((k for k in known if k.lower() == name.lower()), None)
        if match is None:
            raise RepsError(f"rotation days must exist in splits, unknown: {name}")
        entries.append(match)
    before = {"rotation": _rotation_image(get_rotation(c))}
    after = {"rotation": _rotation_image(entries)}
    anchor_row = c.execute("SELECT anchor_date, position FROM rotation_anchor WHERE id = 1").fetchone()
    had_anchor = anchor_row is not None
    try:
        cleared = _write_rotation(c, entries)
        change = record_change(c, "rotation", "rotation", before, after, evidence)
        anchor_change = None
        if had_anchor and cleared:
            from .adherence import _anchor_image

            anchor_change = record_change(
                c, "rotation", "anchor", _anchor_image(dict(anchor_row)),
                {"rotation": None, "anchor_date": None, "position": None}, evidence)
        c.commit()
    except sqlite3.IntegrityError as e:
        c.rollback()
        raise RepsError(f"rotation write refused: {e}")
    out = {"rotation": get_rotation(c), "change_id": change["change_id"]}
    if had_anchor:
        out["anchor_cleared"] = cleared
    if anchor_change is not None:
        out["anchor_change_id"] = anchor_change["change_id"]
    return out


def show_rotation():
    c = conn()
    return {"rotation": get_rotation(c)}


def weekly_volume(c, muscle, week_starts):
    from datetime import timedelta
    base = week_starts[0].isoformat()
    rows = c.execute("""
        SELECT date(w.date) as day, COUNT(*) as sets
        FROM sets s
        JOIN workouts w ON w.id = s.workout_id
        JOIN set_muscle sm ON sm.set_id = s.id
        WHERE sm.muscle = ? AND date(w.date) >= ?
        GROUP BY day
    """, (muscle, base)).fetchall()
    per_day = {r["day"]: r["sets"] for r in rows}
    out = []
    for ws in week_starts:
        we = ws + timedelta(days=7)
        out.append(sum(n for d, n in per_day.items() if ws.isoformat() <= d < we.isoformat()))
    return out


def trim_leading_zeros(weekly):
    """Drop pre-history zero weeks before the first logged sets for a muscle.

    Weeks before anything was ever logged are absent, not skipped: counting
    them as bad weeks flags every muscle below MEV on a fresh log. Zeros
    after the first nonzero week stay, a skipped week is information. An
    all-zero window is returned whole, a never-trained muscle still flags.
    """
    for i, n in enumerate(weekly):
        if n > 0:
            return weekly[i:]
    return weekly


def span_start(weeklies):
    """First week index with any logged sets across muscles: the history start.

    Weeks before anything was logged are absent for every muscle, never
    skipped. Returns the window width when nothing was logged, so every
    slice comes back empty and nothing can flag on no data.
    """
    width = max([len(w) for w in weeklies] or [0])
    for i in range(width):
        if any(i < len(w) and w[i] > 0 for w in weeklies):
            return i
    return width


def count_bad_weeks(weekly, mev, min_span):
    """Zero and low week counts over the trained span (audit check 8 rule).

    `weekly` arrives already sliced at the history start by the caller;
    per-muscle leading zeros are absent, not skipped. A span that never
    trained the muscle counts whole only when long enough to judge
    (min_span, the bad-week bar); shorter spans contribute nothing.
    """
    if mev == 0:
        # MEV 0 means no direct work is required (covered indirectly),
        # so zero-set weeks meet the floor and never flag.
        return (0, 0)
    trimmed = trim_leading_zeros(weekly)
    if not trimmed:
        return (len(weekly), 0) if len(weekly) >= min_span else (0, 0)
    return (sum(1 for n in trimmed if n == 0),
            sum(1 for n in trimmed if 0 < n < mev))


def recent_average(weekly, k=4):
    """Mean over the last k trained-span weeks (pre-history zeros excluded)."""
    trimmed = trim_leading_zeros(weekly)
    recent = trimmed[-k:] if len(trimmed) >= k else trimmed
    return sum(recent) / len(recent) if recent else 0


def classify_volume(weekly, mev, mrv, vol_bad):
    """Shared volume classifier for plan status and audit flags.

    Below-MEV mirrors audit check 8 exactly (zero or low weeks counted over
    the trained span, pre-history excluded); above-MRV uses the recent-4-week
    average over the same span. Meeting MEV exactly (n == mev) is in range,
    only strictly-below weeks count as low.
    """
    zero_weeks, low_weeks = count_bad_weeks(weekly, mev, vol_bad)
    if zero_weeks >= vol_bad or low_weeks >= vol_bad:
        return "below_mev"
    avg = recent_average(weekly)
    if mrv is not None and avg > mrv:
        return "above_mrv"
    return "in_range"


def volume_block(c):
    """Per-muscle weekly counts plus bounds and status, the same shape plan builds.

    Shared by plan and the dashboard snapshot so both read one computation.
    """
    from datetime import timedelta
    from .weeks import week_starts as _week_starts
    constants = load_constants()
    thresholds = constants.thresholds
    starts = [date.fromisoformat(s) for s in _week_starts(thresholds.volume_window_weeks)]
    vol_bad = thresholds.volume_bad_weeks
    weeklies = {muscle: weekly_volume(c, muscle, starts)
                for muscle in constants.muscles}
    start = span_start(list(weeklies.values()))
    volume = {}
    for muscle, entry in constants.muscles.items():
        weekly = weeklies[muscle]
        volume[muscle] = {"weekly": weekly, "mev": entry.mev, "mav": entry.mav,
                          "mrv": entry.mrv, "freq": entry.freq,
                          "status": classify_volume(weekly[start:], entry.mev, entry.mrv, vol_bad)}
    return volume


def get_compaction():
    c = conn()
    row = c.execute("SELECT last_compacted, postponed_until FROM compaction WHERE id = 1").fetchone()
    if not row:
        return {"last_compacted": None, "postponed_until": None}
    return {"last_compacted": row["last_compacted"], "postponed_until": row["postponed_until"]}


def set_compaction(last_compacted=None, postponed_until=None):
    """Typed compaction markers (replaces untyped meta writes).

    None means leave the stored value unchanged. "never"/"" clears
    last_compacted back to NULL.
    """
    clear_last = last_compacted in ("never", "")
    if last_compacted is not None and not clear_last:
        try:
            datetime.strptime(last_compacted, "%b %d %Y")
        except ValueError:
            raise RepsError('last_compacted must be "never" or "Mon D YYYY" (e.g. Oct 1 2026)')
    if postponed_until is not None:
        try:
            postponed_until = date.fromisoformat(postponed_until).isoformat()
        except ValueError:
            raise RepsError("postponed_until must be YYYY-MM-DD")
    c = conn()
    cur = get_compaction()
    if last_compacted is not None:
        cur["last_compacted"] = None if clear_last else last_compacted
    if postponed_until is not None:
        cur["postponed_until"] = postponed_until
    c.execute("INSERT INTO compaction (id, last_compacted, postponed_until) VALUES (1, ?, ?) "
              "ON CONFLICT (id) DO UPDATE SET last_compacted = excluded.last_compacted, "
              "postponed_until = excluded.postponed_until",
              (cur["last_compacted"], cur["postponed_until"]))
    c.commit()
    return get_compaction()


def compaction_due():
    comp = get_compaction()
    last = comp["last_compacted"]
    postponed = comp["postponed_until"]
    if postponed:
        try:
            if date.today() < date.fromisoformat(postponed):
                return {"due": False, "last": last}
        except ValueError:
            pass
    if last is None:
        return {"due": date.today().day != 1, "last": None}
    try:
        last_date = datetime.strptime(last, "%b %d %Y").date()
    except ValueError:
        return {"due": False, "last": last}
    first = date.today().replace(day=1)
    return {"due": date.today() > first and last_date < first, "last": last}


def read_priorities(c):
    """Effective priority tiers. Absence means maintain; expired rows no longer apply."""
    today = date.today().isoformat()
    return {r["muscle"]: {"tier": r["tier"], "since": r["since"], "until": r["until"]}
            for r in c.execute("SELECT * FROM priority").fetchall()
            if r["until"] is None or r["until"] >= today}


def priority_needs_confirm(c):
    """Expired or soon-expiring tiers, for the renew-or-revert moment."""
    today = date.today()
    out = []
    for r in c.execute("SELECT * FROM priority").fetchall():
        if r["until"] and (date.fromisoformat(r["until"]) - today).days <= 7:
            out.append({"type": "priority", "muscle": r["muscle"], "tier": r["tier"],
                        "until": r["until"],
                        "expired": date.fromisoformat(r["until"]) < today})
    return out


def set_priority(muscle, tier, until=None, evidence=""):
    muscle = muscle.strip().lower()
    if tier not in values(PriorityTier):
        raise RepsError("tier must be one of priority maintain deprioritize")
    constants = load_constants()
    known = set(constants.muscles) | set(constants.untracked)
    hit = canon_muscle_name(muscle, known)
    if hit is not None:
        muscle = hit
    if muscle not in constants.muscles:
        raise RepsError(f"'{muscle}' is not a tracked muscle (untracked: {', '.join(constants.untracked)})")
    if until is not None:
        try:
            until = date.fromisoformat(until).isoformat()
        except ValueError:
            raise RepsError("until must be YYYY-MM-DD")
    c = conn()
    old = c.execute("SELECT * FROM priority WHERE muscle = ?", (muscle,)).fetchone()
    before = _priority_image(dict(old) if old else None)
    today = date.today().isoformat()
    c.execute("INSERT INTO priority (muscle, tier, since, until) VALUES (?, ?, ?, ?) "
              "ON CONFLICT (muscle) DO UPDATE SET tier = excluded.tier, since = excluded.since, until = excluded.until",
              (muscle, tier, today, until))
    after = {"tier": tier, "since": today, "until": until}
    change = record_change(c, "priority", muscle, before, after, evidence)
    c.commit()
    return {"priority": muscle, "tier": tier, "until": until, "change_id": change["change_id"]}


def clear_priority(muscle, evidence=""):
    muscle = muscle.strip().lower()
    c = conn()
    old = c.execute("SELECT * FROM priority WHERE muscle = ?", (muscle,)).fetchone()
    cur = c.execute("DELETE FROM priority WHERE muscle = ?", (muscle,))
    out = {"cleared": muscle, "rows": cur.rowcount}
    if old is not None:
        change = record_change(c, "priority", muscle, _priority_image(dict(old)),
                               _priority_image(None), evidence)
        out["change_id"] = change["change_id"]
    c.commit()
    return out


def list_priorities():
    c = conn()
    rows = c.execute("SELECT * FROM priority ORDER BY muscle").fetchall()
    return [dict(r) for r in rows]


def set_deload(scope, subject, evidence=""):
    if scope not in values(DeloadScope):
        raise RepsError("scope must be lift or slot")
    if not subject:
        raise RepsError("deload subject is required")
    c = conn()
    today = date.today().isoformat()
    if scope == "lift":
        subject = subject.strip().lower()
        if not c.execute("SELECT exercise FROM lift WHERE exercise = ?", (subject,)).fetchone():
            raise RepsError(f"'{subject}' is not a known lift")
    else:
        match = next((d for d in split_day_order("active", c=c) if d.lower() == subject.strip().lower()), None)
        if not match:
            raise RepsError(f"no active split day '{subject.strip()}'")
        subject = match
    existing = c.execute("SELECT id FROM deload_state WHERE scope = ? AND subject = ? AND cleared_on IS NULL",
                         (scope, subject)).fetchone()
    if existing:
        return {"deload_id": existing["id"], "scope": scope, "subject": subject, "reused": True}
    cur = c.execute("INSERT INTO deload_state (scope, subject, set_on, cleared_on) VALUES (?, ?, ?, NULL)",
                    (scope, subject, today))
    change = record_change(c, "deload", f"{scope}:{subject}",
                           {"scope": scope, "subject": subject, "action": "set", "active": False},
                           {"scope": scope, "subject": subject, "action": "set", "active": True},
                           evidence)
    c.commit()
    return {"deload_id": cur.lastrowid, "scope": scope, "subject": subject,
            "change_id": change["change_id"]}


def clear_deload(evidence=""):
    # Prose first: if the State write fails, the DB is untouched and a retry
    # is safe. A markdown edit must never break a DB command halfway.
    c = conn()
    rows = c.execute("SELECT scope, subject FROM deload_state WHERE cleared_on IS NULL ORDER BY id").fetchall()
    today = date.today().isoformat()
    for r in rows:
        append_memory_state(f"{today}: deload completed for {r['scope']} {r['subject']}")
    c.execute("UPDATE deload_state SET cleared_on = ? WHERE cleared_on IS NULL", (today,))
    change_ids = []
    for r in rows:
        change = record_change(c, "deload", f"{r['scope']}:{r['subject']}",
                               {"scope": r["scope"], "subject": r["subject"],
                                "action": "clear", "active": True},
                               {"scope": r["scope"], "subject": r["subject"],
                                "action": "clear", "active": False},
                               evidence)
        change_ids.append(change["change_id"])
    c.commit()
    out = {"cleared": len(rows)}
    if change_ids:
        out["change_ids"] = change_ids
    return out


def active_deloads(c):
    return c.execute("SELECT * FROM deload_state WHERE cleared_on IS NULL ORDER BY id").fetchall()


def deload_covers(deloads, exercise, day_moves):
    """True if an active deload row covers this exercise (lift scope: exact name)."""
    lowered = {k.lower(): v for k, v in day_moves.items()}
    for d in deloads:
        if d["scope"] == "lift" and d["subject"] == exercise:
            return True
        if d["scope"] == "slot" and exercise in lowered.get(d["subject"].lower(), []):
            return True
    return False


def split_all_movements(variant="active", c=None):
    moves = set()
    for r in slot_rows(c or conn(), variant):
        moves.update(r["moves"])
    return moves


def day_movements(day, variant="active", c=None):
    moves = []
    for r in slot_rows(c or conn(), variant, day):
        moves.extend(r["moves"])
    return moves


def best_split_day(trained, c=None):
    """Best-matching split day, or None when ambiguous.

    Ties resolve to the first candidate explicitly (this is a suggestion
    for the reconcile gate, not a classification): the tie rule itself
    lives in reps/slots.py.
    """
    from .slots import slot_of_session
    c = c or conn()
    days = parse_active_split_days(c)
    match = slot_of_session(list(trained), days)
    if match["day"] is not None:
        return match["day"]
    if match["candidates"]:
        return match["candidates"][0]
    return None


def get_split(day=None, variant="active"):
    c = conn()
    if variant not in values(SplitVariant):
        raise RepsError("variant must be active or baseline")
    if day and not read_split(variant, day, c=c):
        raise RepsError(f"no {variant} split day '{day}'")
    days = [day] if day else split_day_order(variant, c=c)
    return {"variant": variant,
            "days": [{"day": d, "slots": read_split(variant, d, c=c)} for d in days]}


def _write_slot(c, variant, day, slot, moves, sets):
    c.execute("INSERT OR IGNORE INTO split_day (name) VALUES (?)", (day,))
    row = c.execute("SELECT id FROM split_slot WHERE variant = ? AND day = ? AND slot = ?",
                    (variant, day, slot)).fetchone()
    if row:
        slot_id = row["id"]
        c.execute("UPDATE split_slot SET sets = ? WHERE id = ?", (sets, slot_id))
        c.execute("DELETE FROM split_slot_lift WHERE slot_id = ?", (slot_id,))
    else:
        cur = c.execute("INSERT INTO split_slot (variant, day, slot, sets) VALUES (?, ?, ?, ?)",
                        (variant, day, slot, sets))
        slot_id = cur.lastrowid
    for pos, move in enumerate(moves):
        ensure_lift(c, move)
        c.execute("INSERT INTO split_slot_lift (slot_id, position, exercise) VALUES (?, ?, ?)",
                  (slot_id, pos, move))


def set_split(day, slot, movements, sets, variant="active", evidence=""):
    c = conn()
    if variant not in values(SplitVariant):
        raise RepsError("variant must be active or baseline")
    try:
        slot = int(slot)
        sets = int(sets)
    except (TypeError, ValueError):
        raise RepsError("slot and sets must be integers")
    if sets <= 0:
        raise RepsError("sets must be positive")
    movements = movements.strip().lower()
    if not movements:
        raise RepsError("movements cannot be empty")
    moves = parse_movements(movements)
    for move in moves:
        if lift_muscles(c, move) is None:
            raise RepsError(f"'{move}' is not a known lift, split unchanged")
    before = _day_snapshot(c, variant, day)
    before_moves = next((r["movements"] for r in read_split(variant, day, c=c) if r["slot"] == slot), None)
    try:
        _write_slot(c, variant, day, slot, moves, sets)
        after = _day_snapshot(c, variant, day)
        change = record_change(c, "program", f"{variant}:{day}", before, after, evidence)
        c.commit()
    except sqlite3.IntegrityError as e:
        c.rollback()
        raise RepsError(f"split write refused: {e}")
    out = {"split": variant, "day": day, "slot": slot, "movements": movements, "sets": sets,
           "change_id": change["change_id"]}
    if variant == "active":
        # MEV floor warns, never blocks: a human reviews the split edit first.
        # Scoped to muscles in the before or after movements only, so fresh
        # programs do not cry wolf about unrelated gaps.
        affected = muscles_for_movements(c, movements)
        if before_moves:
            affected |= muscles_for_movements(c, before_moves)
        warnings = mev_floor_warnings(programmed_weekly_volume(c), affected)
        if warnings:
            out["warnings"] = warnings
    return out


def move_split(day, exercise, to_slot, evidence=""):
    c = conn()
    exercise = exercise.strip().lower()
    try:
        to_slot = int(to_slot)
    except (TypeError, ValueError):
        raise RepsError("slot must be an integer")
    rows = slot_rows(c, "active", day)
    if not rows:
        raise RepsError(f"no active split day '{day}'")
    before = _day_snapshot(c, "active", day)
    origin = next((r for r in rows if exercise in r["moves"]), None)
    if not origin:
        raise RepsError(f"'{exercise}' is not in {day}")
    if len(origin["moves"]) > 1:
        raise RepsError(f"'{exercise}' shares slot {origin['slot']} ({' / '.join(origin['moves'])}); "
                       f"use set_split to rearrange interchangeable pairs explicitly")
    carry_sets = origin["sets"]
    remaining = []
    for r in rows:
        kept = [m for m in r["moves"] if m != exercise]
        if kept:
            remaining.append({"moves": kept, "sets": r["sets"]})
    to_slot = max(1, min(to_slot, len(remaining) + 1))
    remaining.insert(to_slot - 1, {"moves": [exercise], "sets": carry_sets})
    c.execute("DELETE FROM split_slot WHERE variant = 'active' AND day = ?", (day,))
    for i, r in enumerate(remaining, 1):
        _write_slot(c, "active", day, i, r["moves"], r["sets"])
    after = _day_snapshot(c, "active", day)
    change = record_change(c, "program", f"active:{day}", before, after, evidence)
    c.commit()
    return {"moved": exercise, "day": day, "to_slot": to_slot, "change_id": change["change_id"]}


def reconcile_split(day, after=None, evidence=""):
    c = conn()
    if not read_split("active", day, c=c):
        raise RepsError(f"no active split day '{day}'")
    w = open_workout(c)
    if not w:
        w = c.execute("SELECT * FROM workouts WHERE status = 'done' ORDER BY date DESC, id DESC LIMIT 1").fetchone()
    if not w:
        raise RepsError("no workout to reconcile from")
    trained = [r["exercise"] for r in c.execute(
        "SELECT exercise, MIN(id) m FROM sets WHERE workout_id = ? GROUP BY exercise ORDER BY m",
        (w["id"],)).fetchall()]
    known = split_all_movements("active", c=c)
    new = [ex for ex in trained if ex not in known]
    if not new:
        return {"reconciled": day, "added": []}
    before = _day_snapshot(c, "active", day)
    rows = slot_rows(c, "active", day)
    if after:
        anchor = next((r for r in rows if after.strip().lower() in r["moves"]), None)
        if not anchor:
            raise RepsError(f"'{after}' is not in {day}")
        insert_at = anchor["slot"] + 1
    else:
        insert_at = len(rows) + 1
    new_slot_sets = load_constants().thresholds.default_new_slot_sets
    shift = len(new)
    # Descending so shifted slots never collide with not-yet-moved ones.
    for r in c.execute("SELECT id, slot FROM split_slot WHERE variant = 'active' AND day = ? "
                       "AND slot >= ? ORDER BY slot DESC", (day, insert_at)).fetchall():
        c.execute("UPDATE split_slot SET slot = slot + ? WHERE id = ?", (shift, r["id"]))
    for i, ex in enumerate(new):
        _write_slot(c, "active", day, insert_at + i, [ex], new_slot_sets)
    after = _day_snapshot(c, "active", day)
    change = record_change(c, "program", f"active:{day}", before, after, evidence)
    c.commit()
    return {"reconciled": day, "added": new, "change_id": change["change_id"]}


def diff_split():
    c = conn()
    active = {(r["day"], r["slot"]): (r["movements"], r["sets"]) for r in read_split("active", c=c)}
    baseline = {(r["day"], r["slot"]): (r["movements"], r["sets"]) for r in read_split("baseline", c=c)}
    lines = []
    for key in sorted(set(active) | set(baseline)):
        a, b = active.get(key), baseline.get(key)
        if a != b:
            lines.append(f"{key[0]} #{key[1]}: baseline {b} vs active {a}")
    return {"matches": not lines, "lines": lines}


def revert_split(day=None, evidence=""):
    c = conn()
    if day:
        if not read_split("baseline", day, c=c):
            raise RepsError(f"no baseline split day '{day}'")
        days = [day]
    else:
        days = list(dict.fromkeys(split_day_order("baseline", c=c) + split_day_order("active", c=c)))
    change_ids = []
    for d in days:
        base = read_split("baseline", d, c=c)
        before = _day_snapshot(c, "active", d)
        c.execute("DELETE FROM split_slot WHERE variant = 'active' AND day = ?", (d,))
        for r in base:
            _write_slot(c, "active", d, r["slot"], parse_movements(r["movements"]), r["sets"])
        after = _day_snapshot(c, "active", d)
        if before != after:
            change = record_change(c, "program", f"active:{d}", before, after, evidence)
            change_ids.append(change["change_id"])
    c.commit()
    out = {"reverted": day or "all"}
    if change_ids:
        out["change_ids"] = change_ids
    return out


def consume_session_flags(c, workout_id):
    trained = {r["exercise"] for r in c.execute(
        "SELECT DISTINCT exercise FROM sets WHERE workout_id = ?", (workout_id,)).fetchall()}
    muscles = set()
    for ex in trained:
        muscles.update(lift_muscles(c, ex) or [])
    subjects = trained | muscles
    if not subjects:
        return 0
    cur = c.execute("UPDATE flags SET consumed_at = ? WHERE consumed_at IS NULL AND subject IN (%s)" % placeholders(len(subjects)),
                    [datetime.now().isoformat(timespec="seconds")] + sorted(subjects))
    return cur.rowcount


def add_flag(subject, reason):
    if not reason:
        raise RepsError("flag reason is required")
    c = conn()
    created = datetime.now().isoformat(timespec="seconds")
    cur = c.execute("INSERT INTO flags (subject, reason, created, consumed_at) VALUES (?, ?, ?, NULL)",
                    (subject.strip().lower(), reason, created))
    c.commit()
    return {"flag_id": cur.lastrowid, "subject": subject.strip().lower()}


def list_flags():
    c = conn()
    rows = c.execute("SELECT * FROM flags WHERE consumed_at IS NULL ORDER BY id").fetchall()
    return [dict(r) for r in rows]


def consume_flag(flag_id):
    c = conn()
    try:
        flag_id = int(flag_id)
    except (TypeError, ValueError):
        raise RepsError("no such flag")
    cur = c.execute("UPDATE flags SET consumed_at = ? WHERE id = ? AND consumed_at IS NULL",
                    (datetime.now().isoformat(timespec="seconds"), flag_id))
    if cur.rowcount == 0:
        raise RepsError("no such unconsumed flag")
    c.commit()
    return {"consumed": flag_id}


def add_rule(text, subject, expires=None, evidence=""):
    if not text:
        raise RepsError("rule text is required")
    if not subject:
        raise RepsError("rule subject is required")
    if expires is not None:
        try:
            expires = date.fromisoformat(expires).isoformat()
        except ValueError:
            raise RepsError("expiry must be YYYY-MM-DD")
    c = conn()
    today = date.today().isoformat()
    created = datetime.now().isoformat(timespec="seconds")
    cur = c.execute("INSERT INTO rules (subject, text, start_date, expiry, status, created) VALUES (?, ?, ?, ?, 'active', ?)",
                    (subject.strip().lower(), text, today, expires, created))
    rid = cur.lastrowid
    change = record_change(c, "rule", str(rid),
                           {"rule_id": rid, "action": "add", "text": None,
                            "subject": None, "expiry": None, "status": None},
                           {"rule_id": rid, "action": "add", "text": text,
                            "subject": subject.strip().lower(), "expiry": expires,
                            "status": "active"},
                           evidence)
    c.commit()
    return {"rule_id": rid, "subject": subject.strip().lower(), "expiry": expires,
            "change_id": change["change_id"]}


def rule_status_rows(c):
    return [dict(r) for r in c.execute("SELECT * FROM rules WHERE status = 'active' ORDER BY id").fetchall()]


def rules_with_confirm(c):
    today = date.today()
    out = []
    for r in rule_status_rows(c):
        needs = bool(r["expiry"] and (date.fromisoformat(r["expiry"]) - today).days <= 7)
        entry = dict(r)
        entry["needs_confirm"] = needs
        out.append(entry)
    return out


def list_rules(expiring_within=None):
    c = conn()
    out = rules_with_confirm(c)
    today = date.today()
    if expiring_within is not None:
        try:
            window = int(expiring_within)
        except (TypeError, ValueError):
            raise RepsError("expiring-within must be an integer")
        out = [r for r in out if r["expiry"] and (date.fromisoformat(r["expiry"]) - today).days <= window]
    return out


def _rule_image(row):
    if row is None:
        return {"rule_id": 0, "action": "add", "text": None,
                "subject": None, "expiry": None, "status": None}
    return {"rule_id": row["id"], "action": "add", "text": row["text"],
            "subject": row["subject"], "expiry": row["expiry"], "status": row["status"]}


def confirm_rule(rule_id, extend=None, archive=False, evidence=""):
    c = conn()
    try:
        rule_id = int(rule_id)
    except (TypeError, ValueError):
        raise RepsError("no such rule")
    row = c.execute("SELECT * FROM rules WHERE id = ?", (rule_id,)).fetchone()
    if not row:
        raise RepsError("no such rule")
    before = _rule_image(dict(row))
    if archive:
        c.execute("UPDATE rules SET status = 'archived' WHERE id = ?", (rule_id,))
        after = dict(before, action="archive", status="archived")
    elif extend:
        try:
            expiry = date.fromisoformat(extend).isoformat()
        except ValueError:
            raise RepsError("extend date must be YYYY-MM-DD")
        c.execute("UPDATE rules SET expiry = ?, status = 'active' WHERE id = ?", (expiry, rule_id))
        after = dict(before, action="extend", expiry=expiry, status="active")
    else:
        raise RepsError("rule confirm needs an extend date or archive true")
    change = record_change(c, "rule", str(rule_id), before, after, evidence)
    c.commit()
    return {"rule_id": rule_id, "archived": archive, "expiry": extend if not archive else None,
            "change_id": change["change_id"]}


def programmed_weekly_volume(c, split_rows=None):
    """Programmed weekly sets per muscle from the active split and rotation.

    Full credit per mapped muscle like plan volume, scaled from cycle length
    to a week. All tracked muscles initialize at zero so removed muscles read
    0, not absent. Unmapped movements contribute nothing.
    """
    constants = load_constants()
    totals = {m: 0 for m in constants.muscles}
    rows = split_rows if split_rows is not None else read_split("active", c=c)
    for r in rows:
        for move in parse_movements(r["movements"]):
            for mu in lift_muscles(c, move) or []:
                if mu in totals:
                    totals[mu] += r["sets"]
    cycle = get_rotation(c)
    cycle_days = len(cycle) if cycle else 7
    return {m: round(v * 7.0 / cycle_days, 1) for m, v in totals.items()}


def muscles_for_movements(c, text):
    """Tracked and untracked mapped muscles for a movements cell."""
    out = set()
    for move in parse_movements(text):
        out.update(lift_muscles(c, move) or [])
    return out


def mev_floor_warnings(after_vol, affected):
    """Below-MEV warnings scoped to edited muscles only. MEV 0 muscles never warn."""
    constants = load_constants()
    out = []
    for m in sorted(affected):
        entry = constants.muscles.get(m)
        if entry is None or entry.mev == 0:
            continue
        if after_vol.get(m, 0) < entry.mev:
            out.append(f"{m}: programmed {after_vol.get(m, 0)}/wk below MEV {entry.mev} after this edit")
    return out
