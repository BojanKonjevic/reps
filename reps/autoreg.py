from datetime import date

from .errors import RepsError

from .constants import load_constants
from .db import conn
from .progression import top_e1rm_by_date
from .program import (mev_floor_warnings, muscles_for_movements,
                      parse_movements, programmed_weekly_volume,
                      read_split, rule_status_rows, split_day_order)


def autoreg_permitted(c):
    """True iff an active rule with subject autoreg authorizes the coach pass."""
    return any(r["subject"] == "autoreg" for r in rule_status_rows(c))


def autoreg_active_holds(c, today=None):
    """Unexpired autoreg_holds rows, oldest first."""
    today = today or date.today().isoformat()
    return [dict(r) for r in c.execute(
        "SELECT * FROM autoreg_holds WHERE hold_until >= ? ORDER BY id", (today,)).fetchall()]


def autoreg_miss_streaks(c):
    """Exercises ending in 2+ consecutive miss progression verdicts, newest first."""
    out = []
    for r in c.execute("SELECT DISTINCT exercise FROM progression").fetchall():
        ex = r["exercise"]
        rows = c.execute("SELECT verdict, workout_id FROM progression WHERE exercise = ? "
                         "ORDER BY workout_id DESC", (ex,)).fetchall()
        streak = 0
        for p in rows:
            if p["verdict"] == "miss":
                streak += 1
            else:
                break
        if streak >= 2:
            out.append({"exercise": ex, "streak": streak, "workout_id": rows[0]["workout_id"]})
    out.sort(key=lambda e: e["workout_id"], reverse=True)
    return [{"exercise": e["exercise"], "streak": e["streak"]} for e in out]


def autoreg_drop_watch(c):
    """Exercises whose last 3 top-set e1RMs show two consecutive drops at deload_watch_pct size.

    Deload sessions are filtered out first (they deliberately deviate).
    Deterministic reuse of top_e1rm_by_date, same shape as the Session report watch.
    """
    threshold = load_constants().thresholds.deload_watch_pct
    out = []
    for r in c.execute("SELECT DISTINCT exercise FROM sets").fetchall():
        ex = r["exercise"]
        clean = [(day, e) for day, e, notes, _ in top_e1rm_by_date(c, ex)
                 if "deload" not in (notes or "").lower()]
        if len(clean) < 3:
            continue
        (_, e1), (_, e2), (_, e3) = clean[-3:]
        if e1 <= 0 or e2 <= 0:
            continue
        p1, p2 = (e2 - e1) / e1 * 100, (e3 - e2) / e2 * 100
        if p1 <= threshold and p2 <= threshold:
            out.append({"exercise": ex, "drops_pct": [round(p1, 1), round(p2, 1)]})
    return sorted(out, key=lambda e: e["exercise"])


def autoreg_grouped(c, flagged):
    """Flagged lifts sharing a muscle with 2+ members each, via the mapping table."""
    groups: dict = {}
    for ex in flagged:
        mapping = c.execute("SELECT muscles FROM lift_muscle_map WHERE exercise = ?", (ex,)).fetchone()
        if not mapping:
            continue
        for mu in mapping["muscles"].split(","):
            groups.setdefault(mu, set()).add(ex)
    return {mu: sorted(members) for mu, members in sorted(groups.items()) if len(members) >= 2}


def autoreg_block(c):
    """Fresh autoreg signal bundle for plan."""
    miss = autoreg_miss_streaks(c)
    drop = autoreg_drop_watch(c)
    flagged = sorted({m["exercise"] for m in miss} | {d["exercise"] for d in drop})
    return {"permitted": autoreg_permitted(c),
            "holds": autoreg_active_holds(c),
            "miss_streaks": miss,
            "drop_watch": drop,
            "grouped": autoreg_grouped(c, flagged),
            "program_volume": programmed_weekly_volume(c)}


