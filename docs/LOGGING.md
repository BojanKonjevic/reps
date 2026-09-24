# Logging

Session protocol for the logging agent. This plus `AGENTS.md` is everything needed to run a session. Program design lives in `PROGRAMMING.md`, dashboard work in `DASHBOARD.md`.

All operations are MCP tools (`reps/mcp/`). Tool results carry `ok` plus `data` or `output`; a refusal (`ok: false`) names the reason, never guess past it.

## Session start

Fresh agents have no chat memory, so rebuild it from files first:

1. Run `plan`. Its bundle is the computed session state: today, slot_guess, volume, ledger, lifts, split, goals, rules, progression, flags, priority, deload, autoreg, compaction. Then read `MEMORY.md` and `SCIENCE.md` for judgment state only. Active rules beat SCIENCE.md defaults which beat raw history. My logged data beats SCIENCE.md defaults for my specific lifts.
2. Check dates: read `plan`'s `rules.needs_confirm` (derived: expired or expiring within 7 days, rules and priority tiers alike). If anything expired since last session or expires within 7 days, ask once before logging anything it affects. Resolve rules with `program_rule_confirm`, priority tiers with `program_priority_set` / `program_priority_clear`, never delete silently.
3. Stale workout check: read `plan`'s `today.stale`. Soft signals: user trains a different muscle group than the open session, or says something like "just got to the gym" after yesterday's sets with no `done`. Any hard signal, or two soft ones, means ask "new workout?" before writing anything. Answering yes means explicitly closing the old one first so it gets its `session_end` note, never auto closing silently.
4. Compaction check: read `plan`'s `compaction.due`. If due, run compaction now (see Memory writeback). Skippable on request with "do it later", and then it must not nag again that day.
5. Working memory is small and fixed: the `plan` bundle plus the judgment state in `MEMORY.md`. No bulk historical-sets pull at session start: `session_get`, `session_range`, and `session_notes` stay review-mode tools, never pulled in bulk at session start. The only exception is a targeted slot-history peek per step 6 (workout-level only via `session_calendar`/`session_notes`, never a sets pull). Never load the full `snapshot_export` into chat, it is for the dashboard file only.
6. Slot resolution: every session start settles what today is. User states it, or the agent states its assumption ("assuming Upper B, last trained Upper A then Lower A") and moves on; the assumption counts as confirmed unless explicitly rejected. `plan`'s `slot_guess` is the default assumption (override with `plan` and an explicit slot when the user states it). If the first logged movement contradicts the assumption, that movement wins, the slot is corrected on the spot.
7. Coach pass: run the autoregulation pass from `PROGRAMMING.md` now, before prescribing anything. It may rewrite the active split (trims, adds, swaps); everything below reads the updated split.
8. Plan: once the slot is settled, present the full session plan upfront, lift by lift, before anything is logged. Every session is planned. If `session_today` shows a rest row for today, confirm the user is training before planning anything. Read the live volume check from `plan`'s `volume`: any muscle under its MEV not covered by an Active rule or a `deprioritize` tier gets folded into the plan when it fits an existing slot (extra set or alternate pick, never a program change), otherwise surfaced as a one-line note. Priority tier breaks ties for slack volume inside MAV/MRV headroom; Goal trajectory numbers always win over this nudge. Nudges never rewrite the split, directly or indirectly. Full prescription precedence, highest first: Active rules / injuries / pain notes; Deload state (affected lifts only, volume down per SCIENCE.md deload guidance, trajectory resumes next session); Goal trajectory numbers; Priority tier allocation; live MEV nudge; ledger bump/hold. For each movement in the day's slot (alternates included): read progression, ledger, and flags from `plan`'s `split` slots; take active goal trajectories covering the exact movement as the strong prior. Prescribe exercise, weight, reps, sets, stating e1RM both ways; schemes default to 3-8 reps, true 1-3 singles only as explicit tests in the final 1-2 sessions before a goal deadline. For slot alternates, lean toward the better recent trend or the less recently trained, unless the user picks. Cold start (no Progression state): no target, no PR flag, ask for a conservative first set to failure and seed from the result. Guardrails: jumps proportional to history, never a leap; no PR attempts on the first session back from a break (per `plan`'s `today.break`), program maintenance instead, said explicitly; injuries, pain notes, and Active rules always win. Mark PR attempts clearly. The user confirms or edits before training; nothing is logged until actually performed. If the slot is corrected later, refresh the plan for the corrected day.

Core principle: a wrong log poisons every future analysis, a question costs nothing. When unsure about exercise, weight, reps, or which rule applies, ask first or verify with a query. Never guess into the db.

## How to log

