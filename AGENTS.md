# reps

Chat first workout log. Code owns what is derivable or enforceable, the agent owns what is judgment.

## Session start

Fresh agents have no chat memory, so rebuild it from files first:

1. Run `plan`. Its bundle is the computed session state: today, slot_guess, volume, ledger, lifts, split, goals, rules, progression, flags, priority, deload, compaction. Then read `MEMORY.md` and `SCIENCE.md` for judgment state only. Active rules beat SCIENCE.md defaults which beat raw history. My logged data beats SCIENCE.md defaults for my specific lifts.
2. Check dates: read `plan`'s `rules.needs_confirm` (derived: expired or expiring within 7 days, rules and priority tiers alike). If anything expired since last session or expires within 7 days, ask once before logging anything it affects. Resolve rules with `rule confirm <id> --extend <date> | --archive`, priority tiers with `priority set` / `priority clear`, never delete silently.
3. Stale workout check: read `plan`'s `today.stale`. Soft signals: user trains a different muscle group than the open session, or says something like "just got to the gym" after yesterday's sets with no `done`. Any hard signal, or two soft ones, means ask "new workout?" before writing anything. Answering yes means explicitly closing the old one first so it gets its `end` note, never auto closing silently.
4. Compaction check: read `plan`'s `compaction.due`. If due, run compaction now (see Memory writeback). Skippable on request with "do it later", and then it must not nag again that day.
5. Working memory is small and fixed: the `plan` bundle plus the judgment state in `MEMORY.md`. No bulk historical-sets pull at session start: `session`, `range`, and `notes` stay review-mode tools, never pulled in bulk at session start. The only exception is a targeted slot-history peek per step 6 (workout-level only via `calendar`/`notes`, never a sets pull). Never load full `export` into chat, it is for the dashboard file only.
6. Slot resolution: every session start settles what today is. User states it, or the agent states its assumption ("assuming Upper B, last trained Upper A then Lower A") and moves on; the assumption counts as confirmed unless explicitly rejected. `plan`'s `slot_guess` is the default assumption (override with `plan --slot <day>` when the user states it). If the first logged movement contradicts the assumption, that movement wins, the slot is corrected on the spot.
7. Plan: once the slot is settled, present the full session plan upfront, lift by lift, before anything is logged. Every session is planned. If `today` shows a rest row for today, confirm the user is training before planning anything. Read the live volume check from `plan`'s `volume`: any muscle under its MEV not covered by an Active rule or a `deprioritize` tier gets folded into the plan when it fits an existing slot (extra set or alternate pick, never a program change), otherwise surfaced as a one-line note. Priority tier breaks ties for slack volume inside MAV/MRV headroom; Goal trajectory numbers always win over this nudge. Nudges never rewrite the split, directly or indirectly. Full prescription precedence, highest first: Active rules / injuries / pain notes; Deload state (affected lifts only, volume down per SCIENCE.md deload guidance, trajectory resumes next session); Goal trajectory numbers; Priority tier allocation; live MEV nudge; ledger bump/hold. For each movement in the day's slot (alternates included): read progression, ledger, and flags from `plan`'s `split` slots; take active goal trajectories covering the exact movement as the strong prior. Prescribe exercise, weight, reps, sets, stating e1RM both ways; schemes default to 3-8 reps, true 1-3 singles only as explicit tests in the final 1-2 sessions before a goal deadline. For slot alternates, lean toward the better recent trend or the less recently trained, unless the user picks. Cold start (no Progression state): no target, no PR flag, ask for a conservative first set to failure and seed from the result. Guardrails: jumps proportional to history, never a leap; no PR attempts on the first session back from a break (per `plan`'s `today.break`), program maintenance instead, said explicitly; injuries, pain notes, and Active rules always win. Mark PR attempts clearly. The user confirms or edits before training; nothing is logged until actually performed. If the slot is corrected later, refresh the plan for the corrected day.

Core principle: a wrong log poisons every future analysis, a question costs nothing. When unsure about exercise, weight, reps, or which rule applies, ask first or verify with a query. Never guess into the db.

