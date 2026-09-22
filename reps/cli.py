import re
import sys
from datetime import date

from .audit import cmd_audit, cmd_doctor
from .autoreg import cmd_autoreg_apply, cmd_autoreg_log, cmd_autoreg_revert
from .constants import (_join_muscles, canon_muscle_name, cmd_constants_set,
                        cmd_constants_show, cmd_constants_validate, load_constants)
from .db import conn
from .goals import (cmd_goal_add, cmd_goal_drop, cmd_goal_rewrite,
                    cmd_goal_show)
from .muscles import cmd_map_note, cmd_map_show, cmd_rename, cmd_retag
from .plan import cmd_plan
from .progression import cmd_progression_set, cmd_progression_show
from .program import (cmd_deload_clear, cmd_deload_set, cmd_flag_add,
                      cmd_flag_consume, cmd_flag_list, cmd_meta_set,
                      cmd_meta_show, cmd_priority_clear, cmd_priority_list,
                      cmd_priority_set, cmd_rule_add, cmd_rule_confirm,
                      cmd_rule_list, cmd_split_diff, cmd_split_move,
                      cmd_split_reconcile, cmd_split_revert, cmd_split_set,
                      cmd_split_show, split_day_prefix)
from .sessions import (cmd_calendar, cmd_check, cmd_context, cmd_delete_set,
                       cmd_delete_workout, cmd_end, cmd_exercises, cmd_history,
                       cmd_log, cmd_notes, cmd_range, cmd_rest, cmd_session,
                       cmd_start, cmd_stats, cmd_today, cmd_update,
                       cmd_update_workout, cmd_weigh)
from .sync import cmd_dump, cmd_export, cmd_restore, cmd_sync


def resolve_known_prefix(toks, known, max_words, what):
    """Split tokens into (known name, rest) via longest known-prefix match.

    Exits instead of guessing when nothing matches.
    """
    match = next((i for i in range(min(len(toks) - 1, max_words), 0, -1)
                  if " ".join(toks[:i]).lower() in known), None)
    if match is None:
        sys.exit(f"could not identify the {what}; quote a known name (see map show)")
    return " ".join(toks[:match]), " ".join(toks[match:])


def usage():
    sys.exit(
        "usage: log.py start [note] | log <exercise> <weight> <reps> [note] [muscles=a,b] [bw] "
        "| update <id> <field> <value> | update-workout <id> <field> <value> | retag <exercise> <muscles> [bw] "
        "| delete-set <id> | delete-workout <id> | end [note] | today | exercises | history <ex> [limit] "
         "| session <yyyy-mm-dd> | range <from> <to> | notes [limit] | calendar "
         "| stats | export | rename <old> <new> | context [n] | weigh <kg> [note] | sync [force] | restore [force] | audit | rest [yyyy-mm-dd] [note]"
         " | constants show [key] | constants validate | constants set <key> <json-value>"
         " | plan [--slot <day>] [--verbose] | check [note]"
         " | progression set <exercise> --verdict <hit|miss|hold|baseline> --next <target> --direction <up|flat|down> [--note <t>] [--workout <id>]"
         " | progression show [exercise] | flag add <subject> <reason> | flag list | flag consume <id>"
         " | priority set <muscle> <tier> [--until <date>] | priority clear <muscle> | priority list"
         " | deload set --scope <lift|slot> <name> | deload clear"
         " | split show [day] [--variant active|baseline] | split set <day> <slot#> <movements> <sets> [--variant baseline]"
         " | split move <day> <exercise> --to <slot#> | split reconcile --day <day> [--after <exercise>]"
         " | split diff | split revert [day]"
         " | map show [exercise] | map set <exercise> <muscles> [bw] | map note <exercise> <text>"
         " | rule add <text> --subject <x> [--expires <date>] | rule list [--expiring-within <n>]"
         " | rule confirm <id> --extend <date> | --archive"
         " | goal add <exercise> --target <e1rm> --deadline <date> [--desc <t>] [--from <e1rm>]"
         " | goal show [id] | goal rewrite <id> | goal drop <id>"
         " | autoreg apply --day <day> --slot <n> --to <movements> <sets> --evidence <text> [--from <movements>]"
         " | autoreg log | autoreg revert <id>"
    )


