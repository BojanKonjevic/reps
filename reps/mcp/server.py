"""reps.mcp: canonical machine interface for agents.

MCP is the sole normal way to operate Reps. These tools are thin adapters:
each handler translates structured MCP inputs into one existing Reps
domain operation and returns its result. No business logic lives here;
invariants are enforced once, in the domain modules.

Result contract: every tool returns a dict with "ok" true/false.
- ok true with JSON output: {"ok": true, "data": <parsed payload>}
- ok true with prose output: {"ok": true, "output": <text>}
- failure (domain refused, e.g. bad id or invariant): {"ok": false,
  "error": <reason>, "output": <partial output>}
"""

import io
import json
from contextlib import redirect_stdout
from typing import Optional

from mcp.server import MCPServer

from reps import adherence as _adherence
from reps import audit as _audit
from reps import autoreg as _autoreg
from reps import constants as _constants
from reps import goals as _goals
from reps import muscles as _muscles
from reps import plan as _plan
from reps import program as _program
from reps import progression as _progression
from reps import sessions as _sessions
from reps import sync as _sync

mcp = MCPServer("reps")


async def list_tool_names() -> list[str]:
    """Tool names through the MCP interface (what an agent discovers)."""
    return [t.name for t in await mcp.list_tools()]


def _payload_from_text(texts: list[str]):
    """Parse the JSON text content of a tool result, or return raw text."""
    text = "".join(texts)
    try:
        return json.loads(text)
    except ValueError:
        return {"output": text}


async def call_tool(name: str, arguments: dict) -> dict:
    """Invoke one tool through the MCP interface and return its structured result."""
    result = await mcp.call_tool(name, arguments)
    structs = getattr(result, "structured_content", None)
    if isinstance(structs, dict) and structs:
        return structs
    texts = [b.text for b in getattr(result, "content", []) if hasattr(b, "text")]
    if texts:
        return _payload_from_text(texts)
    return {}


def run_domain(fn, *args, **kwargs) -> dict:
    """Invoke one domain operation, capturing its printed result.

    Domain functions print JSON or prose and signal refusal via
    SystemExit. This adapter converts that convention into the MCP
    result contract without reimplementing any domain behavior.
    """
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            fn(*args, **kwargs)
    except SystemExit as e:
        reason = e.code if isinstance(e.code, str) and e.code else "refused"
        return {"ok": False, "error": reason, "output": buf.getvalue()}
    except Exception as e:  # unexpected bug, never a domain refusal
        return {"ok": False, "error": f"{type(e).__name__}: {e}", "output": buf.getvalue()}
    text = buf.getvalue()
    if text.strip():
        try:
            return {"ok": True, "data": json.loads(text)}
        except ValueError:
            return {"ok": True, "output": text}
    return {"ok": True, "output": ""}


# === sessions ===


@mcp.tool()
def session_start(note: str = "") -> dict:
    """Open a new workout. Workouts are only created explicitly, never auto-created.

    Args:
        note: Optional opening note for the session.
    """
    return run_domain(_sessions.start, note)


@mcp.tool()
def session_log_set(exercise: str, weight: float, reps: int, note: str = "",
                    muscles: str = "", bodyweight: bool = False) -> dict:
    """Log one set into the open workout. Fails when no workout is open.

    Args:
        exercise: Canonical lift name (lowercase training name).
        weight: Load in kg (extra only for weighted bodyweight work, 0 with bodyweight flag for true bodyweight).
        reps: Performed reps, positive integer.
        note: Free feel/form note. Failure is the silent default, never logged.
        muscles: Comma list for first use of a movement, recorded forever.
        bodyweight: True only for true bodyweight-only moves logged at 0.
    """
    return run_domain(_sessions.log, exercise, weight, reps, note, muscles, bodyweight)


@mcp.tool()
def session_update_set(set_id: int, field: str, value: str) -> dict:
    """Correct one set by id.

    Args:
        set_id: Exact set id (confirm in chat before destructive calls).
        field: One of weight, reps, exercise, note.
        value: New value.
    """
    return run_domain(_sessions.update, set_id, field, value)