1. Workouts are only created explicitly. `session_log_set` fails when no workout is open, it never auto creates. On any training message, run `session_today` to see if a workout is open, then `session_start` when sure a new session began.
2. Talk stays conversational, no rigid syntax. The agent infers batch logging from plain talk: "squat 90 5/5/7, last to failure" or three rapid "same x5" messages means fan out to multiple `session_log_set` calls in one burst. Mid workout replies stay terse ("logged 3x"), full summary at `session_end`.
3. Before logging a set, check the `session_context` lifts list for canonical names. Reuse an existing name when it clearly matches.
4. Log with `session_log_set` (exercise, weight, reps, free note text, plus `muscles` on first use of a movement, see Muscle attribution). The mapping is authoritative thereafter: differing muscles are refused, log genuine variations under their own name.
5. RPE is not tracked. Never ask for it, never log it. Feel goes in plain words in the note instead. Failure is the silent default, never logged as a note; note only stopping short of failure or something off.
6. Warmups are not tracked. Never log them, they pollute maxes and PRs.
7. Weights are always kg unless the user says otherwise. On lbs input convert (divide by 2.205) and state the conversion in the reply. Bodyweight goes with `session_weigh` plus optional note. No scale at home, so entries come from the gym scale: not fasted, less consistent, not every day. One entry per day is enough, latest wins on the chart.
8. Weighted bodyweight work logs extra only: dips at bodyweight plus 20kg is `session_log_set` dips 20 for reps. True bodyweight only moves log zero with the bodyweight flag: pullup 0 for reps with muscles back,biceps and bodyweight true.
9. Corrections and removals are explicit. Ordinal to id mapping ("second squat was 92.5") is agent reasoning over `session_today`, but the destructive call itself needs an exact id: `session_update_set`, `session_delete_set`, `session_delete_workout`, `session_update_workout` (fields: notes, date, status). Never infer an id for a delete, confirm it in chat first.
10. Rest days are tracked explicitly, never inferred from absence: `session_rest` with an explicit date marks a day as rest (backfill allowed, future refused). Rest rows carry no sets, never count as sessions, and render distinctly on the calendar. Training on a marked rest day is allowed, the day then shows as trained.
11. On `done`, `finished`, or clear end of session, first write per-lift progression (`progression_set` for every trained lift with verdict, next target as weight x reps, direction; reps are required, bare weights are refused, e.g. `82.5x5` not `82.5`), optionally run `session_check` to preview the close gate, then run `session_end` with a short session summary (feel, sleep, pain, what moved well). `session_end` refuses to close while anything is outstanding and reports the exact fix per item; `session_end` with a force reason skips writeback items (progression, reconcile, deload note) with the reason recorded in the workout note, but never skips missing muscles. Then run `sync_push` to push the dashboard, then commit `workouts.sql` and push the repo (`data: <today's date>` as message). The sql dump is tracked in git, that commit is the backup and the undo button. This repo is fully agent written, committing and pushing here needs no permission.
12. Unilateral sets are capped by the first hand when lower; always log weaker side reps with L/R in the note when sides diverge. This applies without being asked when the movement name says unilateral, the user reports per-side reps, or the movement's notes say unilateral.
13. Setup values live in movement notes (`muscle_map_show`), never in set or session notes. Surface them proactively exactly once, in the next-exercise reminder mid-session. When the user states a new setup value, write it with `muscle_map_note`, confirm briefly, and keep it out of the `session_log_set` note. Ask if unsure.
14. Mid-session adaptation: only each lift's first work set is compared against its plan target (later sets fade with fatigue). Compare in e1RM against the `constants_show` rep_bands thresholds: over target, propose bumping the remaining sets once, tersely and in both forms; at clear underperformance, back off instead, never pushing through pain or form breakdown; anything between stays silent. Above 15 reps, e1RM is logged but never triggers a proposal. One adjustment per lift per session, remaining sets only.
15. `session_log_set` and `session_update_set` sometimes return `warnings` (stale open workout, near-duplicate name, implausible jump): stop and verify with the user before continuing, never log past a warning blindly. Warnings are not blocks; a confirmed true value proceeds.

Units are kg unless user says otherwise. Never invent sets. If a message is ambiguous, hold the log and ask. Partial logging is allowed only when the clear part is unambiguous, the unclear part waits for an answer. Tool arguments take plain multi-word names as ordinary strings, no quoting layer exists.

## Naming

You own the ontology. There is no alias list in code.

1. Normalize to lowercase training names, for example `flat barbell bench press`, `back squat`, `overhead press`.
2. Known shorthands: `ohp` means overhead press, `bench` means flat barbell bench press unless MEMORY.md or context says otherwise, `squat` means back squat unless context says front or split.
3. `same` or `again` refers to the last exercise in the open workout.
4. If user names something new that has no close match, ask once, then reuse that spelling forever.
5. If duplicates happen, merge with `muscle_rename`.

## Muscle attribution

One movement trains as many groups as it trains. Each set carries its own muscle list, so compounds give full credit to every group they hit.

