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
from .db import CFG, DB, SCHEMA, conn, open_workout, placeholders
from .errors import RepsError
from .goals import (add_goal, build_checkpoints, drop_goal, get_goal,
                    goal_progress, goal_sessions, rewrite_goal)
from .memory import MEMORY_FILE, append_memory_state
from .mcp.server import call_tool as mcp_call_tool
from .mcp.server import list_tool_names as mcp_list_tool_names
from .mcp.server import mcp as mcp_server
from .models import (ConstantsModel, SnapshotAdherence,
                     SnapshotAutoreg, SnapshotModel, SnapshotValidationError,
                     first_error, validate_snapshot)
from .muscles import (attach_muscles, best_e1rm, e1rm_of, get_mapping,
                      rename_exercise, set_exercise_mapping,
                      set_movement_note)
from .plan import get_plan
from .program import (active_deloads, add_flag, add_rule, best_split_day,
                      clear_deload, clear_priority, confirm_rule,
                      consume_flag, consume_session_flags, day_movements,
                      deload_covers, diff_split, get_meta, get_split,
                      list_flags, list_priorities, list_rules,
                      mev_floor_warnings, move_split, muscles_for_movements,
                      parse_movements, parse_rotation, programmed_weekly_volume,
                      read_priorities, read_split, reconcile_split,
                      revert_split, rule_status_rows, rules_with_confirm,
                      set_deload, set_meta, set_priority, set_split,
                      split_all_movements, split_day_order, volume_block)
from .progression import (get_progression, set_progression,
                          top_e1rm_by_date)
from .sessions import (check_end_gate, delete_set, delete_workout,
                       end_gate_items, end_workout, get_calendar, get_context,
                       get_history, get_notes, get_session, get_session_range,
                       get_stats, get_today, list_exercises, log_set, mark_rest,
                       record_bodyweight, start_workout, update_set,
                       update_workout)
from .signals import SEVERITY_ORDER, build_signals
from .sync import (build_snapshot, build_snapshot_validated, dump_sql,
                   export_snapshot, push_snapshot, restore_sql)

__all__ = [
    "CFG", "CONSTANTS_FILE", "ConstantsModel", "DB", "MEMORY_FILE",
    "RepsError", "SCHEMA", "SEVERITY_ORDER", "SnapshotAdherence",
    "SnapshotAutoreg", "SnapshotModel",
    "SnapshotValidationError", "active_deloads", "add_flag", "add_goal",
    "add_rule", "adherence_block", "adherence_snapshot", "anchor_rotation",
    "append_memory_state", "apply_autoreg", "attach_muscles",
    "autoreg_active_holds", "autoreg_block", "autoreg_drop_watch",
    "autoreg_grouped", "autoreg_miss_streaks", "autoreg_permitted",
    "best_e1rm", "best_split_day", "build_checkpoints", "build_signals",
    "build_snapshot", "build_snapshot_validated", "canon_muscle_name",
    "check_constants", "check_end_gate", "classify_date", "clean_muscles",
    "clear_deload", "clear_priority", "confirm_rule", "consume_flag",
    "consume_session_flags", "day_movements", "delete_set", "delete_workout",
    "deload_covers", "diff_split", "drift_days", "drop_goal", "dump_sql",
    "end_gate_items", "end_workout", "expected_day", "expectation_context",
    "export_snapshot", "first_error", "get_anchor", "get_calendar",
    "get_constants", "get_context", "get_goal", "get_history", "get_mapping",
    "get_meta", "get_notes", "get_plan", "get_progression",
    "get_rotation_status", "get_session", "get_session_range", "get_split",
    "get_stats", "get_today", "goal_progress", "goal_sessions",
    "is_rest_day", "list_autoreg_changes", "list_exercises", "list_flags",
    "list_priorities", "list_rules", "load_constants", "log_set",
    "mark_rest", "match_day", "mcp_call_tool", "mcp_list_tool_names",
    "mcp_server", "mev_floor_warnings", "move_split", "muscles_for_movements",
    "open_workout", "parse_anchor", "parse_mev_from_science",
    "parse_movements", "parse_rotation", "placeholders",
    "programmed_weekly_volume", "push_snapshot", "read_priorities",
    "read_split", "reconcile_split", "record_bodyweight", "rename_exercise",
    "rep_band_bound", "restore_sql", "revert_autoreg_change", "revert_split",
    "rewrite_goal", "rule_status_rows", "rules_with_confirm", "run_audit",
    "run_doctor", "set_constant", "set_deload", "set_exercise_mapping",
    "set_meta", "set_movement_note", "set_priority", "set_progression",
    "set_split", "split_all_movements", "split_day_order", "start_workout",
    "status_range", "top_e1rm_by_date", "tracked_muscles", "update_set",
    "update_workout", "validate_constants", "validate_snapshot",
    "volume_block",
]