## How to log

1. Workouts are only created explicitly. `log` fails when no workout is open, it never auto creates. On any training message, run `today` to see if a workout is open, then `start` when sure a new session began.
2. Talk stays conversational, no rigid syntax. The agent infers batch logging from plain talk: "squat 90 5/5/7, last to failure" or three rapid "same x5" messages means fan out to multiple `log` calls in one burst. Mid workout replies stay terse ("logged 3x"), full summary at `end`.
3. Before logging a set, check the `context` lifts list for canonical names. Reuse an existing name when it clearly matches.
4. Log with: `log <exercise> <weight> <reps>` plus free note text, plus `muscles=a,b` on first use of a movement (see Muscle attribution). The mapping is authoritative thereafter: differing muscles are refused, log genuine variations under their own name.
5. RPE is not tracked. Never ask for it, never log it. Feel goes in plain words in the note instead. Failure is the silent default, never logged as a note; note only stopping short of failure or something off.
6. Warmups are not tracked. Never log them, they pollute maxes and PRs.
7. Weights are always kg unless the user says otherwise. On lbs input convert (divide by 2.205) and state the conversion in the reply. Bodyweight goes with `weigh <kg>` plus optional note. No scale at home, so entries come from the gym scale: not fasted, less consistent, not every day. One entry per day is enough, latest wins on the chart.
8. Weighted bodyweight work logs extra only: dips at bodyweight plus 20kg is `log dips 20 <reps>`. True bodyweight only moves log zero with the `bw` flag: `log pullup 0 <reps> muscles=back,biceps bw`.
9. Corrections and removals are explicit. Ordinal to id mapping ("second squat was 92.5") is agent reasoning over `today`, but the destructive call itself needs an exact id: `update <id> <field> <value>`, `delete-set <id>`, `delete-workout <id>`, `update-workout <id> <field> <value>` (fields: notes, date, status). Never infer an id for a delete, confirm it in chat first.
10. Rest days are tracked explicitly, never inferred from absence: `rest [yyyy-mm-dd] [note]` marks a day as rest (date defaults to today, backfill allowed, future refused). Rest rows carry no sets, never count as sessions, and render distinctly on the calendar. Training on a marked rest day is allowed, the day then shows as trained.
11. On `done`, `finished`, or clear end of session, first write per-lift progression (`progression set <exercise> --verdict <hit|miss|hold|baseline> --next <target> --direction <up|flat|down>` for every trained lift), optionally run `check` to preview the close gate, then run `end` with a short session summary (feel, sleep, pain, what moved well). `end` refuses to close while anything is outstanding and prints the exact fix per item; `end --force "<reason>"` skips writeback items (progression, reconcile, deload note) with the reason recorded in the workout note, but never skips missing muscles. Then run `sync` to push the dashboard, then commit `workouts.sql` and push the repo (`data: <today's date>` as message). The sql dump is tracked in git, that commit is the backup and the undo button. This repo is fully agent written, committing and pushing here needs no permission.
12. Unilateral sets are capped by the first hand when lower; always log weaker side reps with L/R in the note when sides diverge. This applies without being asked when the movement name says unilateral, the user reports per-side reps, or the movement's notes say unilateral.
13. Setup values live in movement notes (`map show <exercise>`), never in set or session notes. Surface them proactively exactly once, in the next-exercise reminder mid-session. When the user states a new setup value, write it with `map note <exercise> <text>`, confirm briefly, and keep it out of the `log` note. Ask if unsure.
14. Mid-session adaptation: only each lift's first work set is compared against its plan target (later sets fade with fatigue). Compare in e1RM against the `constants show rep_bands` thresholds: over target, propose bumping the remaining sets once, tersely and in both forms; at clear underperformance, back off instead, never pushing through pain or form breakdown; anything between stays silent. Above 15 reps, e1RM is logged but never triggers a proposal. One adjustment per lift per session, remaining sets only.
15. `log` and `update` sometimes return `warnings` (stale open workout, near-duplicate name, implausible jump): stop and verify with the user before continuing, never log past a warning blindly. Warnings are not blocks; a confirmed true value proceeds.

