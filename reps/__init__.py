"""reps: workout log. Code owns what is derivable or enforceable, the agent owns what is judgment.

Package surface. Import from here; `log.py` at the repo root re-exports
everything so the CLI and existing tooling keep working.
"""

from .adherence import (adherence_block, adherence_snapshot, classify_date, cmd_rotation_anchor,
                        cmd_rotation_status, drift_days, expected_day,
                        expectation_context, get_anchor, is_rest_day,
                        match_day, parse_anchor, status_range)
from .audit import cmd_audit, cmd_doctor
from .autoreg import (autoreg_active_holds, autoreg_block, autoreg_drop_watch,
                      autoreg_grouped, autoreg_miss_streaks, autoreg_permitted,
                      cmd_autoreg_apply, cmd_autoreg_log, cmd_autoreg_revert)
from .cli import main
from .constants import (CONSTANTS_FILE, canon_muscle_name, clean_muscles,
                        cmd_constants_set, cmd_constants_show,
                        cmd_constants_validate, load_constants,
                        load_constants_model, parse_mev_from_science, rep_band_bound,
                        tracked_muscles, validate_constants)
from .db import CFG, DB, SCHEMA, conn, open_workout, placeholders
from .goals import (build_checkpoints, cmd_goal_add, cmd_goal_drop,
                    cmd_goal_rewrite, cmd_goal_show, goal_progress,
                    goal_sessions)
from .memory import MEMORY_FILE, append_memory_state
from .models import (ConstantsModel, SnapshotModel, SnapshotValidationError,
                     first_error, validate_snapshot)
from .muscles import (attach_muscles, best_e1rm, cmd_map_note, cmd_map_show,
                      cmd_rename, cmd_retag, e1rm_of)
from .plan import cmd_plan
from .program import (active_deloads, best_split_day, cmd_deload_clear,
                      cmd_deload_set, cmd_flag_add, cmd_flag_consume,
                      cmd_flag_list, cmd_meta_set, cmd_meta_show,
                      cmd_priority_clear, cmd_priority_list, cmd_priority_set,
                      cmd_rule_add, cmd_rule_confirm, cmd_rule_list,
                      cmd_split_diff, cmd_split_move, cmd_split_reconcile,
                      cmd_split_revert, cmd_split_set, cmd_split_show,
                      consume_session_flags, day_movements,
                      deload_covers, mev_floor_warnings, muscles_for_movements,
                      parse_movements, parse_rotation, programmed_weekly_volume,
                      read_priorities, read_split, rule_status_rows,
                      rules_with_confirm, split_all_movements, split_day_order,
                      volume_block)
from .progression import (cmd_progression_set, cmd_progression_show,
                          top_e1rm_by_date)
from .sessions import (cmd_calendar, cmd_check, cmd_context, cmd_delete_set,
                       cmd_delete_workout, cmd_end, cmd_exercises, cmd_history,
                       cmd_log, cmd_notes, cmd_range, cmd_rest, cmd_session,
                       cmd_start, cmd_stats, cmd_today, cmd_update,
                       cmd_update_workout, cmd_weigh, end_gate_items)
from .signals import SEVERITY_ORDER, build_signals
from .sync import (build_snapshot, build_snapshot_validated, cmd_dump, cmd_export, cmd_restore, cmd_sync)

__all__ = [
    "CFG", "CONSTANTS_FILE", "ConstantsModel", "DB", "MEMORY_FILE", "SCHEMA", "SEVERITY_ORDER",
    "SnapshotModel", "SnapshotValidationError", "active_deloads", "adherence_block", "adherence_snapshot", "append_memory_state", "attach_muscles",
    "autoreg_active_holds", "autoreg_block", "autoreg_drop_watch",
    "autoreg_grouped", "autoreg_miss_streaks", "autoreg_permitted",
    "best_e1rm", "best_split_day", "build_checkpoints", "build_signals", "build_snapshot", "build_snapshot_validated",
    "canon_muscle_name", "classify_date", "clean_muscles", "cmd_audit", "cmd_autoreg_apply",
    "cmd_autoreg_log", "cmd_autoreg_revert", "cmd_calendar", "cmd_check",
    "cmd_constants_set", "cmd_constants_show", "cmd_constants_validate",
    "cmd_context", "cmd_delete_set", "cmd_delete_workout", "cmd_deload_clear",
    "cmd_deload_set", "cmd_doctor", "cmd_dump", "cmd_end", "cmd_exercises",
    "cmd_export", "cmd_flag_add", "cmd_flag_consume", "cmd_flag_list",
    "cmd_goal_add", "cmd_goal_drop", "cmd_goal_rewrite", "cmd_goal_show",
    "cmd_history", "cmd_log", "cmd_map_note", "cmd_map_show", "cmd_meta_set",
    "cmd_meta_show", "cmd_notes", "cmd_plan", "cmd_priority_clear",
    "cmd_priority_list", "cmd_priority_set", "cmd_progression_set",
    "cmd_progression_show", "cmd_range", "cmd_rename", "cmd_rest",
    "cmd_restore", "cmd_retag", "cmd_rotation_anchor", "cmd_rotation_status",
    "cmd_rule_add", "cmd_rule_confirm",
    "cmd_rule_list", "cmd_session", "cmd_split_diff", "cmd_split_move",
    "cmd_split_reconcile", "cmd_split_revert", "cmd_split_set",
    "cmd_split_show", "cmd_start", "cmd_stats", "cmd_sync", "cmd_today",
    "cmd_update", "cmd_update_workout", "cmd_weigh", "conn",
    "consume_session_flags", "day_movements", "deload_covers", "drift_days",
    "e1rm_of",
    "end_gate_items", "expected_day",     "expectation_context", "first_error", "get_anchor",
    "goal_progress", "goal_sessions",     "is_rest_day", "load_constants", "load_constants_model",
    "main", "match_day", "mev_floor_warnings", "muscles_for_movements", "open_workout",
    "parse_anchor", "parse_mev_from_science", "parse_movements", "parse_rotation",
    "placeholders", "programmed_weekly_volume", "read_priorities",
    "read_split", "rep_band_bound", "rule_status_rows", "rules_with_confirm",
    "split_all_movements", "split_day_order", "status_range",
    "top_e1rm_by_date", "tracked_muscles", "validate_constants", "validate_snapshot", "volume_block",
]
