# SSOT owner: training block dates, confirmed program changes, and block lift comparisons.

from collections import defaultdict
from datetime import date
from sqlite3 import Connection

from .constants import load_constants
from .db import conn
from .errors import RepsError
from .history import list_changes, value_at
from .trends import is_slipping, is_stalling


def _day(value: str) -> str:
    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError):
        raise RepsError("block date must be YYYY-MM-DD") from None
    if parsed.isoformat() != value:
        raise RepsError("block date must be YYYY-MM-DD")
    if parsed > date.today():
        raise RepsError("block date cannot be in the future")
    return value


def _coach_note(note: str) -> str:
    if not isinstance(note, str) or not note.strip():
        raise RepsError("a final coach note is required to close a block")
    return note.strip()


def block_on(c: Connection, day: str) -> dict | None:
    row = c.execute(
        "SELECT * FROM training_block WHERE start_date <= ? AND (end_date IS NULL OR end_date >= ?)",
        (day, day),
    ).fetchone()
    return dict(row) if row else None


def current_block(c: Connection, day: str) -> dict | None:
    block = block_on(c, day)
    return block if block and block["end_date"] is None else None


def require_block(c: Connection, day: str) -> dict:
    block = block_on(c, day)
    if block is None:
        raise RepsError(f"no block covers {day}. Start a block or correct its dates first")
    return block


def _get(c: Connection, block_id: int) -> dict:
    row = c.execute("SELECT * FROM training_block WHERE id = ?", (block_id,)).fetchone()
    if row is None:
        raise RepsError("no such training block")
    return dict(row)


def _check_span(c: Connection, start: str, end: str | None, block_id: int | None = None) -> None:
    if end is not None and end < start:
        raise RepsError("block end cannot precede its start")
    if c.execute(
        "SELECT 1 FROM training_block WHERE id IS NOT ? "
        "AND (? IS NULL OR start_date <= ?) AND (end_date IS NULL OR end_date >= ?)",
        (block_id, end, end, start),
    ).fetchone():
        raise RepsError("training blocks cannot overlap")


def _check_coverage(c: Connection) -> None:
    uncovered = c.execute(
        "SELECT w.id, w.date FROM workouts w WHERE w.status != 'rest' AND NOT EXISTS "
        "(SELECT 1 FROM training_block b WHERE b.start_date <= w.date "
        "AND (b.end_date IS NULL OR b.end_date >= w.date)) ORDER BY w.date, w.id LIMIT 1"
    ).fetchone()
    if uncovered:
        raise RepsError(f"workout {uncovered['id']} on {uncovered['date']} would be outside every block")


def slot_diff_text(before: dict | None, after: dict | None) -> str:
    if before is None:
        return f"added {after['movements']} x{after['sets']}"
    if after is None:
        return f"removed {before['movements']}"
    moves_changed = before["movements"] != after["movements"]
    sets_changed = before["sets"] != after["sets"]
    if moves_changed and sets_changed:
        return (f"{before['movements']} {before['sets']} sets -> "
                f"{after['movements']} {after['sets']} sets")
    if moves_changed:
        return f"{before['movements']} -> {after['movements']}"
    if sets_changed:
        return f"{before['movements']}: {before['sets']} sets -> {after['sets']} sets"
    return ""


def _changes(c: Connection, previous_end: str, start: str, through_id: int | None = None) -> list[dict]:
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for change in list_changes("program", until=start, c=c):
        if change["subject"].startswith("active:"):
            groups[("slots", change["subject"])].append(change)
    rotation = list_changes("rotation", "rotation", until=start, c=c)
    if rotation:
        groups[("rotation", "Rotation")] = rotation
    out = []
    for (key, subject), history in groups.items():
        if through_id is not None:
            history = [change for change in history if change["id"] <= through_id]
        relevant = [change for change in history if change["date"] > previous_end]
        if not relevant:
            continue
        before = value_at(history, previous_end, key)
        after = relevant[-1]["after"].get(key)
        if key == "slots":
            left = {slot["slot"]: slot for slot in before or []}
            right = {slot["slot"]: slot for slot in after or []}
            details = [slot_diff_text(left.get(i), right.get(i))
                       for i in sorted(left.keys() | right.keys())]
        elif before != after:
            fmt = lambda order: " / ".join(day or "rest" for day in order or []) or "unset"
            details = [f"{fmt(before)} -> {fmt(after)}"]
        else:
            details = []
        details = [item for item in details if item]
        if details:
            out.append({
                "change_id": relevant[-1]["id"],
                "subject": subject.removeprefix("active:"),
                "details": details,
                "source_ids": [change["id"] for change in relevant],
            })
    return out


def _draft(c: Connection, start: str) -> dict:
    if c.execute("SELECT 1 FROM training_block WHERE end_date IS NULL").fetchone():
        raise RepsError("close the active block before starting another")
    latest = c.execute("SELECT end_date FROM training_block ORDER BY start_date DESC LIMIT 1").fetchone()
    previous_end = latest["end_date"] if latest else None
    if previous_end is not None and start <= previous_end:
        raise RepsError("a new block must start after the previous block ends")
    return {"start_date": start, "previous_end": previous_end,
            "changes": _changes(c, previous_end, start) if previous_end else []}


