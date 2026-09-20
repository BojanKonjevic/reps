# reps

Chat first workout log. The agent owns meaning, `log.py` only stores.

## Session start

Fresh agents have no chat memory, so rebuild it from files first:

1. Run `plan` first. Its JSON bundle is the computed session state: `today` (open workout, rest row, staleness, last session, gap, break flag), `slot_guess`, `volume` (rolling 8-week weekly sets per muscle with MEV/MAV/MRV status), `ledger` (7-day sets/sessions/last-hit per muscle, derived, never stored), `lifts` (per-lift last/best aggregates), `compaction`. Then read `MEMORY.md`, `MOVEMENTS.md`, `GOALS.md`, and `SCIENCE.md` for judgment state only. Active rules in MEMORY.md beat SCIENCE.md defaults which beat raw history. SCIENCE.md provides evidence-based bounds for goal realism, session prescriptions, split suggestions, and any judgment call. My logged data in MEMORY.md beats SCIENCE.md defaults for my specific lifts. Check all four before asking anything about units, mappings, or program.
2. Check dates: compare today against every rule expiry plus the Needs confirm section. If a rule expired since last session or expires within 7 days, ask once before logging anything it affects (example: incline block ended Nov 1 and user still logs incline, ask to extend or close). Move expired rules to Needs confirm, never delete silently.
3. Stale workout check: read `plan`'s `today.stale` (`is_stale` already combines the hard signals: open date is not today, or `age_days >= 1`, or gap since `last_set_created` over 8h). Soft signals: user trains a different muscle group than the open session, or says something like "just got to the gym" after yesterday's sets with no `done`. Any hard signal, or two soft ones, means ask "new workout?" before writing anything. Answering yes means explicitly closing the old one first so it gets its `end` note, never auto closing silently.
4. Compaction check: read `plan`'s `compaction.due`. If due, run compaction now (see Memory writeback). Skippable on request with "do it later", and then it must not nag again that day. Note: compaction postponed until Oct 1 2026 (project started Sep 16 2026, nothing to compact before then). Remove this note when compaction first runs.
5. Working memory is small and fixed: the `plan` bundle (today, slot guess, volume, ledger, lifts, progression, flags, priority, deload, compaction) plus the judgment state across `MEMORY.md`, `MOVEMENTS.md`, and `GOALS.md` (Active split, Goals, Active rules). No bulk historical-sets pull at session start: `session`, `range`, and `notes` stay review-mode tools for analytical questions (at home, analysis, postplan docs), never pulled in bulk at session start. The only exception is a targeted slot-history peek per step 6 (workout-level only via `calendar`/`notes`, never a sets pull). Never load full `export` into chat, it is for the dashboard file only.
6. Slot resolution: every session start settles what today is. User states it, or the agent states its assumption ("assuming Upper B, last trained Upper A then Lower A") and moves on; the assumption counts as confirmed unless explicitly rejected. `plan`'s `slot_guess` is the default assumption (override with `plan --slot <day>` when the user states it). If a slot-history lookup is needed for the assumption, it is workout-level only (`calendar` dates, `notes` if needed), never a sets pull. If the first logged movement contradicts the assumption, that movement wins, the slot is corrected on the spot.
7. Plan: once the slot is settled, present the full session plan upfront, lift by lift, before anything is logged. Every session is planned. If `today` shows a rest row for today, confirm the user is training before planning anything. Before prescribing, read the live volume check straight from `plan`'s `volume` (rolling 8-week weekly sets per muscle with MEV/MAV/MRV status from `constants.json`, same computation AUDIT.md check 8 uses, no manual `range` pull). Any muscle under its MEV that is not already covered by an Active rule or a Priority tier of `deprioritize` (see Prioritize) gets folded into the plan when the muscle appears in today's slots or has an available interchangeable/accessory slot (an extra set or alternate pick inside the existing slot, same category as the ledger bump, never a program change); otherwise surface it as a one-line note in the plan message so it stays visible even on days it cannot be addressed. When several muscles compete for the same slack volume inside MAV/MRV headroom, Priority tier breaks the tie (see Prioritize); Goal trajectory numbers always win over this nudge. This check never rewrites the Active split, directly or indirectly: per-session nudges inside existing slots only, program changes go through Split rule 3 or Split review. Also before prescribing, check Deload state in MEMORY.md. If set and the day's slot includes an affected lift, that lift gets SCIENCE.md's deload guidance (volume down 40-60%, intensity held) instead of the normal bump/hold/goal-trajectory logic. Deload state takes precedence over the live volume nudge above and over Priority tier allocation for the affected lift specifically; nothing else in the session is affected. The goal trajectory itself is unchanged, it resumes next session (sessions shift, never silently compressed, same rule as Slippage). Injuries, pain notes, and Active rules still win over everything, including the deload prescription. Full prescription precedence for any lift, highest first: Active rules / injuries / pain notes; Deload state (affected lifts only); Goal trajectory numbers; Priority tier allocation; live MEV nudge; ledger bump/hold. For each movement in the day's Active split slot (alternates included): read its Progression state (last target, verdict, direction); check `plan`'s `ledger` for every muscle it trains (recent sets, days since last hit, bump or hold); read Flagged entries touching it, then delete them; take active goal trajectories covering the exact movement (never its alternatives) as the strong prior, never a blind override (but see the precedence list above: Deload state supersedes goal numbers for an affected lift for that session only). A goal number that risks near-term volume elsewhere is skipped or scaled back only if that makes the goal more likely, otherwise the trajectory holds. Prescribe exercise, weight, reps, sets, stating e1RM both ways (`Target: e1RM 107.9, prescribed as 92.5kg x 5`); schemes default to 3-8 reps, true 1-3 singles only as explicit tests in the final 1-2 sessions before a goal deadline. For slot alternates, lean toward the better recent trend or the less recently trained, unless the user picks. Cold start (no Progression state): no target, no PR flag, ask for a conservative first set to failure and seed from the result. Guardrails: jumps proportional to history, never a leap; no PR attempts on the first session back from a break (4+ days since the last done session per `calendar`, rest rows included in the gap), program maintenance instead, said explicitly; injuries, pain notes, and Active rules always win. Mark PR attempts clearly. The user confirms or edits before training; nothing is logged until actually performed. If the slot is corrected later, refresh the plan for the corrected day.

