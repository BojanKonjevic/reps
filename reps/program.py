import json
import sqlite3
import sys
from datetime import date, datetime

from .constants import canon_muscle_name, load_constants
from .db import conn, open_workout, placeholders
from .memory import append_memory_state


def parse_movements(text):
    """Split a stored movements cell into a list of canonical names."""
    return [m.strip().lower() for m in text.split("/") if m.strip()]


def split_day_order(variant="active", c=None):
    """Day names in rotation order (rest entries excluded)."""
    c = c or conn()
    days = [r["day"] for r in c.execute(
        "SELECT DISTINCT day FROM splits WHERE variant = ?", (variant,)).fetchall()]
    rotation = parse_rotation(c)
    order = [d for d in rotation if d in days]
    return order + [d for d in sorted(days) if d not in order]


def read_split(variant="active", day=None, c=None):
    """Split rows as [{day, slot, movements, sets}], optionally one day."""
    c = c or conn()
    if day:
        rows = c.execute("SELECT day, slot, movements, sets FROM splits WHERE variant = ? AND day = ? ORDER BY slot",
                         (variant, day)).fetchall()
    else:
        rows = c.execute("SELECT day, slot, movements, sets FROM splits WHERE variant = ? ORDER BY day, slot",
                         (variant,)).fetchall()
    return [dict(r) for r in rows]


def parse_active_split_days(c=None):
    """Active split as {day: [movement, ...]} with interchangeable entries flattened."""
    days = {}
    for r in read_split("active", c=c):
        moves = days.setdefault(r["day"], [])
        for move in r["movements"].split("/"):
            move = move.strip().lower()
            if move:
                moves.append(move)
    return days


def parse_rotation(c=None):
    """Rotation order from meta."""
    c = c or conn()
    try:
        row = c.execute("SELECT value FROM meta WHERE key = 'rotation'").fetchone()
        return json.loads(row["value"]) if row else []
    except (sqlite3.Error, ValueError):
        return []


def weekly_volume(c, muscle, week_starts):
    from datetime import timedelta
    base = week_starts[0].isoformat()
    rows = c.execute("""
        SELECT date(w.date) as day, COUNT(*) as sets
        FROM sets s
        JOIN workouts w ON w.id = s.workout_id
        JOIN set_muscles sm ON sm.set_id = s.id
        WHERE sm.muscle = ? AND date(w.date) >= ?
        GROUP BY day
    """, (muscle, base)).fetchall()
    per_day = {r["day"]: r["sets"] for r in rows}
    out = []
    for ws in week_starts:
        we = ws + timedelta(days=7)
        out.append(sum(n for d, n in per_day.items() if ws.isoformat() <= d < we.isoformat()))
    return out


def count_bad_weeks(weekly, mev):
    """Zero and low week counts over the whole window (audit check 8 rule)."""
    if mev == 0:
        # MEV 0 means no direct work is required (covered indirectly),
        # so zero-set weeks meet the floor and never flag.
        return (0, 0)
    return (sum(1 for n in weekly if n == 0),
            sum(1 for n in weekly if 0 < n < mev))


def classify_volume(weekly, mev, mrv, vol_bad):
    """Shared volume classifier for plan status and audit flags.

    Below-MEV mirrors audit check 8 exactly (zero or low weeks counted over
    the whole window); above-MRV uses the recent-4-week average.
    """
    zero_weeks, low_weeks = count_bad_weeks(weekly, mev)
    if zero_weeks >= vol_bad or low_weeks >= vol_bad:
        return "below_mev"
    recent = weekly[-4:] if len(weekly) >= 4 else weekly
    avg = sum(recent) / len(recent) if recent else 0
    if mrv is not None and avg > mrv:
        return "above_mrv"
    return "in_range"


def volume_block(c):
    """Per-muscle weekly counts plus bounds and status, the same shape plan builds.

    Shared by plan and the dashboard snapshot so both read one computation.
    """
    from datetime import timedelta
    constants = load_constants()
    thresholds = constants.thresholds
    today = date.today()
    vol_weeks = thresholds.volume_window_weeks
    week_starts = [today - timedelta(days=today.weekday() + 7 * i) for i in range(vol_weeks - 1, -1, -1)]
    vol_bad = thresholds.volume_bad_weeks
    volume = {}
    for muscle, entry in constants.muscles.items():
        weekly = weekly_volume(c, muscle, week_starts)
        volume[muscle] = {"weekly": weekly, "mev": entry.mev, "mav": entry.mav,
                          "mrv": entry.mrv, "freq": entry.freq,
                          "status": classify_volume(weekly, entry.mev, entry.mrv, vol_bad)}
    return volume