def preview_start(start_date: str) -> dict:
    return _draft(conn(), _day(start_date))


def start_block(start_date: str, confirmed_change_ids: list[int]) -> dict:
    start = _day(start_date)
    c = conn()
    with c:
        c.execute("BEGIN IMMEDIATE")
        draft = _draft(c, start)
        candidates = {item["change_id"]: item for item in draft["changes"]}
        selected = set(confirmed_change_ids)
        if selected - candidates.keys():
            raise RepsError("program changes have changed. Preview the block start again")
        block_id = c.execute("INSERT INTO training_block(start_date) VALUES (?)", (start,)).lastrowid
        c.executemany(
            "INSERT INTO block_program_change(block_id, change_id, previous_end, start_date) VALUES (?, ?, ?, ?)",
            [(block_id, i, draft["previous_end"], start) for i in sorted(selected)],
        )
        _check_coverage(c)
    return block_view(c, _get(c, block_id))


def close_block(end_date: str, coach_note: str) -> dict:
    end = _day(end_date)
    note = _coach_note(coach_note)
    c = conn()
    with c:
        c.execute("BEGIN IMMEDIATE")
        row = c.execute("SELECT * FROM training_block WHERE end_date IS NULL").fetchone()
        if row is None:
            raise RepsError("no active block to close")
        if c.execute("SELECT 1 FROM workouts WHERE status = 'open'").fetchone():
            raise RepsError("close the open workout before closing the block")
        block_id = row["id"]
        _check_span(c, row["start_date"], end, block_id)
        c.execute("UPDATE training_block SET end_date = ?, coach_note = ? WHERE id = ?",
                  (end, note, block_id))
        _check_coverage(c)
    return block_view(c, _get(c, block_id))


def correct_block(block_id: int, start_date: str | None = None,
                  end_date: str | None = None, coach_note: str | None = None) -> dict:
    c = conn()
    with c:
        c.execute("BEGIN IMMEDIATE")
        block = _get(c, block_id)
        start = _day(start_date) if start_date is not None else block["start_date"]
        end = _day(end_date) if end_date is not None else block["end_date"]
        if block["end_date"] is None and (end_date is not None or coach_note is not None):
            raise RepsError("use the block close tool to save an end date and final note together")
        note = _coach_note(coach_note) if coach_note is not None else block["coach_note"]
        _check_span(c, start, end, block_id)
        c.execute("UPDATE training_block SET start_date = ?, end_date = ?, coach_note = ? WHERE id = ?",
                  (start, end, note, block_id))
        _check_coverage(c)
    return block_view(c, _get(c, block_id))


def block_view(c: Connection, block: dict) -> dict:
    rows = c.execute(
        "SELECT change_id, previous_end, start_date FROM block_program_change "
        "WHERE block_id = ? ORDER BY change_id", (block["id"],),
    ).fetchall()
    changes = []
    if rows:
        first = rows[0]
        selected = {row["change_id"] for row in rows}
        changes = [item for item in _changes(c, first["previous_end"], first["start_date"], max(selected))
                   if item["change_id"] in selected]
    return {**block, "changes": changes}


def blocks_view(c: Connection) -> list[dict]:
    return [block_view(c, dict(row)) for row in c.execute(
        "SELECT * FROM training_block ORDER BY start_date, id")]


def list_blocks() -> list[dict]:
    return blocks_view(conn())


def lift_comparisons(c: Connection, block_id: int | None = None) -> dict[int, dict[str, dict]]:
    """Per-block strength facts from completed, e1RM-counting training days."""
    thresholds = load_constants().thresholds
    rows = c.execute(
        "SELECT b.id AS block_id, s.exercise, w.date AS day, MAX(e1rm(s.weight, s.reps)) AS top "
        "FROM training_block b JOIN workouts w ON w.date >= b.start_date "
        "AND (b.end_date IS NULL OR w.date <= b.end_date) "
        "JOIN sets s ON s.workout_id = w.id "
        "WHERE w.status = 'done' AND s.reps <= ? AND (? IS NULL OR b.id = ?) "
        "GROUP BY b.id, s.exercise, w.date "
        "ORDER BY b.id, s.exercise, w.date", (thresholds.e1rm_cap_reps, block_id, block_id),
    )
    history: dict[tuple, list] = defaultdict(list)
    for row in rows:
        if row["top"] is not None:
            history[(row["block_id"], row["exercise"])].append((row["day"], row["top"]))
    out: dict[int, dict[str, dict]] = defaultdict(dict)
    t = thresholds.model_dump()
    for (block_id, exercise), days in history.items():
        series = [top for _, top in days]
        best_day, best = max(days, key=lambda pair: pair[1])
        drops = is_slipping(series, t)
        out[block_id][exercise] = {
            "sessions": len(days), "baseline": round(series[0], 1), "best": round(best, 1),
            "best_date": best_day, "last": round(series[-1], 1), "last_date": days[-1][0],
            "slipping": drops["drops_pct"] if drops else None,
            "stalling": not drops and is_stalling(series, t),
        }
    return dict(out)