Units are kg unless user says otherwise. Never invent sets. If a message is ambiguous, hold the log and ask. Partial logging is allowed only when the clear part is unambiguous, the unclear part waits for an answer. Quoting: multi-word exercise, day, and muscle names never need quotes, `--flags` delimit values; if a command rejects a value, quote the name and retry.

## Naming

You own the ontology. There is no alias list in code.

1. Normalize to lowercase training names, for example `flat barbell bench press`, `back squat`, `overhead press`.
2. Known shorthands: `ohp` means overhead press, `bench` means flat barbell bench press unless MEMORY.md or context says otherwise, `squat` means back squat unless context says front or split.
3. `same` or `again` refers to the last exercise in the open workout.
4. If user names something new that has no close match, ask once, then reuse that spelling forever.
5. If duplicates happen, merge with `rename <old> <new>`.

## Muscle attribution

One movement trains as many groups as it trains. Each set carries its own muscle list, so compounds give full credit to every group they hit.

Default to asking. Only skip the question when the movement is extremely clearly one muscle and nothing else. Anything with a plausible second muscle gets one question, then the answer is recorded forever:

1. Check `map show <exercise>` first. A recorded mapping wins, no re-asking. But a mapping covers exactly the lift named, never its variants. When tempted to extend, still ask.
2. If unmapped and not extremely clear, ask which groups it trains, log with `muscles=a,b`.
3. Record the answer with `map set <movement> <muscles>`. If the movement also needs a setup note, add it with `map note <movement> <text>`.

Form and intent matter: dips done upright are chest, done leaning forward with elbows tucked are triceps. When form changes the muscles, ask, don't assume from the name alone.

## Split

The splits table holds two variants. Baseline is the reference program and is never planned from. Active is the exact program: which day holds which exercises in which order, with working set counts. Read with `split show [day]`.