def meta_get(c, key):
    row = c.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def compaction_due():
    # Meta only. No interface parses prose for this fact.
    c = conn()
    last = meta_get(c, "last_compacted")
    if last in (None, "", "never"):
        last = None
    postponed = meta_get(c, "compaction_postponed_until")
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


def meta_show(key=None):
    c = conn()
    if key:
        print(json.dumps({key: meta_get(c, key)}))
        return
    print(json.dumps({r["key"]: r["value"] for r in c.execute("SELECT key, value FROM meta ORDER BY key")}, indent=2))


def meta_set(key, value):
    if key not in ("last_compacted", "compaction_postponed_until", "rotation"):
        sys.exit("meta key must be one of last_compacted compaction_postponed_until rotation")
    if key == "last_compacted" and value not in ("never", ""):
        try:
            datetime.strptime(value, "%b %d %Y")
        except ValueError:
            sys.exit('last_compacted must be "never" or "Mon D YYYY" (e.g. Oct 1 2026)')
    if key == "compaction_postponed_until":
        try:
            value = date.fromisoformat(value).isoformat()
        except ValueError:
            sys.exit("compaction_postponed_until must be YYYY-MM-DD")
    if key == "rotation":
        try:
            parsed = json.loads(value)
        except ValueError:
            sys.exit("rotation must be a JSON array")
        if not isinstance(parsed, list) or not parsed:
            sys.exit("rotation must be a non-empty JSON array")
        value = json.dumps(parsed)
    c = conn()
    c.execute("INSERT INTO meta (key, value) VALUES (?, ?) "
              "ON CONFLICT (key) DO UPDATE SET value = excluded.value", (key, value))
    c.commit()
    print(json.dumps({"meta": key, "value": value}))


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


def priority_set(muscle, tier, until=None):
    muscle = muscle.strip().lower()
    if tier not in ("priority", "maintain", "deprioritize"):
        sys.exit("tier must be one of priority maintain deprioritize")
    constants = load_constants()
    known = set(constants.muscles) | set(constants.untracked)
    hit = canon_muscle_name(muscle, known)
    if hit is not None:
        muscle = hit
    if muscle not in constants.muscles:
        sys.exit(f"'{muscle}' is not a tracked muscle (untracked: {', '.join(constants.untracked)})")
    if until is not None:
        try:
            until = date.fromisoformat(until).isoformat()
        except ValueError:
            sys.exit("until must be YYYY-MM-DD")
    c = conn()
    c.execute("INSERT INTO priority (muscle, tier, since, until) VALUES (?, ?, ?, ?) "
              "ON CONFLICT (muscle) DO UPDATE SET tier = excluded.tier, since = excluded.since, until = excluded.until",
              (muscle, tier, date.today().isoformat(), until))
    c.commit()
    print(json.dumps({"priority": muscle, "tier": tier, "until": until}))


def priority_clear(muscle):
    c = conn()
    cur = c.execute("DELETE FROM priority WHERE muscle = ?", (muscle.strip().lower(),))
    c.commit()
    print(json.dumps({"cleared": muscle.strip().lower(), "rows": cur.rowcount}))


def priority_list():
    c = conn()
    rows = c.execute("SELECT * FROM priority ORDER BY muscle").fetchall()
    print(json.dumps([dict(r) for r in rows], indent=2))


def deload_set(scope, subject):
    if scope not in ("lift", "slot"):
        sys.exit("scope must be lift or slot (quote multi-word names)")
    if not subject:
        sys.exit("deload subject is required")
    c = conn()
    today = date.today().isoformat()
    if scope == "lift":
        subject = subject.strip().lower()
        if not c.execute("SELECT exercise FROM lift_muscle_map WHERE exercise = ?", (subject,)).fetchone():
            sys.exit(f"'{subject}' has no mapping (run muscle_map_set first)")
    else:
        match = next((d for d in split_day_order("active", c=c) if d.lower() == subject.strip().lower()), None)
        if not match:
            sys.exit(f"no active split day '{subject.strip()}' (see split show)")
        subject = match
    existing = c.execute("SELECT id FROM deload_state WHERE scope = ? AND subject = ? AND cleared_on IS NULL",
                         (scope, subject)).fetchone()
    if existing:
        print(json.dumps({"deload_id": existing["id"], "scope": scope, "subject": subject, "reused": True}))
        return
    cur = c.execute("INSERT INTO deload_state (scope, subject, set_on, cleared_on) VALUES (?, ?, ?, NULL)",
                    (scope, subject, today))
    c.commit()
    print(json.dumps({"deload_id": cur.lastrowid, "scope": scope, "subject": subject}))