Default to asking. Only skip the question when the movement is extremely clearly one muscle and nothing else. Anything with a plausible second muscle gets one question, then the answer is recorded forever:

1. Check `muscle_map_show` first. A recorded mapping wins, no re-asking. But a mapping covers exactly the lift named, never its variants. When tempted to extend, still ask.
2. If unmapped and not extremely clear, ask which groups it trains, log with `muscles` set.
3. Record the answer with `muscle_map_set`. If the movement also needs a setup note, add it with `muscle_map_note`.

Form and intent matter: dips done upright are chest, done leaning forward with elbows tucked are triceps. When form changes the muscles, ask, don't assume from the name alone.

Volume is anatomical by muscle group, and one set can count for several groups at once. Tracked groups live in `constants.json` (`constants_show` on muscles; never neck, calves, traps). Per lift attribution lives in the mapping table (`muscle_map_show`). If a new movement maps to an untracked group or no clear group, ask once whether to track it, then follow the answer.

## Split

The splits table holds two variants. Baseline is the reference program and is never planned from. Active is the exact program: which day holds which exercises in which order, with working set counts. Read with `program_split_show`. Program changes themselves (rewrites, not routine updates) are designed in `PROGRAMMING.md`; this section covers the mechanics.

1. At every session `session_end`, the gate enforces reconciliation: newly logged exercises must be appended via `program_split_reconcile`.
2. A one-off swap logs under the existing active slot and adds the alternate via `program_split_set`. It never rewrites the program.
3. The active split takes routine updates (`program_split_set`, `program_split_move`, `program_split_reconcile`). The baseline is rewritten only on explicit instruction for a major program change, via `program_split_set` with the baseline variant. Never infer either from one unusual session.
4. Session planning reads the active split first (`plan` includes the guessed day's slots): it defines what a full day contains.

## Session report

Every session that ends explicitly ("done", "finished") or implicitly (clearly over, user moving on) gets a short report in chat. Sessions closed only because a new day found them stale get no report, their data is suspect.

Short and conversational, but every claim grounded in numbers just pulled: PRs hit, top sets versus the last same slot session, plan targets hit or missed, anything notable from notes (pain, bad sleep). One take at most, no essays, no generic motivation.

Plus, when they trigger, each in one line:

- Trajectory rewrite: if a goal trajectory changed this session, state what changed (old versus new numbers for the upcoming sessions), why (which logged result caused it), and which neighboring sessions shifted. Silence when the plan survived intact.
- Deload watch: per `constants` deload_watch_pct, two consecutive same-slot drops flag that one more like this triggers a reactive deload per SCIENCE.md. Rare by design. When the flag condition is met again with no recovery in between, run `program_deload_set` instead of only narrating it in chat.
- Stall note: if a main lift has no PR in 3 same slot sessions, say so.

## Memory writeback

Chat history dies with the session, files survive. When user states something durable, write it down:

1. Prefs and plans go to the rules table via `program_rule_add`. Permanent per-movement facts go to the mapping (`muscle_map_set`, `muscle_map_note`). Goal statements go through the flow in `PROGRAMMING.md`. Expired rules surface in `program_rule_list` under `needs_confirm` and get asked about once, then reactivated or archived. Nothing durable is ever deleted without an answer.
2. Session feel and life context go to workout notes via `session_end`. End notes stay lean, one line, only what numbers cannot explain. DB holds weights. Pain/sleep silent when fine. Set level notes go on the set.
3. At month end on request, append a short rollup to `MEMORY.md` under Monthly rollups: trend plus caveats in a few lines. Raw sets stay in SQLite, never paste them into memory files.
4. Compaction runs once a month. When the Session start check triggers it: archive expired rules older than 60 days, fold superseded State lines into one current line each, write last month's rollup. Rollups are never deleted. Run `program_meta_set` on last_compacted with `<Mon D YYYY>` when done. If the user says later, skip silently until next session.
5. Every compaction publishes last month's rollup as a postplan doc (PRs, stalls, adherence with miss versus rest verdicts, next block suggestion) using the postplan workflow, links it in chat, and stores the link with the rollup in MEMORY.md. Adherence counts come straight from `program_rotation_status` over the month, never from a hand tally.
6. At every session `session_end`, update the plan state for the session just trained: Progression state for every trained lift via `progression_set`, and new Flagged entries via `program_flag_add` for clear over/underperformance versus ledger headroom (flags touching the session are consumed by `session_end` itself, or `program_flag_consume` for anything left over). The Muscle load ledger is derived by `plan` and needs no writeback. Mid-session reasoning stays ephemeral, never in session or set notes.
7. Deload sessions: the `session_end` note for a session trained under Deload state must include the word `deload` (the gate enforces this). After `session_end` completes, run `program_deload_clear` (it appends the dated State line itself).

Keep `MEMORY.md` short. Current state only, dated lines, no essays.