def main():
    if len(sys.argv) < 2:
        usage()
    cmd = sys.argv[1]
    rest = sys.argv[2:]
    if cmd == "start":
        cmd_start(" ".join(rest))
    elif cmd == "log" and len(rest) >= 3:
        # Exercise is everything up to the first two numeric tokens (weight, reps).
        nums = [i for i, t in enumerate(rest) if re.fullmatch(r"\d+(\.\d+)?", t)]
        if len(nums) < 2:
            sys.exit("usage: log <exercise> <weight> <reps> [note] [muscles=a,b] [bw] (quoting never needed)")
        exercise, weight, reps = " ".join(rest[:nums[0]]), rest[nums[0]], rest[nums[1]]
        if not exercise:
            sys.exit("usage: log <exercise> <weight> <reps> [note] [muscles=a,b] [bw] (quoting never needed)")
        note_parts = []
        muscles = ""
        bodyweight = False
        for tok in rest[nums[1] + 1:]:
            if tok.startswith("muscles="):
                muscles = tok[len("muscles="):]
                continue
            if tok == "bw":
                bodyweight = True
                continue
            note_parts.append(tok)
        cmd_log(exercise, weight, reps, " ".join(note_parts), muscles, bodyweight)
    elif cmd == "update" and len(rest) >= 3:
        cmd_update(rest[0], rest[1], " ".join(rest[2:]))
    elif cmd == "end":
        force = None
        toks = list(rest)
        if "--force" in toks:
            i = toks.index("--force")
            force = " ".join(toks[i + 1:]).strip() or None
            toks = toks[:i]
            if not force:
                sys.exit("end --force needs a reason, it is written into the workout note")
        cmd_end(" ".join(toks), force)
    elif cmd == "today":
        cmd_today()
    elif cmd == "exercises":
        cmd_exercises()
    elif cmd == "history" and len(rest) >= 1:
        lim = rest[1] if len(rest) > 1 else "50"
        cmd_history(rest[0], lim)
    elif cmd == "stats":
        cmd_stats()
    elif cmd == "export":
        cmd_export()
    elif cmd == "rename" and len(rest) >= 2:
        cmd_rename(rest[0], " ".join(rest[1:]))
    elif cmd == "retag" and len(rest) >= 2:
        bodyweight = "bw" in rest
        rest = [r for r in rest if r != "bw"]
        if len(rest) >= 2:
            cmd_retag(rest[0], ",".join(rest[1:]), bodyweight)
    elif cmd == "delete-set" and len(rest) >= 1:
        cmd_delete_set(rest[0])
    elif cmd == "delete-workout" and len(rest) >= 1:
        cmd_delete_workout(rest[0])
    elif cmd == "update-workout" and len(rest) >= 3:
        cmd_update_workout(rest[0], rest[1], " ".join(rest[2:]))
    elif cmd == "session" and len(rest) >= 1:
        cmd_session(rest[0])
    elif cmd == "range" and len(rest) >= 2:
        cmd_range(rest[0], rest[1])
    elif cmd == "notes":
        cmd_notes(rest[0] if len(rest) > 0 else "200")
    elif cmd == "calendar":
        cmd_calendar()
    elif cmd == "context":
        lim = rest[0] if len(rest) > 0 else "3"
        cmd_context(lim)
    elif cmd == "weigh" and len(rest) >= 1:
        cmd_weigh(rest[0], " ".join(rest[1:]))
    elif cmd == "sync":
        cmd_sync("force" in rest)
    elif cmd == "restore":
        cmd_restore("force" in rest)
    elif cmd == "audit":
        cmd_audit()
    elif cmd == "constants" and rest[:1] == ["show"]:
        cmd_constants_show(rest[1] if len(rest) > 1 else None)
    elif cmd == "constants" and rest[:1] == ["validate"]:
        cmd_constants_validate()
    elif cmd == "constants" and rest[:1] == ["set"] and len(rest) >= 3:
        cmd_constants_set(rest[1], " ".join(rest[2:]))
    elif cmd == "check":
        cmd_check(" ".join(rest))
    elif cmd == "doctor":
        cmd_doctor()
    elif cmd == "dump":
        cmd_dump()
    elif cmd == "meta" and rest[:1] == ["show"]:
        cmd_meta_show(rest[1] if len(rest) > 1 else None)
    elif cmd == "meta" and rest[:1] == ["set"] and len(rest) >= 3:
        cmd_meta_set(rest[1], " ".join(rest[2:]))
    elif cmd == "progression" and rest[:1] == ["set"] and len(rest) >= 2:
        toks = rest[1:]
        first_flag = next((i for i, t in enumerate(toks) if t.startswith("--")), len(toks))
        exercise = " ".join(toks[:first_flag])
        verdict = next_target = direction = note = workout_id = None
        toks = toks[first_flag:]
        i = 0
        while i < len(toks):
            if toks[i] == "--verdict" and i + 1 < len(toks):
                verdict = toks[i + 1]
                i += 2
            elif toks[i] == "--next" and i + 1 < len(toks):
                next_target = toks[i + 1]
                i += 2
            elif toks[i] == "--direction" and i + 1 < len(toks):
                direction = toks[i + 1]
                i += 2
            elif toks[i] == "--note" and i + 1 < len(toks):
                note = toks[i + 1]
                i += 2
            elif toks[i] == "--workout" and i + 1 < len(toks):
                workout_id = toks[i + 1]
                i += 2
            else:
                i += 1
        cmd_progression_set(exercise, verdict, next_target, direction, note or "", workout_id)
    elif cmd == "progression" and rest[:1] == ["show"]:
        cmd_progression_show(" ".join(rest[1:]) or None)
    elif cmd == "flag" and rest[:1] == ["add"] and len(rest) >= 3:
        # Subject is an exercise or muscle: longest known match wins, so both
        # sides can go unquoted; unknown subjects fall back to first token.
        toks = rest[1:]
        known_subjects = ({r["exercise"] for r in conn().execute("SELECT exercise FROM lift_muscle_map").fetchall()}
                          | set(load_constants()["muscles"]))
        subject, reason = resolve_known_prefix(toks, known_subjects, 4, "subject (exercise or muscle)")
        cmd_flag_add(subject, reason)
    elif cmd == "flag" and rest[:1] == ["list"]:
        cmd_flag_list()
    elif cmd == "flag" and rest[:1] == ["consume"] and len(rest) >= 2:
        cmd_flag_consume(rest[1])
    elif cmd == "priority" and rest[:1] == ["set"] and len(rest) >= 3:
        toks = rest[1:]
        until = None
        if "--until" in toks:
            j = toks.index("--until")
            until = " ".join(toks[j + 1:]) if j + 1 < len(toks) else None
            toks = toks[:j]
        if len(toks) < 2:
            sys.exit("usage: log.py priority set <muscle> <tier> [--until <date>] (quoting never needed)")
        cmd_priority_set(" ".join(toks[:-1]), toks[-1], until)
    elif cmd == "priority" and rest[:1] == ["clear"] and len(rest) >= 2:
        cmd_priority_clear(" ".join(rest[1:]))
    elif cmd == "priority" and rest[:1] == ["list"]:
        cmd_priority_list()
    elif cmd == "deload" and rest[:1] == ["set"]:
        scope = subject = None
        toks = rest[1:]
        if "--scope" in toks:
            j = toks.index("--scope")
            scope = toks[j + 1] if j + 1 < len(toks) else None
            toks = toks[:j] + toks[j + 2:]
        subject = " ".join(toks) or None
        cmd_deload_set(scope, subject)
    elif cmd == "deload" and rest[:1] == ["clear"]:
        cmd_deload_clear()
    elif cmd == "split" and rest[:1] == ["show"]:
        toks = rest[1:]
        variant = "active"
        if "--variant" in toks:
            j = toks.index("--variant")
            variant = toks[j + 1] if j + 1 < len(toks) else "active"
            toks = toks[:j] + toks[j + 2:]
        cmd_split_show(" ".join(toks) or None, variant)
    elif cmd == "split" and rest[:1] == ["set"] and len(rest) >= 5:
        toks = rest[1:]
        variant = "active"
        if "--variant" in toks:
            j = toks.index("--variant")
            variant = toks[j + 1] if j + 1 < len(toks) else "active"
            toks = toks[:j] + toks[j + 2:]
        # Day is everything up to the first integer (the slot); sets is last.
        slot_at = next((i for i, t in enumerate(toks) if re.fullmatch(r"\d+", t)), None)
        if slot_at is None or slot_at < 1 or slot_at >= len(toks):
            sys.exit("usage: log.py split set <day> <slot#> <movements> <sets> (quote the day if this fails)")
        cmd_split_set(" ".join(toks[:slot_at]), toks[slot_at], " ".join(toks[slot_at + 1:-1]), toks[-1], variant)
    elif cmd == "split" and rest[:1] == ["move"] and len(rest) >= 4:
        toks = rest[1:]
        to_slot = None
        if "--to" in toks:
            j = toks.index("--to")
            to_slot = toks[j + 1] if j + 1 < len(toks) else None
            toks = toks[:j] + toks[j + 2:]
        day, exercise = split_day_prefix(toks)
        if not day or not exercise or to_slot is None:
            sys.exit("usage: log.py split move <day> <exercise> --to <slot#> (quote multi-word names if this fails)")
        cmd_split_move(day, exercise, to_slot)
    elif cmd == "split" and rest[:1] == ["reconcile"]:
        toks = rest[1:]
        day = after = None
        if "--day" in toks:
            j = toks.index("--day")
            k = next((i for i in range(j + 1, len(toks)) if toks[i].startswith("--")), len(toks))
            day, _ = split_day_prefix(toks[j + 1:k])
            toks = toks[:j] + toks[k:]
        if "--after" in toks:
            j = toks.index("--after")
            after = " ".join(toks[j + 1:]) if j + 1 < len(toks) else None
        if not day:
            sys.exit("usage: log.py split reconcile --day <day> [--after <exercise>]")
        cmd_split_reconcile(day, after)
    elif cmd == "split" and rest[:1] == ["diff"]:
        cmd_split_diff()
    elif cmd == "split" and rest[:1] == ["revert"]:
        cmd_split_revert(" ".join(rest[1:]) or None)
    elif cmd == "map" and rest[:1] == ["show"]:
        cmd_map_show(" ".join(rest[1:]) or None)
    elif cmd == "map" and rest[:1] == ["set"] and len(rest) >= 3:
        bodyweight = "bw" in rest or "--bw" in rest
        toks = [t for t in rest[1:] if t not in ("bw", "--bw")]
        # Muscles are matched word-by-word from the right against the known
        # vocabulary (commas ignored); everything before is the exercise name.
        vocab = set(load_constants()["muscles"]) | set(load_constants().get("untracked", []))
        words = " ".join(toks).replace(",", " ").split()
        takes = 0
        while takes < len(words):
            rest = len(words) - takes
            two = " ".join(words[rest - 2:rest]).lower() if rest >= 2 else None
            one = words[rest - 1].lower()
            if two is not None and canon_muscle_name(two, vocab) is not None:
                takes += 2
            elif canon_muscle_name(one, vocab) is not None:
                takes += 1
            else:
                break
        if takes == 0 or takes >= len(words):
            sys.exit("usage: log.py map set <exercise> <muscles> [bw] (quoting never needed)")
        cmd_retag(" ".join(words[:len(words) - takes]),
                  ",".join(_join_muscles(words[len(words) - takes:], vocab)), bodyweight)
    elif cmd == "map" and rest[:1] == ["note"] and len(rest) >= 3:
        toks = rest[1:]
        known = {r["exercise"] for r in conn().execute("SELECT exercise FROM lift_muscle_map").fetchall()}
        exercise, note = resolve_known_prefix(toks, known, 5, "exercise")
        cmd_map_note(exercise, note)
    elif cmd == "rule" and rest[:1] == ["add"] and len(rest) >= 2:
        toks = rest[1:]
        subject = expires = None
        if "--subject" in toks:
            j = toks.index("--subject")
            k = next((i for i in range(j + 1, len(toks)) if toks[i].startswith("--")), len(toks))
            subject = " ".join(toks[j + 1:k]) or None
            toks = toks[:j] + toks[k:]
        if "--expires" in toks:
            j = toks.index("--expires")
            expires = toks[j + 1] if j + 1 < len(toks) else None
            toks = toks[:j] + toks[j + 2:]
        cmd_rule_add(" ".join(toks), subject, expires)
    elif cmd == "rule" and rest[:1] == ["list"]:
        window = None
        if "--expiring-within" in rest:
            j = rest.index("--expiring-within")
            window = rest[j + 1] if j + 1 < len(rest) else None
        cmd_rule_list(window)
    elif cmd == "goal" and rest[:1] == ["add"] and len(rest) >= 2:
        exercise = rest[1]
        toks = rest[2:]
        target = deadline = desc = start = None
        i = 0
        while i < len(toks):
            if toks[i] == "--target" and i + 1 < len(toks):
                target = toks[i + 1]
                i += 2
            elif toks[i] == "--deadline" and i + 1 < len(toks):
                deadline = toks[i + 1]
                i += 2
            elif toks[i] == "--desc":
                desc = " ".join(toks[i + 1:]) if i + 1 < len(toks) else ""
                break
            elif toks[i] == "--from" and i + 1 < len(toks):
                start = toks[i + 1]
                i += 2
            else:
                i += 1
        cmd_goal_add(exercise, target, deadline, desc or "", start)
    elif cmd == "goal" and rest[:1] == ["show"]:
        cmd_goal_show(" ".join(rest[1:]) or None)
    elif cmd == "goal" and rest[:1] == ["rewrite"] and len(rest) >= 2:
        cmd_goal_rewrite(rest[1])
    elif cmd == "goal" and rest[:1] == ["drop"] and len(rest) >= 2:
        cmd_goal_drop(rest[1])
    elif cmd == "autoreg" and rest[:1] == ["log"]:
        cmd_autoreg_log()
    elif cmd == "autoreg" and rest[:1] == ["revert"] and len(rest) >= 2:
        cmd_autoreg_revert(rest[1])
    elif cmd == "autoreg" and rest[:1] == ["apply"]:
        # Flags delimit multi-word values, so day/movements/evidence go unquoted.
        vals: dict = {}
        current = None
        for tok in rest[1:]:
            if tok in ("--day", "--slot", "--to", "--evidence", "--from"):
                current = tok
                vals[current] = []
            elif current is None:
                sys.exit("usage: log.py autoreg apply --day <day> --slot <n> --to <movements> <sets> "
                         "--evidence <text> [--from <movements>]")
            else:
                vals[current].append(tok)
        day = " ".join(vals.get("--day", [])) or None
        slot = " ".join(vals.get("--slot", [])) or None
        to_toks = vals.get("--to", [])
        evidence = " ".join(vals.get("--evidence", [])) or None
        from_toks = vals.get("--from")
        if not day or not slot or len(to_toks) < 2 or not evidence:
            sys.exit("usage: log.py autoreg apply --day <day> --slot <n> --to <movements> <sets> "
                     "--evidence <text> [--from <movements>]")
        cmd_autoreg_apply(day, slot, " ".join(to_toks[:-1]), to_toks[-1], evidence,
                          " ".join(from_toks) if from_toks is not None else None)
    elif cmd == "rule" and rest[:1] == ["confirm"] and len(rest) >= 2:
        extend = archive = None
        archive = "--archive" in rest
        if "--extend" in rest:
            j = rest.index("--extend")
            extend = rest[j + 1] if j + 1 < len(rest) else None
        cmd_rule_confirm(rest[1], extend, archive)
    elif cmd == "plan":
        slot = None
        verbose = "--verbose" in rest
        toks = [t for t in rest if t != "--verbose"]
        if "--slot" in toks:
            i = toks.index("--slot")
            slot = " ".join(toks[i + 1:]) if i + 1 < len(toks) else None
        cmd_plan(slot, verbose)
    elif cmd == "rest":
        day = date.today().isoformat()
        words = rest
        if words:
            try:
                day = date.fromisoformat(words[0]).isoformat()
                words = words[1:]
            except ValueError:
                pass
        cmd_rest(day, " ".join(words))
    else:
        usage()