@mcp.tool()
def session_update_workout(workout_id: int, field: str, value: str) -> dict:
    """Correct one workout by id (fields: notes, date, status).

    Args:
        workout_id: Exact workout id.
        field: One of notes, date, status.
        value: New value.
    """
    return run_domain(_sessions.update_workout, workout_id, field, value)


@mcp.tool()
def session_delete_set(set_id: int) -> dict:
    """Delete one set by id. Confirm the exact id in chat first.

    Args:
        set_id: Exact set id.
    """
    return run_domain(_sessions.delete_set, set_id)


@mcp.tool()
def session_delete_workout(workout_id: int) -> dict:
    """Delete one workout by id. Confirm the exact id in chat first.

    Args:
        workout_id: Exact workout id.
    """
    return run_domain(_sessions.delete_workout, workout_id)


@mcp.tool()
def session_end(note: str = "", force: str = "") -> dict:
    """Close the open workout after the end gate passes (progression for every
    trained lift, new exercises reconciled, deload note when training deloaded).

    Args:
        note: Short session summary (feel, sleep, pain, what moved well).
        force: Reason to skip writeback items, recorded in the workout note. Never skips missing muscles.
    """
    return run_domain(_sessions.end, note, force or None)


@mcp.tool()
def session_check(note: str = "") -> dict:
    """Preview the end gate without closing: what is still outstanding.

    Args:
        note: Draft end note to check against the gate.
    """
    return run_domain(_sessions.check, note)


@mcp.tool()
def session_rest(day: str, note: str = "") -> dict:
    """Mark a day as rest. Rest is tracked explicitly, never inferred.

    Args:
        day: Date yyyy-mm-dd. Backfill allowed, future refused.
        note: Optional rest note.
    """
    return run_domain(_sessions.rest, day, note)


@mcp.tool()
def session_weigh(kg: float, note: str = "") -> dict:
    """Log a bodyweight entry (gym scale, one per day is enough).

    Args:
        kg: Bodyweight in kg.
        note: Optional note.
    """
    return run_domain(_sessions.weigh, kg, note)


@mcp.tool()
def session_today() -> dict:
    """Ground truth for the open workout and today's sets."""
    return run_domain(_sessions.today)


@mcp.tool()
def session_exercises() -> dict:
    """Every known exercise name for canonical-name checks before logging."""
    return run_domain(_sessions.exercises)


@mcp.tool()
def session_history(exercise: str, limit: int = 50) -> dict:
    """Recent sets for one exercise, newest first.

    Args:
        exercise: Canonical lift name.
        limit: Max rows.
    """
    return run_domain(_sessions.history, exercise, limit)


@mcp.tool()
def session_get(day: str) -> dict:
    """Full detail for one dated session.

    Args:
        day: Date yyyy-mm-dd.
    """
    return run_domain(_sessions.session, day)


@mcp.tool()
def session_range(from_date: str, to_date: str) -> dict:
    """Review-mode bulk pull over a date range. Feeds agent reasoning, never shown raw.

    Args:
        from_date: Start yyyy-mm-dd.
        to_date: End yyyy-mm-dd.
    """
    return run_domain(_sessions.session_range, from_date, to_date)


@mcp.tool()
def session_notes(limit: int = 200) -> dict:
    """Recent set/session notes for pain and feel context.

    Args:
        limit: Max rows.
    """
    return run_domain(_sessions.notes, limit)


@mcp.tool()
def session_calendar() -> dict:
    """Workout calendar with PR days and rotation verdicts."""
    return run_domain(_sessions.calendar)


@mcp.tool()
def session_stats() -> dict:
    """Aggregate training numbers."""
    return run_domain(_sessions.stats)


@mcp.tool()
def session_context(limit: int = 3) -> dict:
    """Canonical lift names plus recent context for disambiguation.

    Args:
        limit: Sessions of context.
    """
    return run_domain(_sessions.context, limit)


# === muscles ===


@mcp.tool()
def muscle_map_show(exercise: str = "") -> dict:
    """Recorded muscle mapping (authoritative per lift) and setup notes.

    Args:
        exercise: Lift name, or empty for the full map.
    """
    return run_domain(_muscles.map_show, exercise or None)


@mcp.tool()
def muscle_map_set(exercise: str, muscles: str, bodyweight: bool = False) -> dict:
    """Record the muscle answer for a movement forever.

    Args:
        exercise: Lift name.
        muscles: Comma list of tracked groups.
        bodyweight: True for bodyweight-only moves.
    """
    return run_domain(_muscles.retag, exercise, muscles, bodyweight)