Core principle: a wrong log poisons every future analysis, a question costs nothing. When unsure about exercise, weight, reps, or which rule applies, ask first or verify with a query. Never guess into the db.

## How to log

1. Workouts are only created explicitly. `log` fails when no workout is open, it never auto creates. On any training message, run `today` to see if a workout is open, then `start` when sure a new session began.
2. Talk stays conversational, no rigid syntax. The agent infers batch logging from plain talk: "squat 90 5/5/7, last to failure" or three rapid "same x5" messages means fan out to multiple `log` calls in one burst. Mid workout replies stay terse ("logged 3x"), full summary at `end`.
3. Before logging a set, check the `context` lifts list for canonical names. Reuse an existing name when it clearly matches.
4. Log with: `log <exercise> <weight> <reps>` plus free note text, plus `muscles=a,b` naming every muscle group the movement trains (see Muscle attribution).
5. RPE is not tracked. Never ask for it, never log it. Feel goes in plain words in the note instead. Failure is the silent default, never logged as a note; note only stopping short of failure or something off.
6. Warmups are not tracked. Never log them, they pollute maxes and PRs.
7. Weights are always kg unless the user says otherwise. On lbs input convert (divide by 2.205) and state the conversion in the reply. Bodyweight goes with `weigh <kg>` plus optional note, for example `weigh 84.2 gym scale`. No scale at home, so entries come from the gym scale: not fasted, less consistent, not every day. One entry per day is enough, latest wins on the chart.
8. Weighted bodyweight work logs extra only: dips at bodyweight plus 20kg is `log dips 20 <reps>`. True bodyweight only moves (pullup with no added weight) log zero with the `bw` flag: `log pullup 0 <reps> muscles=back,biceps bw`.
9. Corrections and removals are explicit. Ordinal to id mapping ("second squat was 92.5") is agent reasoning over `today`, but the destructive call itself needs an exact id: `update <id> <field> <value>`, `delete-set <id>`, `delete-workout <id>`, `update-workout <id> <field> <value>` (fields: notes, date, status). Never infer an id for a delete, confirm it in chat first.
10. Rest days are tracked explicitly, never inferred from absence: `rest [yyyy-mm-dd] [note]` marks a day as rest with an optional note (date defaults to today, backfill allowed, future refused). Rest rows carry no sets, never count as sessions, and render distinctly on the calendar. Training on a marked rest day is allowed, the day then shows as trained.
11. On `done`, `finished`, or clear end of session, first write per-lift progression (`progression set <exercise> --verdict <hit|miss|hold|baseline> --next <target> --direction <up|flat|down>` for every trained lift), optionally run `check` to preview the close gate, then run `end` with a short session summary (feel, sleep, pain, what moved well). `end` refuses to close while anything is outstanding (missing muscles, missing progression, missing deload note) and prints the exact fix per item; `end --force "<reason>"` closes anyway with the reason recorded in the workout note. That note is how future sessions remember the qualitative side. Then run `sync` to push the dashboard, then commit `workouts.sql` and push the repo (`data: <today's date>` as message). The sql dump is tracked in git, that commit is the backup and the undo button. This repo is fully agent written, committing and pushing here needs no permission.
12. Unilateral sets are capped by the first hand when lower; always log weaker side reps with L/R in the note when sides diverge. This applies without being asked when the movement name says unilateral, the user reports per-side reps, or the movement's notes say unilateral.
13. Setup values live in MOVEMENTS.md, never in set or session notes. Height (cable height or seat height), grip, stack, and attachment details surface proactively exactly once: in the next-exercise reminder mid-session. Otherwise mention them only when the user asks about setup directly. When the user states a new setup value, write it to the movement's notes in MOVEMENTS.md, confirm briefly, and keep it out of the `log` note. Ask if unsure.
14. Mid-session adaptation: only each lift's first work set is compared against its plan target (later sets fade with fatigue, comparing them misreads tiredness as signal). Compare in e1RM: at 4%+ over target (1-6 reps), 5%+ (7-10), 8%+ (11-15), propose bumping the remaining sets once, tersely and in both forms (`e1RM 111 vs 107.9 target, want 95 for the rest?`); at clear underperformance, back off instead, never pushing through pain or form breakdown; anything between stays silent on the plan. Above 15 reps, e1RM is logged but never triggers a proposal. One adjustment per lift per session, remaining sets only, never rewriting other lifts' prescriptions.
15. `log` and `update` sometimes return `warnings` (stale open workout, near-duplicate name, implausible jump, drifted muscles): stop and verify with the user before continuing, never log past a warning blindly. Warnings are not blocks; a confirmed true value proceeds.