def apply_autoreg(day, slot, to_movements, to_sets, evidence, from_movements=None):
    """Single entry point for every autonomous program edit.

    Refuses, in order: no permission rule, missing slot, from-guard mismatch,
    unmapped movements, held slot, below-MEV result.
    """
    from datetime import timedelta
    c = conn()
    today = date.today().isoformat()
    if not autoreg_permitted(c):
        raise RepsError("autoreg has no standing permission (program_rule_add with subject autoreg)")
    try:
        slot = int(slot)
    except (TypeError, ValueError):
        raise RepsError(f"no active split slot '{slot}' on '{day}'")
    match = next((d for d in split_day_order("active", c=c) if d.lower() == (day or "").strip().lower()), None)
    if match is None:
        raise RepsError(f"no active split slot '{slot}' on '{day}'")
    day = match
    cur = next((r for r in read_split("active", day, c=c) if r["slot"] == slot), None)
    if cur is None:
        raise RepsError(f"no active split slot '{slot}' on '{day}'")
    if from_movements is not None and parse_movements(from_movements) != parse_movements(cur["movements"]):
        raise RepsError(f"from-guard mismatch: slot {slot} on '{day}' holds '{cur['movements']}', "
                 f"not '{from_movements.strip().lower()}' (refusing to clobber a concurrent edit)")
    to_movements = (to_movements or "").strip().lower()
    if not to_movements:
        raise RepsError("movements cannot be empty")
    try:
        to_sets = int(to_sets)
    except (TypeError, ValueError):
        raise RepsError("sets must be an integer")
    if to_sets <= 0:
        raise RepsError("sets must be positive")
    if not (evidence or "").strip():
        raise RepsError("evidence is required")
    for move in parse_movements(to_movements):
        if not c.execute("SELECT exercise FROM lift_muscle_map WHERE exercise = ?", (move,)).fetchone():
            raise RepsError(f"'{move}' has no mapping (run muscle_map_set first), split unchanged")
    held = c.execute("SELECT * FROM autoreg_holds WHERE day = ? AND movements = ? AND hold_until >= ?",
                     (day, cur["movements"], today)).fetchone()
    if held:
        raise RepsError(f"slot {slot} on '{day}' is held until {held['hold_until']}, revert first")
    simulated = [dict(r) for r in read_split("active", c=c)]
    for r in simulated:
        if r["day"] == day and r["slot"] == slot:
            r["movements"], r["sets"] = to_movements, to_sets
            break
    affected = muscles_for_movements(c, cur["movements"]) | muscles_for_movements(c, to_movements)
    below = mev_floor_warnings(programmed_weekly_volume(c, simulated), affected)
    if below:
        raise RepsError("below MEV, refusing: " + "; ".join(below))
    if parse_movements(to_movements) != parse_movements(cur["movements"]):
        action = "swap"
    elif to_sets < cur["sets"]:
        action = "trim"
    else:
        action = "add"
    c.execute("INSERT INTO splits (variant, day, slot, movements, sets) VALUES ('active', ?, ?, ?, ?) "
              "ON CONFLICT (variant, day, slot) DO UPDATE SET movements = excluded.movements, sets = excluded.sets",
              (day, slot, to_movements, to_sets))
    hold_until = None
    if action in ("trim", "swap"):
        hold_until = (date.today() + timedelta(days=8)).isoformat()
        c.execute("INSERT INTO autoreg_holds (day, movements, action, set_on, hold_until, reason) "
                  "VALUES (?, ?, ?, ?, ?, ?)",
                  (day, to_movements, action, today, hold_until, evidence.strip()))
    cur_change = c.execute(
        "INSERT INTO autoreg_changes (date, action, day, slot, before_movements, before_sets, "
        "after_movements, after_sets, evidence, reverted_on) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)",
        (today, action, day, slot, cur["movements"], cur["sets"], to_movements, to_sets, evidence.strip()))
    c.commit()
    return {"autoreg": action, "day": day, "slot": slot,
            "before": {"movements": cur["movements"], "sets": cur["sets"]},
            "after": {"movements": to_movements, "sets": to_sets},
            "hold_until": hold_until, "change_id": cur_change.lastrowid,
            "evidence": evidence.strip()}


def list_autoreg_changes():
    c = conn()
    rows = c.execute("SELECT * FROM autoreg_changes ORDER BY id").fetchall()
    return [{**dict(r), "reverted": r["reverted_on"] is not None} for r in rows]


def revert_autoreg_change(change_id):
    """Restore before state exactly; clears matching unexpired holds."""
    c = conn()
    today = date.today().isoformat()
    try:
        change_id = int(change_id)
    except (TypeError, ValueError):
        raise RepsError("no such autoreg change")
    row = c.execute("SELECT * FROM autoreg_changes WHERE id = ?", (change_id,)).fetchone()
    if not row:
        raise RepsError("no such autoreg change")
    if row["reverted_on"] is not None:
        raise RepsError(f"change {change_id} already reverted on {row['reverted_on']}")
    cur = next((r for r in read_split("active", row["day"], c=c) if r["slot"] == row["slot"]), None)
    if (cur is None or parse_movements(cur["movements"]) != parse_movements(row["after_movements"])
            or cur["sets"] != row["after_sets"]):
        raise RepsError(f"slot {row['slot']} on '{row['day']}' no longer matches the recorded after-state, reconcile manually")
    c.execute("INSERT INTO splits (variant, day, slot, movements, sets) VALUES ('active', ?, ?, ?, ?) "
              "ON CONFLICT (variant, day, slot) DO UPDATE SET movements = excluded.movements, sets = excluded.sets",
              (row["day"], row["slot"], row["before_movements"], row["before_sets"]))
    c.execute("UPDATE autoreg_changes SET reverted_on = ? WHERE id = ?", (today, change_id))
    cleared = c.execute("DELETE FROM autoreg_holds WHERE day = ? AND movements = ? AND hold_until >= ?",
                        (row["day"], row["after_movements"], today)).rowcount
    c.commit()
    return {"reverted": change_id, "day": row["day"], "slot": row["slot"],
            "restored": {"movements": row["before_movements"], "sets": row["before_sets"]},
            "holds_cleared": cleared}