@mcp.tool()
def muscle_map_note(exercise: str, text: str) -> dict:
    """Write a permanent per-movement setup fact (setup values live here, never in set notes).

    Args:
        exercise: Lift name.
        text: Setup fact.
    """
    return run_domain(_muscles.map_note, exercise, text)


@mcp.tool()
def muscle_rename(old: str, new: str) -> dict:
    """Merge duplicate lift names, keeping history.

    Args:
        old: Existing name to merge away.
        new: Canonical surviving name.
    """
    return run_domain(_muscles.rename, old, new)


# === plan ===


@mcp.tool()
def plan(slot: str = "", verbose: bool = False) -> dict:
    """Computed session state bundle: today, slot guess, volume, ledger, lifts,
    split, goals, rules, progression, flags, priority, deload, autoreg. Read
    this first at session start, before MEMORY.md judgment state.

    Args:
        slot: Override the slot guess with an explicit day.
        verbose: Include the full ledger detail.
    """
    return run_domain(_plan.plan, slot or None, verbose)


# === program ===


@mcp.tool()
def program_split_show(day: str = "", variant: str = "active") -> dict:
    """Read the program. Active is the exact program planned from; baseline is reference only.

    Args:
        day: Optional single day.
        variant: active or baseline.
    """
    return run_domain(_program.split_show, day or None, variant)


@mcp.tool()
def program_split_set(day: str, slot: int, movements: str, sets: int,
                      variant: str = "active") -> dict:
    """Routine active-split update (one-off swaps add the alternate here, never a rewrite).

    Args:
        day: Split day name.
        slot: Slot number.
        movements: Movement expression.
        sets: Working set count.
        variant: active normally, baseline only for explicit major program changes.
    """
    return run_domain(_program.split_set, day, slot, movements, sets, variant)


@mcp.tool()
def program_split_move(day: str, exercise: str, to_slot: int) -> dict:
    """Move an exercise between slots on a day.

    Args:
        day: Split day name.
        exercise: Exercise to move.
        to_slot: Destination slot number.
    """
    return run_domain(_program.split_move, day, exercise, to_slot)


@mcp.tool()
def program_split_reconcile(day: str, after: str = "") -> dict:
    """Append newly logged exercises to a day (the end gate enforces this).

    Args:
        day: Split day name.
        after: Optional exercise to insert after.
    """
    return run_domain(_program.split_reconcile, day, after or None)


@mcp.tool()
def program_split_diff() -> dict:
    """Active versus baseline divergence."""
    return run_domain(_program.split_diff)


@mcp.tool()
def program_split_revert(day: str = "") -> dict:
    """Revert active toward baseline, whole program or one day.

    Args:
        day: Optional single day, or empty for the whole program.
    """
    return run_domain(_program.split_revert, day or None)


@mcp.tool()
def program_priority_set(muscle: str, tier: str, until: str = "") -> dict:
    """Bring a muscle up or down: tier breaks ties for slack volume.

    Args:
        muscle: Tracked muscle.
        tier: One of priority, maintain, deprioritize.
        until: Optional expiry date.
    """
    return run_domain(_program.priority_set, muscle, tier, until or None)


@mcp.tool()
def program_priority_clear(muscle: str) -> dict:
    """Clear a muscle priority tier.

    Args:
        muscle: Tracked muscle.
    """
    return run_domain(_program.priority_clear, muscle)


@mcp.tool()
def program_priority_list() -> dict:
    """Current muscle priority tiers."""
    return run_domain(_program.priority_list)


@mcp.tool()
def program_deload_set(scope: str, subject: str) -> dict:
    """Mark a lift or slot as deloaded (volume down per SCIENCE.md, trajectory resumes next session).

    Args:
        scope: One of lift, slot.
        subject: Lift or slot name.
    """
    return run_domain(_program.deload_set, scope, subject)


@mcp.tool()
def program_deload_clear() -> dict:
    """Clear deload state after the deload session ends (appends the dated state line)."""
    return run_domain(_program.deload_clear)