Units are kg unless user says otherwise. Never invent sets. If a message is ambiguous, hold the log and ask. Partial logging is allowed only when the clear part is unambiguous, the unclear part waits for an answer.

## Naming

You own the ontology. There is no alias list in code.

1. Normalize to lowercase training names, for example `flat barbell bench press`, `back squat`, `overhead press`.
2. Known shorthands: `ohp` means overhead press, `bench` means flat barbell bench press unless MEMORY.md or context says otherwise (for example an active incline block), `squat` means back squat unless context says front or split.
3. `same` or `again` refers to the last exercise in the open workout.
4. If user names something new that has no close match, ask once, then reuse that spelling forever.
5. If duplicates happen, merge with `rename <old> <new>`.

## Muscle attribution

One movement trains as many groups as it trains. Back squat is quads plus glutes, never quads alone. Each set carries its own muscle list, so compounds give full credit to every group they hit.

Default to asking. Only skip the question when the movement is extremely clearly one muscle and nothing else (curls are biceps, pushdowns are triceps; even straight bar pulldown plausibly involves biceps, so it gets asked). Anything with a plausible second muscle gets one question, then the answer is recorded forever:

1. Check `MOVEMENTS.md` Lift mapping first. A recorded mapping wins, no re-asking. But a mapping covers exactly the lift named, never its variants: the flat bench mapping does not cover incline smith underhand, even when a convention looks extendable. When tempted to extend, still ask.
2. If unmapped and not extremely clear, ask which groups it trains, log with `muscles=a,b`.
3. Append the answer to the Lift mapping list in MOVEMENTS.md as `- <movement> -> <muscles>` (for example `- rope hammer curl -> biceps, forearms`). If the movement also needs a setup or logging note, add a subsection under Movement notes (only movements with notes get one). If the user corrects an old mapping, fix past sets with `retag <exercise> <muscles>` too.

