"""reps: workout log. Code owns what is derivable or enforceable, the agent owns what is judgment.

Package surface. Domain operations live in one module per domain; agents
reach them through typed MCP tools in reps.mcp, tests import them from here.
Domain functions return structured values and raise RepsError on refusal;
only log.py (maintenance) and MCP translate those at process/protocol edges.
"""

from .adherence import (adherence_block, adherence_snapshot, anchor_rotation,
                        classify_date, drift_days, expected_day,
                        expectation_context, get_anchor, get_rotation_status,
                        is_rest_day, match_day, parse_anchor, status_range)
from .audit import run_audit, run_doctor
from .autoreg import (apply_autoreg, autoreg_active_holds, autoreg_block,
                      autoreg_drop_watch, autoreg_grouped, autoreg_miss_streaks,
                      autoreg_permitted, list_autoreg_changes,
                      revert_autoreg_change)
from .constants import (CONSTANTS_FILE, canon_muscle_name, check_constants,
                        clean_muscles, get_constants, load_constants,
                        parse_mev_from_science, rep_band_bound, set_constant,
                        tracked_muscles, validate_constants)
from .db import CFG, DB, SCHEMA, SCHEMA_VERSION, conn, open_workout, placeholders
from .errors import Fix, GateItem, GateReport, Refusal, RepsError
from .goals import (add_goal, build_checkpoints, drop_goal, get_goal,
                    goal_progress, goal_sessions, rewrite_goal)
from .history import (get_change, list_changes, record_change, revert_change,
                      state_at)
from .observations import observe
from .memory import MEMORY_FILE, append_memory_state
from .mcp.server import call_tool as mcp_call_tool
from .mcp.server import list_tool_names as mcp_list_tool_names
from .mcp.server import mcp as mcp_server
from .models import (Adherence, Autoreg, BodyweightPoint, CalendarDay,
                     ConstantsModel, Deload, Flag, Goal, Lift, Muscle,
                     NextUp, Priority, ProgramView, RecentNote, Rule,
                     SessionView, Signal, SnapshotModel,
                     SnapshotValidationError, VolumeHistory, first_error,
                     validate_snapshot)
from .e1rm import e1rm
from .muscles import (attach_muscles, best_e1rm, get_mapping,
                      merge_exercises, rename_exercise, set_exercise_mapping,
                      set_movement_note)
from .plan import get_plan
from .program import (active_deloads, add_flag, add_rule, best_split_day,
                      clear_deload, clear_priority, confirm_rule,
                      consume_flag, consume_session_flags, day_movements,
                      deload_covers, diff_split, ensure_lift, get_compaction,
                      get_rotation, get_split,
                      lift_muscles, lift_muscles_csv, list_flags, list_priorities,
                      list_rules, mev_floor_warnings, merge_lifts, move_split,
                      muscles_for_movements, parse_movements, parse_rotation,
                      programmed_weekly_volume, read_priorities, read_split,
                      reconcile_split, rename_lift, revert_split,
                      rule_status_rows, rules_with_confirm, set_compaction,
                      set_deload, set_lift_muscles, set_priority, set_rotation,
                      set_split, show_rotation, slot_rows, split_all_movements,
                      split_day_order, volume_block)
from .progression import (format_target, get_progression, latest as latest_progression,
                          set_progression, top_e1rm_by_date)
from .records import last_pr_date, personal_records
from .sessions import (check_end_gate, delete_set, delete_workout,
                       end_gate_items, end_workout, get_calendar, get_context,
                       get_history, get_notes, get_session, get_session_range,
                       get_stats, get_today, last_done, list_exercises, log_set,
                       mark_rest, record_bodyweight, session_prs, staleness,
                       start_workout, update_set, update_workout)
from .slots import next_slot, slot_of_session
from .trends import drop_watch, is_slipping, is_stalling
from .vocab import (AdherenceStatus, AutoregAction, CalendarKind, DeloadScope,
                    Direction, EvidenceTier, GoalStatus, HistoryDomain, MarkKind,
                    ObserveMetric, PriorityTier, RuleStatus, SplitVariant,
                    Verdict, VolumeStatus, WorkoutStatus)