@mcp.tool()
def program_rule_add(text: str, subject: str = "", expires: str = "") -> dict:
    """Write a durable pref or plan down as a rule.

    Args:
        text: Rule text.
        subject: Optional subject the rule governs.
        expires: Optional expiry date.
    """
    return run_domain(_program.rule_add, text, subject or None, expires or None)


@mcp.tool()
def program_rule_list(expiring_within: Optional[int] = None) -> dict:
    """Rules with confirmation state (expired or expiring soon need one answer, then reactivate or archive).

    Args:
        expiring_within: Optional day window for the needs-confirm slice.
    """
    return run_domain(_program.rule_list, expiring_within)


@mcp.tool()
def program_rule_confirm(rule_id: int, extend: str = "", archive: bool = False) -> dict:
    """Reactivate (extend) or archive a rule. Nothing durable is deleted without an answer.

    Args:
        rule_id: Exact rule id.
        extend: New expiry date for reactivation.
        archive: Archive instead of extending.
    """
    return run_domain(_program.rule_confirm, rule_id, extend or None, archive)


@mcp.tool()
def program_flag_add(subject: str, reason: str) -> dict:
    """Flag clear over/underperformance versus ledger headroom.

    Args:
        subject: Exercise or muscle.
        reason: Why it is flagged.
    """
    return run_domain(_program.flag_add, subject, reason)


@mcp.tool()
def program_flag_list() -> dict:
    """Open flags."""
    return run_domain(_program.flag_list)


@mcp.tool()
def program_flag_consume(flag_id: int) -> dict:
    """Consume a flag that outlived its session.

    Args:
        flag_id: Exact flag id.
    """
    return run_domain(_program.flag_consume, flag_id)


@mcp.tool()
def program_meta_show(key: str = "") -> dict:
    """Rotation state and compaction markers.

    Args:
        key: Optional single key.
    """
    return run_domain(_program.meta_show, key or None)


@mcp.tool()
def program_meta_set(key: str, value: str) -> dict:
    """Write a meta key (rotation order, last_compacted). Never hand-count rotation dates.

    Args:
        key: One of rotation, last_compacted, compaction_postponed_until.
        value: New value (rotation takes a JSON day array).
    """
    return run_domain(_program.meta_set, key, value)


@mcp.tool()
def program_rotation_anchor(date: str, day: str) -> dict:
    """Anchor the rotation schedule to a date. Drift asks for a re-anchor, never re-anchors silently.

    Args:
        date: Anchor date yyyy-mm-dd.
        day: Rotation day trained that date.
    """
    return run_domain(_adherence.rotation_anchor, date, day)


@mcp.tool()
def program_rotation_status(from_date: str = "", to_date: str = "") -> dict:
    """Per-date rotation verdicts over a range. Adherence counts come from here, never a hand tally.

    Args:
        from_date: Start yyyy-mm-dd, defaults to the volume window.
        to_date: End yyyy-mm-dd, defaults to today.
    """
    return run_domain(_adherence.rotation_status, from_date or None, to_date or None)


# === progression and goals ===


@mcp.tool()
def progression_set(exercise: str, verdict: str, next_target: str, direction: str,
                    note: str = "", workout_id: Optional[int] = None) -> dict:
    """Judge one lift for the session just trained (every trained lift gets one at end).

    Args:
        exercise: Lift name.
        verdict: One of hit, miss, hold, baseline.
        next_target: Weight x reps for next time, e.g. 82.5x5 (reps required).
        direction: One of up, flat, down.
        note: Optional note.
        workout_id: Defaults to the open workout; pass an id to backfill a closed one.
    """
    return run_domain(_progression.progression_set, exercise, verdict, next_target,
                direction, note, workout_id)


@mcp.tool()
def progression_show(exercise: str = "") -> dict:
    """Progression state, one lift or all.

    Args:
        exercise: Optional lift name.
    """
    return run_domain(_progression.progression_show, exercise or None)


@mcp.tool()
def goal_add(exercise: str, target_e1rm: float, deadline: str, desc: str = "",
             start_e1rm: Optional[float] = None) -> dict:
    """Declare a goal: trajectory numbers become the strong prior for planning.

    Args:
        exercise: Lift name.
        target_e1rm: Target e1RM.
        deadline: Deadline date.
        desc: Optional description.
        start_e1rm: Optional starting e1RM (defaults to current best).
    """
    return run_domain(_goals.goal_add, exercise, target_e1rm, deadline, desc, start_e1rm)