Form and intent matter: dips done upright are chest, done leaning forward with elbows tucked are triceps. When form changes the muscles, ask, don't assume from the name alone.

## Split

MOVEMENTS.md holds two splits. Baseline split is the reference program and is never planned from. Active split is the exact program: which day holds which exercises in which order, with working set counts. One slot per line as movement x sets, interchangeable moves on one line separated by /.

1. At every session `end`, reconcile against the active split: append newly logged exercises to that day's slots in performed order. Early sessions build the section, later ones just confirm it.
2. A one-off swap ("pec deck instead of flies today") logs under the existing active slot and adds the alternate. It never rewrites the split.
3. The active split takes routine updates (reconciliation, user-directed tweaks). The baseline split is rewritten only on explicit instruction for a major program change. Never infer either from one unusual session.
4. Session planning reads the active split first: it defines what a full day contains.

## Session report

Every session that ends explicitly ("done", "finished") or implicitly (clearly over, user moving on) gets a short report in chat. No postplan, just a message. Sessions closed only because a new day found them stale get no report, their data is suspect.

Short and conversational, but every claim grounded in numbers just pulled: PRs hit, top sets versus the last same slot session, plan targets hit or missed, anything notable from notes (pain, bad sleep). One take at most, no essays, no generic motivation.

Plus, when they trigger, each in one line:

- Trajectory rewrite: if a goal trajectory changed this session, state what changed (old versus new numbers for the upcoming sessions), why (which logged result caused it), and which neighboring sessions shifted. Silence when the plan survived intact.
- Deload watch: if a lift drops ~5%+ e1RM for two consecutive same slot sessions, flag that one more like this triggers a reactive deload per SCIENCE.md. Rare by design. When the flag condition is met again for the same lift/slot with no recovery in between (i.e. a prior Deload watch mention was already given last session and the drop persists), run `deload set --scope <lift|slot> <name>` instead of only narrating it in chat.
- Stall note: if a main lift has no PR in 3 same slot sessions, say so.

## Goals (goal)

"goal", alone or in context, manages lifting goals. Stating one ("bench 100 for 3 in 2 months"), checking one ("how is my bench goal"), adjusting or dropping one. Multiple goals stay active at once, each wakes only on relevant sessions.