def deload_clear():
    # Prose first: if the State write fails, the DB is untouched and a retry
    # is safe. A markdown edit must never break a DB command halfway.
    c = conn()
    rows = c.execute("SELECT scope, subject FROM deload_state WHERE cleared_on IS NULL ORDER BY id").fetchall()
    today = date.today().isoformat()
    for r in rows:
        append_memory_state(f"{today}: deload completed for {r['scope']} {r['subject']}")
    c.execute("UPDATE deload_state SET cleared_on = ? WHERE cleared_on IS NULL", (today,))
    c.commit()
    print(json.dumps({"cleared": len(rows)}))


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
    for r in read_split(variant, c=c):
        moves.update(parse_movements(r["movements"]))
    return moves


def day_movements(day, variant="active", c=None):
    moves = []
    for r in read_split(variant, day, c=c):
        moves.extend(parse_movements(r["movements"]))
    return moves


def best_split_day(trained, c=None):
    trained = set(trained)
    best_day, best_score = None, 0
    for day in split_day_order("active", c=c):
        score = len(trained & set(day_movements(day, c=c)))
        if score > best_score:
            best_day, best_score = day, score
    return best_day


def split_show(day=None, variant="active"):
    c = conn()
    if variant not in ("active", "baseline"):
        sys.exit("variant must be active or baseline")
    if day and not read_split(variant, day, c=c):
        sys.exit(f"no {variant} split day '{day}'")
    lines = []
    for d in ([day] if day else split_day_order(variant, c=c)):
        lines.append(f"### {d}")
        for r in read_split(variant, d, c=c):
            lines.append(f"{r['slot']}. {r['movements']} x{r['sets']}")
    print("\n".join(lines))


def split_set(day, slot, movements, sets, variant="active"):
    c = conn()
    if variant not in ("active", "baseline"):
        sys.exit("variant must be active or baseline (quote multi-word day names)")
    try:
        slot = int(slot)
        sets = int(sets)
    except (TypeError, ValueError):
        sys.exit("slot and sets must be integers")
    if sets <= 0:
        sys.exit("sets must be positive")
    movements = movements.strip().lower()
    if not movements:
        sys.exit("movements cannot be empty")
    for move in parse_movements(movements):
        if not c.execute("SELECT exercise FROM lift_muscle_map WHERE exercise = ?", (move,)).fetchone():
            sys.exit(f"'{move}' has no mapping (run muscle_map_set first), split unchanged")
    before = c.execute("SELECT movements FROM splits WHERE variant = ? AND day = ? AND slot = ?",
                       (variant, day, slot)).fetchone()
    c.execute("INSERT INTO splits (variant, day, slot, movements, sets) VALUES (?, ?, ?, ?, ?) "
              "ON CONFLICT (variant, day, slot) DO UPDATE SET movements = excluded.movements, sets = excluded.sets",
              (variant, day, slot, movements, sets))
    c.commit()
    out = {"split": variant, "day": day, "slot": slot, "movements": movements, "sets": sets}
    if variant == "active":
        # MEV floor warns, never blocks: a human reviews split set first.
        # Scoped to muscles in the before or after movements only, so fresh
        # programs do not cry wolf about unrelated gaps.
        affected = muscles_for_movements(c, movements)
        if before:
            affected |= muscles_for_movements(c, before["movements"])
        warnings = mev_floor_warnings(programmed_weekly_volume(c), affected)
        if warnings:
            out["warnings"] = warnings
    print(json.dumps(out))


