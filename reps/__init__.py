"""reps: workout log. Code owns what is derivable or enforceable, the agent owns what is judgment.

Package surface. Import from here; `log.py` at the repo root re-exports
everything so the CLI and existing tooling keep working.
"""

from .adherence import (adherence_block, adherence_snapshot, classify_date, rotation_anchor,
                        rotation_status, drift_days, expected_day,
                        expectation_context, get_anchor, is_rest_day,
                        match_day, parse_anchor, status_range)
from .audit import audit, doctor
from .autoreg import (autoreg_active_holds, autoreg_block, autoreg_drop_watch,
                      autoreg_grouped, autoreg_miss_streaks, autoreg_permitted,
                      autoreg_apply, autoreg_log, autoreg_revert)
from .constants import (CONSTANTS_FILE, canon_muscle_name, clean_muscles,
                        constants_set, constants_show,
                        constants_validate, load_constants,
                        load_constants_model, parse_mev_from_science, rep_band_bound,
                        tracked_muscles, validate_constants)
from .db import CFG, DB, SCHEMA, conn, open_workout, placeholders
from .goals import (build_checkpoints, goal_add, goal_drop,
                    goal_rewrite, goal_show, goal_progress,
                    goal_sessions)
from .memory import MEMORY_FILE, append_memory_state
from .mcp.server import call_tool as mcp_call_tool
from .mcp.server import list_tool_names as mcp_list_tool_names
from .mcp.server import mcp as mcp_server
from .models import (ConstantsModel, SnapshotModel, SnapshotValidationError,
                     first_error, validate_snapshot)
from .muscles import (attach_muscles, best_e1rm, map_note, map_show,
                      rename, retag, e1rm_of)
from .plan import plan
from .program import (active_deloads, best_split_day, deload_clear,
                      deload_set, flag_add, flag_consume,
                      flag_list, meta_set, meta_show,
                      priority_clear, priority_list, priority_set,
                      rule_add, rule_confirm, rule_list,
                      split_diff, split_move, split_reconcile,
                      split_revert, split_set, split_show,
                      consume_session_flags, day_movements,
                      deload_covers, mev_floor_warnings, muscles_for_movements,
                      parse_movements, parse_rotation, programmed_weekly_volume,
                      read_priorities, read_split, rule_status_rows,
                      rules_with_confirm, split_all_movements, split_day_order,
                      volume_block)
from .progression import (progression_set, progression_show,
                          top_e1rm_by_date)
from .sessions import (calendar, check, context, delete_set,
                       delete_workout, end, exercises, history,
                       log, notes, range, rest, session,
                       start, stats, today, update,
                       update_workout, weigh, end_gate_items)
from .signals import SEVERITY_ORDER, build_signals
from .sync import (build_snapshot, build_snapshot_validated, dump, export, restore, sync)

__all__ = [
    "CFG", "CONSTANTS_FILE", "ConstantsModel", "DB", "MEMORY_FILE", "SCHEMA", "SEVERITY_ORDER",
    "SnapshotModel", "SnapshotValidationError", "active_deloads", "adherence_block", "adherence_snapshot", "append_memory_state", "attach_muscles",
    "autoreg_active_holds", "autoreg_block", "autoreg_drop_watch",
    "autoreg_grouped", "autoreg_miss_streaks", "autoreg_permitted",
    "best_e1rm", "best_split_day", "build_checkpoints", "build_signals", "build_snapshot", "build_snapshot_validated",
    "canon_muscle_name", "classify_date", "clean_muscles", "audit", "autoreg_apply",
    "autoreg_log", "autoreg_revert", "calendar", "check",
    "constants_set", "constants_show", "constants_validate",
    "context", "delete_set", "delete_workout", "deload_clear",
    "deload_set", "doctor", "dump", "end", "exercises",
    "export", "flag_add", "flag_consume", "flag_list",
    "goal_add", "goal_drop", "goal_rewrite", "goal_show",
    "history", "log", "map_note", "map_show", "meta_set",
    "meta_show", "notes", "plan", "priority_clear",
    "priority_list", "priority_set", "progression_set",
    "progression_show", "range", "rename", "rest",
    "restore", "retag", "rotation_anchor", "rotation_status",
    "rule_add", "rule_confirm",
    "rule_list", "session", "split_diff", "split_move",
    "split_reconcile", "split_revert", "split_set",
    "split_show", "start", "stats", "sync", "today",
    "update", "update_workout", "weigh", "conn",
    "consume_session_flags", "day_movements", "deload_covers", "drift_days",
    "e1rm_of",
    "end_gate_items", "expected_day",     "expectation_context", "first_error", "get_anchor",
    "goal_progress", "goal_sessions",     "is_rest_day", "load_constants", "load_constants_model",
    "match_day", "mcp_call_tool", "mcp_list_tool_names", "mcp_server", "mev_floor_warnings", "muscles_for_movements", "open_workout",
    "parse_anchor", "parse_mev_from_science", "parse_movements", "parse_rotation",
    "placeholders", "programmed_weekly_volume", "read_priorities",
    "read_split", "rep_band_bound", "rule_status_rows", "rules_with_confirm",
    "split_all_movements", "split_day_order", "status_range",
    "top_e1rm_by_date", "tracked_muscles", "validate_constants", "validate_snapshot", "volume_block",
]