1. Realism gate first. Compare the target against current bests and the timeframe. Absurd goals get flagged in chat instantly and written nowhere. Sane goals get written to GOALS.md.
2. On entry, convert the stated target to e1RM (a stated single counts as its own weight, never run through the formula) and reflect back what that implies across a few rep ranges for a sanity check before anything is written. Trajectories target e1RM, not fixed rep schemes; prescriptions default to 3-8 reps, with true 1-3 rep tests reserved for the final 1-2 sessions before the deadline and flagged as tests. Trajectories assume the same equipment throughout. Goals fit compounds and stable free-weight movements best; a goal on a noisier or higher-rep lift is allowed, with looser on-track tolerance said upfront.
3. Accepted goals get a trajectory: numbered e1RM checkpoints from today forward, inching up every session or every other one. Sessions are numbered (session 1, session 2), not dated, so skipped days change nothing. The deadline lives on its own line.
4. Evolution: on every relevant log, re-read GOALS.md, compare reality to plan, rewrite the remaining trajectory off new data, informed by whether the plan deliberately deferred or accelerated an attempt that session. Exact match means leave it alone.
5. Slippage: when the remaining sessions no longer fit before the deadline at the current pace, ask whether to extend the deadline or compress the jumps. Never silently compress.
6. Split changes (baseline or active) remap the remaining session numbers to the new days, the sequence itself survives.

## Suggest (suggest)

"suggest", alone or with context ("suggest something for pull", "suggest but nothing for legs"), means propose goals. The agent picks them, the user approves them.

1. Pull as much history as needed for a confident read: check Progression state first for live per-lift momentum, then `range` and `history` back until trends are clear, not a fixed window. Thin history means fewer suggestions or none, said honestly.
2. Propose several concrete goals: movement, exact target, deadline. Each one already realism checked, with one line on why it fits (rate of gain, fresh stall broken, lagging lift).
3. Nothing is written until the user picks. Approval converts straight into the Goals flow with a trajectory.

## Prioritize (prioritize)

`prioritize <muscle> [for <duration>]`, in plain words ("side delts for the next 3 months", "bring up hamstrings"). Fully specified requests execute in the same response. Open requests ("wanna bring up my side delts, what do you suggest?") get a short thread first: state the current picture from data (frequency, volume vs landmarks, trend, recovery notes), ask only what the recommendation depends on (time for extra exposure, recovery state if stale, duration if missing), then propose order plus sets plus frequency verdict with one line of reason each, and execute on confirm.

1. Resolve the muscle first: delt heads track separately, so "delts" alone gets asked which head. Untracked groups (neck, calves, traps) are refused, or tracked first per the mapping rule.
2. Rewrite the active split: the muscle's lifts move to position 1, second at worst, in every slot containing them. If another focus is already active, ask how to order the two before rewriting. Their set counts go up; other accessories in the same slots drop a set or hold (never to zero) so total session volume stays roughly flat. Baseline split is untouched and never planned from. A user-stated rewrite is authorized; a later unusual session still never rewrites anything on its own. If a workout is open, the rewrite takes effect next session unless the user says to apply it now.
3. Write one Active rule carrying the intent: muscle, positioning floor, volume direction, expiry date, or standing until explicitly revoked when no duration is given. A second note only if something doesn't fit the rule line. In the same step, run `priority set <muscle> <tier> [--until <date>]` (`tier` one of `priority` / `maintain` / `deprioritize`, no `--until` for standing; absence means `maintain`). Prose rule and table entry always stay in sync: expiry, revocation, or duration change updates both in the same step. Expiry flows into Needs confirm for the renew-or-revert moment.
4. Check GOALS.md for a goal covering that muscle (any lift training it counts). If one exists, state the pairing and move on. If none exists, auto-run the suggest flow scoped to that muscle: multiple concrete goals, with deadlines inside the focus window when one was given, each already realism-checked. The user picks any, several, or none. A pick converts into a trajectory per the normal Goals flow. Declining is legitimate: the split rewrite and notes stand without a goal.
5. Downstream needs no new rules: planning reads the rewritten split directly; the focus Active rule exempts that muscle from ledger volume holds while everything else gates normally; the Priority tier breaks ties whenever a session has slack volume inside its MAV/MRV band (see Session start step 7), but it never overrides an active Goal trajectory's numbers (Goal trajectories already take strict precedence per the Goals section); reordered sessions are marked in the `end` note with conservative progression verdicts on displaced lifts; revert means restoring baseline lines on request.