from .weeks import monday_of, week_start_of, week_starts, weekly_counts
from .signals import SEVERITY_ORDER, build_signals
from .sessions import break_threshold
from .snapshot import build_views
from .sync import (build_snapshot, build_snapshot_validated, dump_sql,
                   export_snapshot, push_snapshot, restore_sql)

__all__ = [
    "CFG", "CONSTANTS_FILE", "ConstantsModel", "DB", "MEMORY_FILE",
    "Fix", "GateItem", "GateReport", "Refusal", "RepsError", "SCHEMA", "SCHEMA_VERSION",
    "SEVERITY_ORDER", "Adherence",
    "Autoreg", "BodyweightPoint", "CalendarDay", "SnapshotModel",
    "SnapshotValidationError", "Deload", "Flag", "Goal", "Lift", "Muscle",
    "NextUp", "Priority", "ProgramView", "RecentNote", "Rule",
    "SessionView", "Signal", "VolumeHistory", "active_deloads", "add_flag", "add_goal",
    "add_rule", "adherence_block", "adherence_snapshot", "anchor_rotation",
    "append_memory_state", "apply_autoreg", "attach_muscles",
    "autoreg_active_holds", "autoreg_block", "autoreg_drop_watch",
    "autoreg_grouped", "autoreg_miss_streaks", "autoreg_permitted",
    "best_e1rm", "best_split_day", "build_checkpoints", "build_signals",
    "build_snapshot", "build_snapshot_validated", "build_views", "break_threshold", "canon_muscle_name",
    "check_constants", "check_end_gate", "classify_date", "clean_muscles",
    "clear_deload", "clear_priority", "confirm_rule", "consume_flag",
    "consume_session_flags", "day_movements", "delete_set", "delete_workout",
    "deload_covers", "diff_split", "drift_days", "drop_goal", "drop_watch",
    "dump_sql", "e1rm",
    "end_gate_items", "end_workout", "ensure_lift", "expected_day",
    "expectation_context", "export_snapshot", "first_error", "format_target",
    "get_anchor", "get_calendar", "get_change", "get_compaction",
    "get_constants", "get_context", "get_goal", "get_history", "get_mapping",
    "get_notes", "get_plan", "get_progression", "get_rotation",
    "get_rotation_status", "get_session", "get_session_range", "get_split",
    "get_stats", "get_today", "goal_progress", "goal_sessions",
    "is_rest_day", "is_slipping", "is_stalling", "last_done", "last_pr_date",
    "latest_progression", "lift_muscles", "lift_muscles_csv", "list_autoreg_changes",
    "list_changes", "list_exercises", "list_flags",
    "list_priorities", "list_rules", "load_constants", "log_set",
    "mark_rest", "match_day", "mcp_call_tool", "mcp_list_tool_names",
    "mcp_server", "merge_exercises", "merge_lifts", "mev_floor_warnings", "monday_of",
    "move_split", "muscles_for_movements",     "next_slot",
    "observe", "open_workout", "parse_anchor", "parse_mev_from_science",
    "parse_movements", "parse_rotation", "personal_records",
    "placeholders", "programmed_weekly_volume", "push_snapshot",
    "read_priorities", "read_split", "reconcile_split", "record_bodyweight",
    "record_change", "rename_exercise", "rename_lift", "rep_band_bound", "restore_sql",
    "revert_autoreg_change", "revert_change", "revert_split", "rewrite_goal", "rule_status_rows",
    "rules_with_confirm", "run_audit", "run_doctor", "session_prs",
    "set_compaction", "set_constant", "set_deload", "set_exercise_mapping",
    "set_lift_muscles", "set_movement_note", "set_priority", "set_progression",
    "set_rotation", "set_split", "show_rotation", "slot_of_session", "slot_rows",
    "split_all_movements", "split_day_order", "staleness", "start_workout",
    "state_at", "status_range", "top_e1rm_by_date", "tracked_muscles", "update_set",
    "update_workout", "validate_constants", "validate_snapshot",
    "volume_block", "week_start_of", "week_starts", "weekly_counts",
    "AdherenceStatus", "AutoregAction", "CalendarKind", "DeloadScope", "Direction",
    "EvidenceTier", "GoalStatus", "HistoryDomain", "MarkKind", "ObserveMetric",
    "PriorityTier", "RuleStatus", "SplitVariant",
    "Verdict", "VolumeStatus", "WorkoutStatus",
]
