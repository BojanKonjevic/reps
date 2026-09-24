"""reps.mcp: canonical machine interface for agents.

MCP is the sole normal way to operate Reps. These tools are thin adapters:
each handler translates structured MCP inputs into one existing Reps
domain operation and returns its result. No business logic lives here;
invariants are enforced once, in the domain modules. Domain refusals
(RepsError) become error results; anything else propagates as a tool error.

Result contract: every tool returns a dict with "ok" true/false.
- ok true with structured output: {"ok": true, "data": <payload>}
- failure (domain refused): {"ok": false, "error": <reason>}
"""

import json
from collections.abc import Callable
from typing import Any, Literal, Optional

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
from reps.errors import RepsError

mcp = MCPServer("reps")

Verdict = Literal["hit", "miss", "hold", "baseline"]
Direction = Literal["up", "flat", "down"]
Tier = Literal["priority", "maintain", "deprioritize"]
Scope = Literal["lift", "slot"]
Variant = Literal["active", "baseline"]
SetField = Literal["weight", "reps", "exercise", "note"]
WorkoutField = Literal["notes", "date", "status"]


def call_domain(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> dict[str, Any]:
    """Call one domain operation and shape its return into the result contract.

    This translates values and domain exceptions only; it never parses
    output text, because domain functions return data directly.
    """
    try:
        result = fn(*args, **kwargs)
    except RepsError as e:
        return {"ok": False, "error": str(e)}
    return {"ok": True, "data": result}


async def list_tool_names() -> list[str]:
    """Tool names through the MCP interface (what an agent discovers)."""
    return [t.name for t in await mcp.list_tools()]


async def call_tool(name: str, arguments: dict) -> dict:
    """Invoke one tool through the MCP interface and return its structured result."""
    result = await mcp.call_tool(name, arguments)
    texts = [b.text for b in getattr(result, "content", []) if hasattr(b, "text")]
    if getattr(result, "isError", False):
        return {"ok": False, "error": "".join(texts)}
    structs = getattr(result, "structured_content", None)
    if isinstance(structs, dict) and structs:
        return structs
    if texts:
        try:
            return json.loads("".join(texts))
        except ValueError:
            return {"ok": True, "output": "".join(texts)}
    return {"ok": True, "data": None}


# === sessions ===


@mcp.tool()
def session_start(note: str = "") -> dict:
    """Open a new workout. Workouts are only created explicitly, never auto-created.

    Args:
        note: Optional opening note for the session.
    """
    return call_domain(_sessions.start_workout, note)


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
    return call_domain(_sessions.log_set, exercise, weight, reps, note, muscles, bodyweight)


@mcp.tool()
def session_update_set(set_id: int, field: SetField, value: str) -> dict:
    """Correct one set by id.

    Args:
        set_id: Exact set id (confirm in chat before destructive calls).
        field: One of weight, reps, exercise, note.
        value: New value.
    """
    return call_domain(_sessions.update_set, set_id, field, value)


@mcp.tool()
def session_update_workout(workout_id: int, field: WorkoutField, value: str) -> dict:
    """Correct one workout by id.

    Args:
        workout_id: Exact workout id.
        field: One of notes, date, status.
        value: New value.
    """
    return call_domain(_sessions.update_workout, workout_id, field, value)


@mcp.tool()
def session_delete_set(set_id: int) -> dict:
    """Delete one set by id. Confirm the exact id in chat first.

    Args:
        set_id: Exact set id.
    """
    return call_domain(_sessions.delete_set, set_id)


@mcp.tool()
def session_delete_workout(workout_id: int) -> dict:
    """Delete one workout by id. Confirm the exact id in chat first.

    Args:
        workout_id: Exact workout id.
    """
    return call_domain(_sessions.delete_workout, workout_id)


@mcp.tool()
def session_end(note: str = "", force: str = "") -> dict:
    """Close the open workout after the end gate passes (progression for every
    trained lift, new exercises reconciled, deload note when training deloaded).

    Args:
        note: Short session summary (feel, sleep, pain, what moved well).
        force: Reason to skip writeback items, recorded in the workout note. Never skips missing muscles.
    """
    return call_domain(_sessions.end_workout, note, force or None)


@mcp.tool()
def session_check(note: str = "") -> dict:
    """Preview the end gate without closing: what is still outstanding.

    Args:
        note: Draft end note to check against the gate.
    """
    return call_domain(_sessions.check_end_gate, note)


@mcp.tool()
def session_rest(day: str, note: str = "") -> dict:
    """Mark a day as rest. Rest is tracked explicitly, never inferred.

    Args:
        day: Date yyyy-mm-dd. Backfill allowed, future refused.
        note: Optional rest note.
    """
    return call_domain(_sessions.mark_rest, day, note)


@mcp.tool()
def session_weigh(kg: float, note: str = "") -> dict:
    """Log a bodyweight entry (gym scale, one per day is enough).

    Args:
        kg: Bodyweight in kg.
        note: Optional note.
    """
    return call_domain(_sessions.record_bodyweight, kg, note)


@mcp.tool()
def session_today() -> dict:
    """Ground truth for the open workout and today's sets."""
    return call_domain(_sessions.get_today)


@mcp.tool()
def session_exercises() -> dict:
    """Every known exercise name for canonical-name checks before logging."""
    return call_domain(_sessions.list_exercises)


@mcp.tool()
def session_history(exercise: str, limit: int = 50) -> dict:
    """Recent sets for one exercise, newest first.

    Args:
        exercise: Canonical lift name.
        limit: Max rows.
    """
    return call_domain(_sessions.get_history, exercise, limit)


@mcp.tool()
def session_get(day: str) -> dict:
    """Full detail for one dated session.

    Args:
        day: Date yyyy-mm-dd.
    """
    return call_domain(_sessions.get_session, day)


@mcp.tool()
def session_range(from_date: str, to_date: str) -> dict:
    """Review-mode bulk pull over a date range. Feeds agent reasoning, never shown raw.

    Args:
        from_date: Start yyyy-mm-dd.
        to_date: End yyyy-mm-dd.
    """
    return call_domain(_sessions.get_session_range, from_date, to_date)


@mcp.tool()
def session_notes(limit: int = 200) -> dict:
    """Recent set/session notes for pain and feel context.

    Args:
        limit: Max rows.
    """
    return call_domain(_sessions.get_notes, limit)


@mcp.tool()
def session_calendar() -> dict:
    """Workout calendar with PR days and rotation verdicts."""
    return call_domain(_sessions.get_calendar)


@mcp.tool()
def session_stats() -> dict:
    """Aggregate training numbers."""
    return call_domain(_sessions.get_stats)


@mcp.tool()
def session_context(limit: int = 3) -> dict:
    """Canonical lift names plus recent context for disambiguation.

    Args:
        limit: Sessions of context.
    """
    return call_domain(_sessions.get_context, limit)


# === muscles ===


@mcp.tool()
def muscle_map_show(exercise: str = "") -> dict:
    """Recorded muscle mapping (authoritative per lift) and setup notes.

    Args:
        exercise: Lift name, or empty for the full map.
    """
    return call_domain(_muscles.get_mapping, exercise or None)


@mcp.tool()
def muscle_map_set(exercise: str, muscles: str, bodyweight: bool = False) -> dict:
    """Record the muscle answer for a movement forever.

    Args:
        exercise: Lift name.
        muscles: Comma list of tracked groups.
        bodyweight: True for bodyweight-only moves.
    """
    return call_domain(_muscles.set_exercise_mapping, exercise, muscles, bodyweight)


@mcp.tool()
def muscle_map_note(exercise: str, text: str) -> dict:
    """Write a permanent per-movement setup fact (setup values live here, never in set notes).

    Args:
        exercise: Lift name.
        text: Setup fact.
    """
    return call_domain(_muscles.set_movement_note, exercise, text)


@mcp.tool()
def muscle_rename(old: str, new: str) -> dict:
    """Merge duplicate lift names, keeping history.

    Args:
        old: Existing name to merge away.
        new: Canonical surviving name.
    """
    return call_domain(_muscles.rename_exercise, old, new)


# === plan ===


@mcp.tool()
def plan(slot: str = "", verbose: bool = False) -> dict:
    """Computed session state bundle: today, slot guess, volume, ledger, lifts,
    split, goals, rules, progression, flags, priority, deload, autoreg. Read
    this first at session start, before MEMORY.md judgment state.

    Args:
        slot: Override the slot guess with an explicit day.
        verbose: Include human-readable highlights alongside the bundle.
    """
    return call_domain(_plan.get_plan, slot or None, verbose)


# === program ===


@mcp.tool()
def program_split_show(day: str = "", variant: Variant = "active") -> dict:
    """Read the program. Active is the exact program planned from; baseline is reference only.

    Args:
        day: Optional single day.
        variant: active or baseline.
    """
    return call_domain(_program.get_split, day or None, variant)


@mcp.tool()
def program_split_set(day: str, slot: int, movements: str, sets: int,
                      variant: Variant = "active") -> dict:
    """Routine active-split update (one-off swaps add the alternate here, never a rewrite).

    Args:
        day: Split day name.
        slot: Slot number.
        movements: Movement expression.
        sets: Working set count.
        variant: active normally, baseline only for explicit major program changes.
    """
    return call_domain(_program.set_split, day, slot, movements, sets, variant)


@mcp.tool()
def program_split_move(day: str, exercise: str, to_slot: int) -> dict:
    """Move an exercise between slots on a day.

    Args:
        day: Split day name.
        exercise: Exercise to move.
        to_slot: Destination slot number.
    """
    return call_domain(_program.move_split, day, exercise, to_slot)


@mcp.tool()
def program_split_reconcile(day: str, after: str = "") -> dict:
    """Append newly logged exercises to a day (the end gate enforces this).

    Args:
        day: Split day name.
        after: Optional exercise to insert after.
    """
    return call_domain(_program.reconcile_split, day, after or None)


@mcp.tool()
def program_split_diff() -> dict:
    """Active versus baseline divergence."""
    return call_domain(_program.diff_split)


@mcp.tool()
def program_split_revert(day: str = "") -> dict:
    """Revert active toward baseline, whole program or one day.

    Args:
        day: Optional single day, or empty for the whole program.
    """
    return call_domain(_program.revert_split, day or None)


@mcp.tool()
def program_priority_set(muscle: str, tier: Tier, until: str = "") -> dict:
    """Bring a muscle up or down: tier breaks ties for slack volume.

    Args:
        muscle: Tracked muscle.
        tier: One of priority, maintain, deprioritize.
        until: Optional expiry date.
    """
    return call_domain(_program.set_priority, muscle, tier, until or None)


@mcp.tool()
def program_priority_clear(muscle: str) -> dict:
    """Clear a muscle priority tier.

    Args:
        muscle: Tracked muscle.
    """
    return call_domain(_program.clear_priority, muscle)


@mcp.tool()
def program_priority_list() -> dict:
    """Current muscle priority tiers."""
    return call_domain(_program.list_priorities)


@mcp.tool()
def program_deload_set(scope: Scope, subject: str) -> dict:
    """Mark a lift or slot as deloaded (volume down per SCIENCE.md, trajectory resumes next session).

    Args:
        scope: One of lift, slot.
        subject: Lift or slot name.
    """
    return call_domain(_program.set_deload, scope, subject)


@mcp.tool()
def program_deload_clear() -> dict:
    """Clear deload state after the deload session ends (appends the dated state line)."""
    return call_domain(_program.clear_deload)


@mcp.tool()
def program_rule_add(text: str, subject: str = "", expires: str = "") -> dict:
    """Write a durable pref or plan down as a rule.

    Args:
        text: Rule text.
        subject: Optional subject the rule governs.
        expires: Optional expiry date.
    """
    return call_domain(_program.add_rule, text, subject or None, expires or None)


@mcp.tool()
def program_rule_list(expiring_within: Optional[int] = None) -> dict:
    """Rules with confirmation state (expired or expiring soon need one answer, then reactivate or archive).

    Args:
        expiring_within: Optional day window for the needs-confirm slice.
    """
    return call_domain(_program.list_rules, expiring_within)


@mcp.tool()
def program_rule_confirm(rule_id: int, extend: str = "", archive: bool = False) -> dict:
    """Reactivate (extend) or archive a rule. Nothing durable is deleted without an answer.

    Args:
        rule_id: Exact rule id.
        extend: New expiry date for reactivation.
        archive: Archive instead of extending.
    """
    return call_domain(_program.confirm_rule, rule_id, extend or None, archive)


@mcp.tool()
def program_flag_add(subject: str, reason: str) -> dict:
    """Flag clear over/underperformance versus ledger headroom.

    Args:
        subject: Exercise or muscle.
        reason: Why it is flagged.
    """
    return call_domain(_program.add_flag, subject, reason)


@mcp.tool()
def program_flag_list() -> dict:
    """Open flags."""
    return call_domain(_program.list_flags)


@mcp.tool()
def program_flag_consume(flag_id: int) -> dict:
    """Consume a flag that outlived its session.

    Args:
        flag_id: Exact flag id.
    """
    return call_domain(_program.consume_flag, flag_id)


@mcp.tool()
def program_meta_show(key: str = "") -> dict:
    """Rotation state and compaction markers.

    Args:
        key: Optional single key.
    """
    return call_domain(_program.get_meta, key or None)


@mcp.tool()
def program_meta_set(key: str, value: str) -> dict:
    """Write a meta key (rotation order, last_compacted). Never hand-count rotation dates.

    Args:
        key: One of rotation, last_compacted, compaction_postponed_until.
        value: New value (rotation takes a JSON day array).
    """
    return call_domain(_program.set_meta, key, value)


@mcp.tool()
def program_rotation_anchor(date: str, day: str) -> dict:
    """Anchor the rotation schedule to a date. Drift asks for a re-anchor, never re-anchors silently.

    Args:
        date: Anchor date yyyy-mm-dd.
        day: Rotation day trained that date.
    """
    return call_domain(_adherence.anchor_rotation, date, day)


@mcp.tool()
def program_rotation_status(from_date: str = "", to_date: str = "") -> dict:
    """Per-date rotation verdicts over a range. Adherence counts come from here, never a hand tally.

    Args:
        from_date: Start yyyy-mm-dd, defaults to the volume window.
        to_date: End yyyy-mm-dd, defaults to today.
    """
    return call_domain(_adherence.get_rotation_status, from_date or None, to_date or None)


# === progression and goals ===


@mcp.tool()
def progression_set(exercise: str, verdict: Verdict, next_target: str, direction: Direction,
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
    return call_domain(_progression.set_progression, exercise, verdict, next_target,
               direction, note, workout_id)


@mcp.tool()
def progression_show(exercise: str = "") -> dict:
    """Progression state, one lift or all.

    Args:
        exercise: Optional lift name.
    """
    return call_domain(_progression.get_progression, exercise or None)


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
    return call_domain(_goals.add_goal, exercise, target_e1rm, deadline, desc, start_e1rm)


@mcp.tool()
def goal_show(goal_id: str = "") -> dict:
    """Goal trajectories and progress.

    Args:
        goal_id: Optional single goal id.
    """
    return call_domain(_goals.get_goal, goal_id or None)


@mcp.tool()
def goal_rewrite(goal_id: int) -> dict:
    """Recut a goal trajectory after a session moved it.

    Args:
        goal_id: Exact goal id.
    """
    return call_domain(_goals.rewrite_goal, goal_id)


@mcp.tool()
def goal_drop(goal_id: int) -> dict:
    """Drop a goal.

    Args:
        goal_id: Exact goal id.
    """
    return call_domain(_goals.drop_goal, goal_id)


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
    return call_domain(_autoreg.apply_autoreg, day, slot, to_movements, to_sets,
               evidence, from_movements or None)


@mcp.tool()
def autoreg_log() -> dict:
    """Autonomous change ledger."""
    return call_domain(_autoreg.list_autoreg_changes)


@mcp.tool()
def autoreg_revert(change_id: int) -> dict:
    """Restore a change's before-state exactly and clear matching holds.

    Args:
        change_id: Exact autoreg change id.
    """
    return call_domain(_autoreg.revert_autoreg_change, change_id)


# === analysis and configuration ===


@mcp.tool()
def audit_data() -> dict:
    """Full data quality check per docs/AUDIT.md."""
    return call_domain(_audit.run_audit)


@mcp.tool()
def doctor() -> dict:
    """Validate constants, DB, dashboard, and dump consistency."""
    return call_domain(_audit.run_doctor)


@mcp.tool()
def constants_show(key: str = "") -> dict:
    """Single source of truth for muscles, MEV/MAV/MRV, thresholds. My logged
    data beats SCIENCE.md defaults for my lifts; these defaults beat instinct.

    Args:
        key: Optional dotted key (e.g. muscles.chest, thresholds).
    """
    return call_domain(_constants.get_constants, key or None)


@mcp.tool()
def constants_validate() -> dict:
    """Validate constants.json structurally."""
    return call_domain(_constants.check_constants)


@mcp.tool()
def constants_set(key: str, value: str) -> dict:
    """Edit one constants key (never by hand).

    Args:
        key: Dotted key to set.
        value: JSON-encoded new value (a JSON string holds a plain string).
    """
    return call_domain(_constants.set_constant, key, value)


# === snapshot and sync ===


@mcp.tool()
def snapshot_export() -> dict:
    """Full validated dashboard payload (history plus program and forward state).
    For the dashboard file only, never pulled in bulk into chat.
    """
    return call_domain(_sync.export_snapshot)


@mcp.tool()
def sync_push(force: bool = False) -> dict:
    """Push the validated snapshot to the hosted dashboard and dump workouts.sql
    for git history. Pull-first with ETags: a stale base aborts with 412 unless forced.

    Args:
        force: Overwrite deliberately after reconciling a 412.
    """
    return call_domain(_sync.push_snapshot, force)


@mcp.tool()
def maintenance_dump() -> dict:
    """Re-write workouts.sql from the live DB without syncing (recovery and drift fixes)."""
    return call_domain(_sync.dump_sql)


@mcp.tool()
def maintenance_restore(force: bool = False) -> dict:
    """Rebuild the live DB from workouts.sql into a temp file first, replacing
    only after verification. Refuses with an open workout unless forced.

    Args:
        force: Restore despite an open workout.
    """
    return call_domain(_sync.restore_sql, force)