## Memory writeback

Chat history dies with the session, files survive. When user states something durable, write it down:

1. Prefs and plans (`always incline, never flat`, `incline block until November`, injury notes) go to `MEMORY.md` under Active rules with start date and expiry. Permanent per-movement facts go to `MOVEMENTS.md` instead (new mappings into the Lift mapping list, durable setup specifics like stack jumps and machine settings under Movement notes, even when first noticed mid-session). Goal statements go to `GOALS.md`. Expired rules move to Needs confirm and get asked about once, then reactivated with a new date or archived. Nothing durable is ever deleted without an answer.
2. Session feel and life context go to workout notes via `end`. End notes stay lean, one line, only what numbers cannot explain (returns, new lifts, rep scheme shifts, bad sleep, pain). DB holds weights. Pain/sleep silent when fine. Example: Baseline Upper A. Shoulder press first time in a year. First session pushing higher reps on isolations. Reverse curl new. Set level notes go on the set.
3. At month end on request, append a short rollup to `MEMORY.md` under Monthly rollups: trend plus caveats in a few lines. Raw sets stay in SQLite, never paste them into memory files.
4. Compaction runs once a month. When the Session start check triggers it: archive expired rules older than 60 days, fold superseded State and Progression state lines into one current line each, write last month's rollup. Rollups are never deleted. Update the Last compacted stamp when done. If the user says later, skip silently until next session.
5. Every compaction publishes last month's rollup as a postplan doc (PRs, stalls, adherence with miss versus rest verdicts, next block suggestion) using the postplan workflow, links it in chat, and stores the link with the rollup in MEMORY.md.
6. At every session `end`, update the plan state for the session just trained: Progression state for every trained lift via `progression set` (verdict versus target, next target and direction; a lift's first session baselines its top set by e1RM; actuals stay in the db, never duplicated), and new Flagged entries via `flag add` for clear over/underperformance versus ledger headroom (consumed flags were already auto-consumed by `plan`). The Muscle load ledger is derived by `plan` and needs no writeback. Mid-session reasoning stays ephemeral: ledger checks, threshold explanations, and bump rationales live in chat only, never in session or set notes.
7. Deload sessions: the `end` note for a session trained under Deload state must include the word `deload` (the gate enforces this). Required, not optional: AUDIT.md check 4 and `cmd_audit`'s progression-jump/drop logic treat a note containing "deload" as an explained deviation, so without the keyword the deliberately reduced volume would flag as an unexplained `progression_drop` on the next audit run. After `end` completes, run `deload clear` (it appends the dated State line `YYYY-MM-DD: deload completed for <scope> <subject>` itself), the same dated-line convention expired Active rules use when they archive out.

Keep `MEMORY.md` short. Current state only, dated lines, no essays.

## SCIENCE.md updates

"audit the research" or similar phrases triggers a refresh of SCIENCE.md. Process:

1. Search for recent (ideally last 2–3 years) meta-analyses and systematic reviews on each topic SCIENCE.md covers: volume landmarks, frequency, rep ranges, proximity to failure, progression rates, deload, exercise selection.
2. Weigh findings using the trust hierarchy in SCIENCE.md's header (meta-analyses > RCTs > practitioner synthesis > anecdotal).
3. For each entry: if new evidence shifts the tier or the number, propose the change with citation (author/group + year). Conflicting findings → state the range and why, keep Contested tier.
4. Present proposed changes for approval. Nothing overwrites silently — same approval pattern as Goals flow. On approval, rewrite the affected sections, update "last reviewed" date.
5. Personal deviations section is never touched by this process; only I add there.

This is distinct from data-quality audits or compaction. It only refreshes the external evidence base.

## Split review (review the split)

"review the split" or similar phrases triggers a check of the Active split against SCIENCE.md's existing exercise-selection evidence. Process:

1. For each slot in the Active split, cross-check it against SCIENCE.md's Exercise selection principles table and the Personal deviations section. A deviation already on file for a given slot means no flag, settled decisions are not re-litigated. Also run `priority list`: a `priority` tier muscle whose slots don't reflect that emphasis (insufficient frequency, no interchangeable variety) gets flagged here too.
2. For anything flagged, propose a specific swap or addition with the principle cited, same evidentiary rigor SCIENCE.md itself uses (Settled / Contested / Opinion tier, source).
3. Present all proposed changes together. Nothing is written until the user approves, same approval pattern as the SCIENCE.md update flow and the Goals flow.
4. On approval, this is "the user says the split changed" per Split rule 3: rewrite the Active split with an updated date through that exact mechanism, no parallel edit path. One-off sessions still never trigger a program change on their own.
5. This only runs when invoked by name. It is never automatic and never suggested unprompted.

This is distinct from "audit the research" (which refreshes SCIENCE.md against external literature) and "audit the data" (which checks logged data quality). Each trigger does exactly one job.

## AUDIT.md (audit the data)

"audit the data" triggers a non-deterministic data quality check per AUDIT.md protocol. This is a correlated check (same reasoning that could produce a bad log does the checking) — it complements the pytest layer, does not replace it. At every session `end`, audit that session only (all sets have muscles, set counts match the split slot, canonical names). Never run a full-DB audit unless asked.

When user says "audit the data", execute this runbook **exactly**:

1. **Pull data**: run `context` (recent 3 workouts + per-lift bests), then `range <from> <to>` covering last 90 days (or `export` if history is thin). Also `calendar` for gaps. Also `exercises` for name list. Also run `priority list`: check 8 severity depends on `deprioritize` tiers, so the manual pass needs it in front of it before scoring volume flags.
2. **Run checklist** (from AUDIT.md) in order. For each item:
   - Execute the described query against the pulled data
   - If flagged: record `flag: {check: N, severity: high|medium|low, evidence: "specific rows/dates/ids", fix: "one-line fix"}`
   - Never auto-correct
3. **Output report**: one message with all flags, formatted:

   ```
   Audit complete: N flags (X high, Y medium, Z low)

   1. [check name] — severity
      Evidence: ...
      Fix: ...
   ```

4. **Log to MEMORY.md**: append to State section: `YYYY-MM-DD: audit ran, N flags (X high, Y medium, Z low)`
5. **Stop** — do not auto-fix, do not continue to other tasks.

## ISSUES.md

When the user explicitly flags a problem with the agent's interpretation, suggestion, or behavior — "that's wrong", "fix this", "log this issue" — append an entry to ISSUES.md using the template there. Date, one-line summary, the concrete example/trigger, severity (high/medium/low), and a brief fix note. This is for things the user notices but can't fix in the moment. Do not log every minor clarification, only explicit "this is an issue" signals.

`context`, `stats`, `calendar`, `session`, `range`, and `history <exercise>` give ground truth numbers. Gym mode reasons from plan state (`MEMORY.md`, `MOVEMENTS.md`, `GOALS.md`), `today`, and the `lifts` array only, plus the single sanctioned step-7 live volume pull. Review mode may pull hundreds of sessions at once with `range` or `notes`, that output feeds agent reasoning for chat answers and postplan docs, it is never shown raw. Then add your own read on top: trend, e1RM direction, volume per muscle, rotation adherence from `calendar` dates and gaps (rest days fall after Upper B and Lower B) (raw dates in, verdict out, explicit `rest: true` dates decide planned rest first, travel and sick notes from memory only break ties on untracked gaps), PRs, stalls, caveats (small sample, pain notes, missed sessions). Keep it short and honest. Numbers first, take second.

Volume is anatomical by muscle group, and one set can count for several groups at once. Tracked groups live in MOVEMENTS.md under Tracked muscles (currently chest, back, front delt, side delt, rear delt, biceps, triceps, quads, hamstrings, glutes, abs, forearms, adductors; never neck, calves, traps). Per lift attribution lives in MOVEMENTS.md under Lift mapping. If a new movement maps to an untracked group or no clear group, ask once whether to track it, then follow the answer.

Never present tonnage or total set counts as achievements, in chat or on the dashboard. Totals like that mean nothing about progress. Trends, PRs, and adherence are the currency. A PR is any set beating the prior best e1RM for that lift. The first logged set per lift is the baseline, not a PR.

## Dashboard iteration

The dashboard is malleable, not finished. Change it freely whenever the user asks, taste included. It lives in `dashboard/` (`index.html` at root plus `src/` modules: index.ts, worker.ts, utils.ts, charts.ts, liftChart.ts, miniChart.ts, bwChart.ts, stackedChart.ts, date.ts, tip.ts, prs.ts) and deploys with `npm run deploy` from `dashboard/` (auth via CLOUDFLARE_API_TOKEN read from `~/.config/reps/cf_token` plus the account id, both already on this machine). Verify live with curl on `/snapshot` and the root page after every deploy.

Every UI change gets verified before reporting done: `pre-commit run --all-files` (format, lint, typecheck, unit, pytest, backslash gate, same suite CI runs), then `npx playwright test` from `dashboard/` (e2e plus visual regression against committed baselines in `e2e/snapshots/`, generated from deterministic mock data with frozen clock). Phone width plus desktop width, checking the changed view.

Conventions: keep charts honest (e1RM is weight times 1 plus reps over 30, except a true single whose e1RM is the weight itself), keep the snapshot schema forward compatible (the worker ignores unknown fields, so the CLI can add new sections without breaking the page). Each set carries its own muscle list, the volume chart reads it directly and one set can credit several groups. There is no name-pattern fallback anywhere: unmapped lifts are left out entirely until the agent maps them via `retag`. The trend section is small multiples, one mini chart per lift on its own scale with PR trophies and tap-through to the lift page, visibility follows toggle chips (top 8 on by default, All and None buttons, picks persist), palette holds 24 colors. Zero weight sets are excluded from trend lines. Session tables use real thead and tbody. Saved legend prefs prune names missing from the snapshot on load. Never use backslash escapes in dashboard/src/\*, the deploy pipeline strips them and silently breaks the page. `src/worker.ts` is the Worker entry and must stay DOM free, enforced by `src/__tests__/worker.smoke.test.ts` (node env, no DOM, importing it must not throw). `src/index.ts` is browser only. Prefer graphs over headline numbers. PR marker is the trophy icon everywhere (session tables, calendar corner, lift chart canvas), never dots, rings, stars, or pills.

## Dashboard sync

`sync` pushes the full export plus bodyweight to https://reps.bojan-dev.workers.dev/ where the hosted dashboard reads it. Auth lives in `~/.config/reps/config.json`, never in the repo. Local SQLite stays the source of truth. The `workouts.db` binary is gitignored; instead `sync` dumps a text SQL dump (`workouts.sql`) which is committed to git. This gives clean diffs and readable history.

Recovery: if `workouts.db` is corrupted or poisoned, do not `git checkout workouts.db` (it is ignored). Instead:

```
git checkout workouts.sql
rm -f workouts.db
sqlite3 workouts.db < workouts.sql
```

Or run `log.py restore` which does this automatically.

Test CLI flows with `REPS_DB` pointed at /tmp, never the real db. Deterministic checks live in `tests/` (`uv run --with pytest --no-project pytest tests/ -q`; system python has no pytest and no pip, so never `python -m pytest` directly). If a push ever conflicts (two sessions writing at once), pull first, then push. `sync` enforces this server side with ETags: it pulls the snapshot ETag first and pushes with If-Match, a stale base gets a 412 and aborts instead of overwriting. Reconcile, then `sync force` to overwrite deliberately.