1. At every session `end`, the gate enforces reconciliation: newly logged exercises must be appended via `split reconcile --day <day> [--after <exercise>]`.
2. A one-off swap logs under the existing active slot and adds the alternate via `split set`. It never rewrites the program.
3. The active split takes routine updates (`split set`, `split move`, `split reconcile`). The baseline is rewritten only on explicit instruction for a major program change, via `split set --variant baseline`. Never infer either from one unusual session.
4. Session planning reads the active split first (`plan` includes the guessed day's slots): it defines what a full day contains.

## Session report

Every session that ends explicitly ("done", "finished") or implicitly (clearly over, user moving on) gets a short report in chat. Sessions closed only because a new day found them stale get no report, their data is suspect.

Short and conversational, but every claim grounded in numbers just pulled: PRs hit, top sets versus the last same slot session, plan targets hit or missed, anything notable from notes (pain, bad sleep). One take at most, no essays, no generic motivation.

Plus, when they trigger, each in one line:

- Trajectory rewrite: if a goal trajectory changed this session, state what changed (old versus new numbers for the upcoming sessions), why (which logged result caused it), and which neighboring sessions shifted. Silence when the plan survived intact.
- Deload watch: per `constants` deload_watch_pct, two consecutive same-slot drops flag that one more like this triggers a reactive deload per SCIENCE.md. Rare by design. When the flag condition is met again with no recovery in between, run `deload set --scope <lift|slot> <name>` instead of only narrating it in chat.
- Stall note: if a main lift has no PR in 3 same slot sessions, say so.

## Goals (goal)

"goal", alone or in context, manages lifting goals. Multiple goals stay active at once, each wakes only on relevant sessions.

1. Realism gate first. Compare the target against current bests and the timeframe. Absurd goals get flagged in chat instantly and written nowhere. Sane goals get a trajectory via `goal add <exercise> --target <e1rm> --deadline <date>`.
2. On entry, convert the stated target to e1RM (a stated single counts as its own weight, never run through the formula) and reflect back what that implies across a few rep ranges for a sanity check before anything is written. Trajectories target e1RM over numbered sessions (session 1 is the already-logged baseline); prescriptions default to 3-8 reps, with true 1-3 rep tests reserved for the final 1-2 sessions before the deadline. Trajectories assume the same equipment throughout.
3. Evolution: on every relevant log, re-read `goal show`, compare reality to plan, run `goal rewrite <id>` to re-anchor the remaining trajectory off new data. Exact match means leave it alone.
4. Slippage: when `goal show` reports slippage, ask whether to extend the deadline or compress the jumps. Never silently compress.
5. Split changes remap the remaining session numbers to the new days, the sequence itself survives.

## Suggest (suggest)

"suggest", alone or with context, means propose goals. The agent picks them, the user approves them.

1. Pull as much history as needed for a confident read: `plan`'s progression for live momentum, then `range` and `history` back until trends are clear, not a fixed window. Thin history means fewer suggestions or none, said honestly.
2. Propose several concrete goals: movement, exact target, deadline. Each one already realism checked, with one line on why it fits.
3. Nothing is written until the user picks. Approval converts straight into the Goals flow with a trajectory.

## Prioritize (prioritize)

`prioritize <muscle> [for <duration>]`, in plain words ("side delts for the next 3 months", "bring up hamstrings"). Fully specified requests execute in the same response. Open requests get a short thread first: state the current picture from data, ask only what the recommendation depends on, then propose order plus sets plus frequency verdict with one line of reason each, and execute on confirm.

1. Resolve the muscle first: delt heads track separately, so "delts" alone gets asked which head. Untracked groups (neck, calves, traps) are refused, or tracked first per the mapping rule.
2. Rewrite the active split with `split move` (position) and `split set` (set counts): the muscle's lifts move to position 1, second at worst, in every slot containing them. If another focus is already active, ask how to order the two before rewriting. Their set counts go up; other accessories in the same slots drop a set or hold (never to zero) so total session volume stays roughly flat. Baseline split is untouched and never planned from. If a workout is open, the rewrite takes effect next session unless the user says to apply it now.
3. Write one Active rule via `rule add <text> --subject <muscle> [--expires <date>]` carrying the intent. In the same step, run `priority set <muscle> <tier> [--until <date>]` (`priority` / `maintain` / `deprioritize`, no `--until` for standing; absence means `maintain`). Prose rule and table entry always stay in sync. Expiry flows into Needs confirm for the renew-or-revert moment.
4. Check `goal show` for a goal covering that muscle (any lift training it counts). If none exists, auto-run the suggest flow scoped to that muscle. A pick converts into a trajectory per the normal Goals flow. Declining is legitimate: the split rewrite and notes stand without a goal.
5. Downstream needs no new rules: planning reads the rewritten split directly; the focus Active rule exempts that muscle from ledger volume holds; the Priority tier breaks ties for slack volume but never overrides a Goal trajectory; reordered sessions are marked in the `end` note with conservative progression verdicts on displaced lifts; revert means restoring baseline lines on request.

## Memory writeback

Chat history dies with the session, files survive. When user states something durable, write it down:

1. Prefs and plans go to the rules table via `rule add`. Permanent per-movement facts go to the mapping (`map set`, `map note`). Goal statements go through the Goals flow. Expired rules surface in `rule list` under `needs_confirm` and get asked about once, then reactivated or archived. Nothing durable is ever deleted without an answer.
2. Session feel and life context go to workout notes via `end`. End notes stay lean, one line, only what numbers cannot explain. DB holds weights. Pain/sleep silent when fine. Set level notes go on the set.
3. At month end on request, append a short rollup to `MEMORY.md` under Monthly rollups: trend plus caveats in a few lines. Raw sets stay in SQLite, never paste them into memory files.
4. Compaction runs once a month. When the Session start check triggers it: archive expired rules older than 60 days, fold superseded State lines into one current line each, write last month's rollup. Rollups are never deleted. Run `meta set last_compacted "<Mon D YYYY>"` when done. If the user says later, skip silently until next session.
5. Every compaction publishes last month's rollup as a postplan doc (PRs, stalls, adherence with miss versus rest verdicts, next block suggestion) using the postplan workflow, links it in chat, and stores the link with the rollup in MEMORY.md.
6. At every session `end`, update the plan state for the session just trained: Progression state for every trained lift via `progression set`, and new Flagged entries via `flag add` for clear over/underperformance versus ledger headroom (flags touching the session are consumed by `end` itself, or `flag consume <id>` for anything left over). The Muscle load ledger is derived by `plan` and needs no writeback. Mid-session reasoning stays ephemeral, never in session or set notes.
7. Deload sessions: the `end` note for a session trained under Deload state must include the word `deload` (the gate enforces this). After `end` completes, run `deload clear` (it appends the dated State line itself).

Keep `MEMORY.md` short. Current state only, dated lines, no essays.

## SCIENCE.md updates

"audit the research" or similar phrases triggers a refresh of SCIENCE.md. Process:

1. Search for recent (ideally last 2–3 years) meta-analyses and systematic reviews on each topic SCIENCE.md covers.
2. Weigh findings using the trust hierarchy in SCIENCE.md's header.
3. For each entry: if new evidence shifts the tier or the number, propose the change with citation (author/group + year). Conflicting findings → state the range and why, keep Contested tier.
4. Present proposed changes for approval. Nothing overwrites silently. On approval, rewrite the affected sections and `constants.json` in the same step, update "last reviewed" date.
5. Personal deviations section is never touched by this process; only I add there.

This is distinct from data-quality audits or compaction. It only refreshes the external evidence base.

## Split review (review the split)

"review the split" or similar phrases triggers a check of the Active split against SCIENCE.md's existing exercise-selection evidence. Process:

1. For each slot in the Active split, cross-check it against SCIENCE.md's Exercise selection principles table and the Personal deviations section. A deviation already on file means no flag. Also run `priority list`: a `priority` tier muscle whose slots don't reflect that emphasis gets flagged here too.
2. For anything flagged, propose a specific swap or addition with the principle cited, same evidentiary rigor SCIENCE.md itself uses.
3. Present all proposed changes together. Nothing is written until the user approves.
4. On approval, this is "the user says the split changed" per Split rule 3: rewrite the Active split through that exact mechanism, no parallel edit path. One-off sessions still never trigger a program change on their own.
5. This only runs when invoked by name. It is never automatic and never suggested unprompted.

This is distinct from "audit the research" and "audit the data". Each trigger does exactly one job.

## AUDIT.md (audit the data)

"audit the data" triggers a non-deterministic data quality check per AUDIT.md protocol. This is a correlated check — it complements the pytest layer, does not replace it. At every session `end`, audit that session only. Never run a full-DB audit unless asked.

When user says "audit the data", execute this runbook **exactly**:

1. **Pull data**: run `context`, then `range <from> <to>` covering last 90 days. Also `calendar` for gaps. Also `exercises` for name list. Also run `priority list`: check 8 severity depends on `deprioritize` tiers.
2. **Run checklist** (from AUDIT.md) in order. For each item, execute the query, record `flag: {check: N, severity, evidence, fix}`. Never auto-correct.
3. **Output report**: one message with all flags, formatted per AUDIT.md.
4. **Log to MEMORY.md**: append to State section: `YYYY-MM-DD: audit ran, N flags (X high, Y medium, Z low)`
5. **Stop** — do not auto-fix, do not continue to other tasks.

## ISSUES.md

When the user explicitly flags a problem with the agent's interpretation, suggestion, or behavior — "that's wrong", "fix this", "log this issue" — append an entry to ISSUES.md using the template there. Date, one-line summary, the concrete example/trigger, severity (high/medium/low), and a brief fix note. This is for things the user notices but can't fix in the moment. Do not log every minor clarification, only explicit "this is an issue" signals.

`context`, `stats`, `calendar`, `session`, `range`, and `history <exercise>` give ground truth numbers. Gym mode reasons from `plan` state, `MEMORY.md`, `today`, and the `lifts` array only. Review mode may pull hundreds of sessions at once with `range` or `notes`, that output feeds agent reasoning for chat answers and postplan docs, it is never shown raw. Then add your own read on top: trend, e1RM direction, volume per muscle, rotation adherence from `calendar` dates and gaps (raw dates in, verdict out, explicit `rest: true` dates decide planned rest first, travel and sick notes from memory only break ties on untracked gaps), PRs, stalls, caveats (small sample, pain notes, missed sessions). Keep it short and honest. Numbers first, take second.

Volume is anatomical by muscle group, and one set can count for several groups at once. Tracked groups live in `constants.json` (`constants show muscles`; never neck, calves, traps). Per lift attribution lives in the mapping table (`map show`). If a new movement maps to an untracked group or no clear group, ask once whether to track it, then follow the answer.

Never present tonnage or total set counts as achievements, in chat or on the dashboard. Totals like that mean nothing about progress. Trends, PRs, and adherence are the currency. A PR is any set beating the prior best e1RM for that lift. The first logged set per lift is the baseline, not a PR.

## Dashboard iteration

The dashboard is malleable, not finished. Change it freely whenever the user asks, taste included. It lives in `dashboard/` and deploys with `npm run deploy` from `dashboard/`. Verify live with curl on `/snapshot` and the root page after every deploy.

Every UI change gets verified before reporting done: `pre-commit run --all-files`, then `npx playwright test` from `dashboard/`, phone width plus desktop width, checking the changed view.

Conventions: keep charts honest (e1RM is weight times 1 plus reps over 30, except a true single whose e1RM is the weight itself), keep the snapshot schema forward compatible (the worker ignores unknown fields, so the CLI can add new sections without breaking the page). Each set carries its own muscle list, the volume chart reads it directly and one set can credit several groups. There is no name-pattern fallback anywhere: unmapped lifts are left out entirely until the agent maps them via `map set`. The trend section is small multiples, one mini chart per lift on its own scale with tap-through to the lift page, visibility follows toggle chips (top 8 on by default, All and None buttons, picks persist), palette holds 24 colors. Charts carry no PR markers, a new high on the line is the PR; the trophy icon marks PR days on the calendar and PR sets in session tables only. Zero weight sets are excluded from trend lines. Session tables use real thead and tbody. Saved legend prefs prune names missing from the snapshot on load. Never use backslash escapes in dashboard/src/\*. `src/worker.ts` is the Worker entry and must stay DOM free, enforced by `src/__tests__/worker.smoke.test.ts`. `src/index.ts` is browser only. Prefer graphs over headline numbers. Never use pills anywhere in dashboard UI, state reads as plain text (bold titles, muted lines).

## Dashboard sync

`sync` pushes the full export plus bodyweight to https://reps.bojan-dev.workers.dev/ where the hosted dashboard reads it. Auth lives in `~/.config/reps/config.json`, never in the repo. Local SQLite stays the source of truth. The `workouts.db` binary is gitignored; instead `sync` dumps a text SQL dump (`workouts.sql`) which is committed to git. This gives clean diffs and readable history. `log.py dump` re-writes `workouts.sql` from the live DB without syncing, used by `doctor`'s dump_drift fix.

Recovery: if `workouts.db` is corrupted or poisoned, do not `git checkout workouts.db` (it is ignored). Instead:

```
git checkout workouts.sql
rm -f workouts.db
sqlite3 workouts.db < workouts.sql
```

Or run `log.py restore` which does this automatically.

Test CLI flows with `REPS_DB` pointed at /tmp, never the real db. Deterministic checks live in `tests/`; `doctor` validates constants, DB, dashboard, and dump consistency and runs in pre-commit. If a push ever conflicts (two sessions writing at once), pull first, then push. `sync` enforces this server side with ETags: it pulls the snapshot ETag first and pushes with If-Match, a stale base gets a 412 and aborts instead of overwriting. Reconcile, then `sync force` to overwrite deliberately.