def split_move(day, exercise, to_slot):
    c = conn()
    exercise = exercise.strip().lower()
    try:
        to_slot = int(to_slot)
    except (TypeError, ValueError):
        sys.exit("slot must be an integer")
    rows = read_split("active", day, c=c)
    if not rows:
        sys.exit(f"no active split day '{day}'")
    origin = next((r for r in rows if exercise in parse_movements(r["movements"])), None)
    if not origin:
        sys.exit(f"'{exercise}' is not in {day}")
    if len(parse_movements(origin["movements"])) > 1:
        sys.exit(f"'{exercise}' shares slot {origin['slot']} ({origin['movements']}); "
                 f"use split set to rearrange interchangeable pairs explicitly")
    carry_sets = origin["sets"]
    remaining = []
    for r in rows:
        kept = [m for m in (m.strip() for m in r["movements"].split("/")) if m.lower() != exercise]
        if kept:
            remaining.append({"movements": " / ".join(kept), "sets": r["sets"]})
    to_slot = max(1, min(to_slot, len(remaining) + 1))
    remaining.insert(to_slot - 1, {"movements": exercise, "sets": carry_sets})
    c.execute("DELETE FROM splits WHERE variant = 'active' AND day = ?", (day,))
    for i, r in enumerate(remaining, 1):
        c.execute("INSERT INTO splits (variant, day, slot, movements, sets) VALUES ('active', ?, ?, ?, ?)",
                  (day, i, r["movements"], r["sets"]))
    c.commit()
    print(json.dumps({"moved": exercise, "day": day, "to_slot": to_slot}))


def split_reconcile(day, after=None):
    c = conn()
    if not read_split("active", day, c=c):
        sys.exit(f"no active split day '{day}'")
    w = open_workout(c)
    if not w:
        w = c.execute("SELECT * FROM workouts WHERE status = 'done' ORDER BY date DESC, id DESC LIMIT 1").fetchone()
    if not w:
        sys.exit("no workout to reconcile from")
    trained = [r["exercise"] for r in c.execute(
        "SELECT exercise, MIN(id) m FROM sets WHERE workout_id = ? GROUP BY exercise ORDER BY m",
        (w["id"],)).fetchall()]
    known = split_all_movements("active", c=c)
    new = [ex for ex in trained if ex not in known]
    if not new:
        print(json.dumps({"reconciled": day, "added": []}))
        return
    rows = read_split("active", day, c=c)
    if after:
        anchor = next((r for r in rows if after.strip().lower() in parse_movements(r["movements"])), None)
        if not anchor:
            sys.exit(f"'{after}' is not in {day}")
        insert_at = anchor["slot"] + 1
    else:
        insert_at = len(rows) + 1
    new_slot_sets = load_constants().thresholds.default_new_slot_sets
    for i, ex in enumerate(new):
        c.execute("UPDATE splits SET slot = slot + 1 WHERE variant = 'active' AND day = ? AND slot >= ?",
                  (day, insert_at + i))
        c.execute("INSERT INTO splits (variant, day, slot, movements, sets) VALUES ('active', ?, ?, ?, ?)",
                  (day, insert_at + i, ex, new_slot_sets))
    c.commit()
    print(json.dumps({"reconciled": day, "added": new}))


def split_diff():
    c = conn()
    active = {(r["day"], r["slot"]): (r["movements"], r["sets"]) for r in read_split("active", c=c)}
    baseline = {(r["day"], r["slot"]): (r["movements"], r["sets"]) for r in read_split("baseline", c=c)}
    lines = []
    for key in sorted(set(active) | set(baseline)):
        a, b = active.get(key), baseline.get(key)
        if a != b:
            lines.append(f"{key[0]} #{key[1]}: baseline {b} vs active {a}")
    print("\n".join(lines) if lines else "active matches baseline")


def split_revert(day=None):
    c = conn()
    if day:
        base = read_split("baseline", day, c=c)
        if not base:
            sys.exit(f"no baseline split day '{day}'")
        c.execute("DELETE FROM splits WHERE variant = 'active' AND day = ?", (day,))
        for r in base:
            c.execute("INSERT INTO splits (variant, day, slot, movements, sets) VALUES ('active', ?, ?, ?, ?)",
                      (day, r["slot"], r["movements"], r["sets"]))
    else:
        c.execute("DELETE FROM splits WHERE variant = 'active'")
        for r in read_split("baseline", c=c):
            c.execute("INSERT INTO splits (variant, day, slot, movements, sets) VALUES ('active', ?, ?, ?, ?)",
                      (r["day"], r["slot"], r["movements"], r["sets"]))
    c.commit()
    print(json.dumps({"reverted": day or "all"}))


def consume_session_flags(c, workout_id):
    trained = {r["exercise"] for r in c.execute(
        "SELECT DISTINCT exercise FROM sets WHERE workout_id = ?", (workout_id,)).fetchall()}
    muscles = set()
    for ex in trained:
        mapping = c.execute("SELECT muscles FROM lift_muscle_map WHERE exercise = ?", (ex,)).fetchone()
        if mapping:
            muscles.update(mapping["muscles"].split(","))
    subjects = trained | muscles
    if not subjects:
        return 0
    cur = c.execute("UPDATE flags SET consumed_at = ? WHERE consumed_at IS NULL AND subject IN (%s)" % placeholders(len(subjects)),
                    [datetime.now().isoformat(timespec="seconds")] + sorted(subjects))
    return cur.rowcount