@mcp.tool()
def goal_show(goal_id: str = "") -> dict:
    """Goal trajectories and progress.

    Args:
        goal_id: Optional single goal id.
    """
    return run_domain(_goals.goal_show, goal_id or None)


@mcp.tool()
def goal_rewrite(goal_id: int) -> dict:
    """Recut a goal trajectory after a session moved it.

    Args:
        goal_id: Exact goal id.
    """
    return run_domain(_goals.goal_rewrite, goal_id)


@mcp.tool()
def goal_drop(goal_id: int) -> dict:
    """Drop a goal.

    Args:
        goal_id: Exact goal id.
    """
    return run_domain(_goals.goal_drop, goal_id)


# === autoreg ===


@mcp.tool()
def autoreg_apply(day: str, slot: int, to_movements: str, to_sets: int,
                  evidence: str, from_movements: str = "") -> dict:
    """The single entry point for autonomous program edits (trims, adds, swaps).
    Runs the PROGRAMMING.md autoregulation pass first; refuses without permission,
    on holds, on from-guard mismatch, or below MEV.

    Args:
        day: Split day name.
        slot: Slot number.
        to_movements: New movement expression.
        to_sets: New set count.
        evidence: Quoted reason for the change.
        from_movements: Expected current movements (concurrent-edit guard).
    """
    return run_domain(_autoreg.autoreg_apply, day, slot, to_movements, to_sets,
                evidence, from_movements or None)


@mcp.tool()
def autoreg_log() -> dict:
    """Autonomous change ledger."""
    return run_domain(_autoreg.autoreg_log)


@mcp.tool()
def autoreg_revert(change_id: int) -> dict:
    """Restore a change's before-state exactly and clear matching holds.

    Args:
        change_id: Exact autoreg change id.
    """
    return run_domain(_autoreg.autoreg_revert, change_id)


# === analysis and configuration ===


@mcp.tool()
def audit_data() -> dict:
    """Full data quality check per docs/AUDIT.md."""
    return run_domain(_audit.audit)


@mcp.tool()
def doctor() -> dict:
    """Validate constants, DB, dashboard, and dump consistency."""
    return run_domain(_audit.doctor)


@mcp.tool()
def constants_show(key: str = "") -> dict:
    """Single source of truth for muscles, MEV/MAV/MRV, thresholds. My logged
    data beats SCIENCE.md defaults for my lifts; these defaults beat instinct.

    Args:
        key: Optional dotted key (e.g. muscles.chest, thresholds).
    """
    return run_domain(_constants.constants_show, key or None)


@mcp.tool()
def constants_validate() -> dict:
    """Validate constants.json structurally."""
    return run_domain(_constants.constants_validate)


@mcp.tool()
def constants_set(key: str, value: str) -> dict:
    """Edit one constants key (never by hand).

    Args:
        key: Dotted key to set.
        value: JSON-encoded new value (a JSON string holds a plain string).
    """
    return run_domain(_constants.constants_set, key, value)


# === snapshot and sync ===


@mcp.tool()
def snapshot_export() -> dict:
    """Full validated dashboard payload (history plus program and forward state).
    For the dashboard file only, never pulled in bulk into chat.
    """
    return run_domain(_sync.export)


@mcp.tool()
def sync_push(force: bool = False) -> dict:
    """Push the validated snapshot to the hosted dashboard and dump workouts.sql
    for git history. Pull-first with ETags: a stale base aborts with 412 unless forced.

    Args:
        force: Overwrite deliberately after reconciling a 412.
    """
    return run_domain(_sync.sync, force)


@mcp.tool()
def maintenance_dump() -> dict:
    """Re-write workouts.sql from the live DB without syncing (recovery and drift fixes)."""
    return run_domain(_sync.dump)


@mcp.tool()
def maintenance_restore(force: bool = False) -> dict:
    """Rebuild the live DB from workouts.sql into a temp file first, replacing
    only after verification. Refuses with an open workout unless forced.

    Args:
        force: Restore despite an open workout.
    """
    return run_domain(_sync.restore, force)