def flag_add(subject, reason):
    if not reason:
        sys.exit("flag reason is required")
    c = conn()
    created = datetime.now().isoformat(timespec="seconds")
    cur = c.execute("INSERT INTO flags (subject, reason, created, consumed_at) VALUES (?, ?, ?, NULL)",
                    (subject.strip().lower(), reason, created))
    c.commit()
    print(json.dumps({"flag_id": cur.lastrowid, "subject": subject.strip().lower()}))


def flag_list():
    c = conn()
    rows = c.execute("SELECT * FROM flags WHERE consumed_at IS NULL ORDER BY id").fetchall()
    print(json.dumps([dict(r) for r in rows], indent=2))


def flag_consume(flag_id):
    c = conn()
    try:
        flag_id = int(flag_id)
    except (TypeError, ValueError):
        sys.exit("no such flag")
    cur = c.execute("UPDATE flags SET consumed_at = ? WHERE id = ? AND consumed_at IS NULL",
                    (datetime.now().isoformat(timespec="seconds"), flag_id))
    if cur.rowcount == 0:
        sys.exit("no such unconsumed flag (see flag list)")
    c.commit()
    print(json.dumps({"consumed": flag_id}))


def rule_add(text, subject, expires=None):
    if not text:
        sys.exit("rule text is required")
    if not subject:
        sys.exit("rule subject is required")
    if expires is not None:
        try:
            expires = date.fromisoformat(expires).isoformat()
        except ValueError:
            sys.exit("expiry must be YYYY-MM-DD")
    c = conn()
    today = date.today().isoformat()
    created = datetime.now().isoformat(timespec="seconds")
    cur = c.execute("INSERT INTO rules (subject, text, start_date, expiry, status, created) VALUES (?, ?, ?, ?, 'active', ?)",
                    (subject.strip().lower(), text, today, expires, created))
    c.commit()
    print(json.dumps({"rule_id": cur.lastrowid, "subject": subject.strip().lower(), "expiry": expires}))


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


def rule_list(expiring_within=None):
    c = conn()
    out = rules_with_confirm(c)
    today = date.today()
    if expiring_within is not None:
        try:
            window = int(expiring_within)
        except (TypeError, ValueError):
            sys.exit("expiring-within must be an integer")
        out = [r for r in out if r["expiry"] and (date.fromisoformat(r["expiry"]) - today).days <= window]
    print(json.dumps(out, indent=2))


def rule_confirm(rule_id, extend=None, archive=False):
    c = conn()
    try:
        rule_id = int(rule_id)
    except (TypeError, ValueError):
        sys.exit("no such rule")
    row = c.execute("SELECT * FROM rules WHERE id = ?", (rule_id,)).fetchone()
    if not row:
        sys.exit("no such rule")
    if archive:
        c.execute("UPDATE rules SET status = 'archived' WHERE id = ?", (rule_id,))
    elif extend:
        try:
            expiry = date.fromisoformat(extend).isoformat()
        except ValueError:
            sys.exit("extend date must be YYYY-MM-DD")
        c.execute("UPDATE rules SET expiry = ?, status = 'active' WHERE id = ?", (expiry, rule_id))
    else:
        sys.exit("rule confirm needs an extend date or archive true")
    c.commit()
    print(json.dumps({"rule_id": rule_id, "archived": archive, "expiry": extend if not archive else None}))


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
            mapping = c.execute("SELECT muscles FROM lift_muscle_map WHERE exercise = ?", (move,)).fetchone()
            if not mapping:
                continue
            for mu in mapping["muscles"].split(","):
                if mu in totals:
                    totals[mu] += r["sets"]
    cycle = parse_rotation(c)
    cycle_days = len(cycle) if cycle else 7
    return {m: round(v * 7.0 / cycle_days, 1) for m, v in totals.items()}


def muscles_for_movements(c, text):
    """Tracked and untracked mapped muscles for a movements cell."""
    out = set()
    for move in parse_movements(text):
        mapping = c.execute("SELECT muscles FROM lift_muscle_map WHERE exercise = ?", (move,)).fetchone()
        if mapping:
            out.update(mapping["muscles"].split(","))
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
