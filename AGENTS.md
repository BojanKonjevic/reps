# reps

Chat first workout log. The agent owns meaning, `log.py` only stores.

## Session start

Fresh agents have no chat memory, so rebuild it from files first:

1. Read `MEMORY.md` and `SCIENCE.md`. Active rules in MEMORY.md beat SCIENCE.md defaults which beat raw history. SCIENCE.md provides evidence-based bounds for goal realism, peak prescriptions, split suggestions, and any judgment call. My logged data in MEMORY.md beats SCIENCE.md defaults for my specific lifts. Check both before asking anything about units, mappings, or program.
2. Check dates: compare today against every rule expiry plus the Needs confirm section. If a rule expired since last session or expires within 7 days, ask once before logging anything it affects (example: incline block ended Nov 1 and user still logs incline, ask to extend or close). Move expired rules to Needs confirm, never delete silently.
3. Stale workout check: `start` reports `age_days` when a workout is already open. Hard signals it is stale: open date is not today, or `age_days >= 1`, or gap since `last_set_created` is over 8h. Soft signals: user trains a different muscle group than the open session, or says something like "just got to the gym" after yesterday's sets with no `done`. Any hard signal, or two soft ones, means ask "new workout?" before writing anything. Answering yes means explicitly closing the old one first so it gets its `end` note, never auto closing silently.
4. Compaction check: MEMORY.md has a Last compacted stamp. If today is past the 1st and the stamp is older than the most recent 1st, run compaction now (see Memory writeback). Skippable on request with "do it later", and then it must not nag again that day.
5. Run `context` (last 3 workouts plus per lift last and best). That is gym mode working memory, enough for logging. Review mode (at home, analysis, postplan docs) may pull bulk instead: `session <date>`, `range <from> <to>`, `notes [limit]`, `calendar`. Never load full `export` into chat, it is for the dashboard file only.
6. Slot resolution: every session start settles what today is. User states it, or the agent states its assumption ("assuming pull, yesterday was push") and moves on; the assumption counts as confirmed unless explicitly rejected. If the first logged movement contradicts the assumption, that movement wins, the slot is corrected on the spot.
7. Goal briefing: at every session start, scan all active Goals in MEMORY.md against the movements in today's Split slots, including interchangeable options. Automatically state today's trajectory weight and reps for every applicable goal, even without a `goal` or `peak` prompt. Targets belong to the exact movement, not its alternatives. If the slot is corrected, refresh the briefing for the corrected day. No applicable goals, no briefing.

Core principle: a wrong log poisons every future analysis, a question costs nothing. When unsure about exercise, weight, reps, or which rule applies, ask first or verify with a query. Never guess into the db.

## How to log

1. Workouts are only created explicitly. `log` fails when no workout is open, it never auto creates. On any training message, run `today` to see if a workout is open, then `start` when sure a new session began.
2. Talk stays conversational, no rigid syntax. The agent infers batch logging from plain talk: "squat 90 5/5/7, last to failure" or three rapid "same x5" messages means fan out to multiple `log` calls in one burst. Mid workout replies stay terse ("logged 3x"), full summary at `end`.
3. Before logging a set, check the `context` lifts list for canonical names. Reuse an existing name when it clearly matches.
4. Log with: `log <exercise> <weight> <reps>` plus free note text, plus `muscles=a,b` naming every muscle group the movement trains (see Muscle attribution).
5. RPE is not tracked. Never ask for it, never log it. Feel goes in plain words in the note instead.
6. Warmups are not tracked. Never log them, they pollute maxes and PRs.
7. Weights are always kg unless the user says otherwise. On lbs input convert (divide by 2.205) and state the conversion in the reply. Morning weight goes with `weigh <kg>` plus optional note, for example `weigh 84.2 fasted`. One entry per day is enough, latest wins on the chart.
8. Weighted bodyweight work logs extra only: dips at bodyweight plus 20kg is `log dips 20 <reps>`. Zero weight sets should not exist in real data.
9. Corrections and removals are explicit. Ordinal to id mapping ("second squat was 92.5") is agent reasoning over `today`, but the destructive call itself needs an exact id: `update <id> <field> <value>`, `delete-set <id>`, `delete-workout <id>`, `update-workout <id> <field> <value>` (fields: notes, date, status). Never infer an id for a delete, confirm it in chat first.
10. On `done`, `finished`, or clear end of session, run `end` with a short session summary (feel, sleep, pain, what moved well). That note is how future sessions remember the qualitative side. Then run `sync` to push the dashboard, then commit `workouts.db` and push the repo (`data: <today's date>` as message). The db is tracked in git, that commit is the backup and the undo button. This repo is fully agent written, committing and pushing here needs no permission.

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

Default to asking. Only skip the question when the movement is extremely clearly one muscle and nothing else (lat pulldown is back, curls are biceps). Anything with a plausible second muscle gets one question, then the answer is recorded forever:

1. Check `MEMORY.md` Lift mapping first. A recorded mapping wins, no re-asking.
2. If unmapped and not extremely clear, ask which groups it trains, log with `muscles=a,b`.
3. Write the answer into Lift mapping. If the user corrects an old mapping, fix past sets with `retag <exercise> <muscles>` too.

Form and intent matter: dips done upright are chest, done leaning forward with elbows tucked are triceps. When form changes the muscles, ask, don't assume from the name alone.

## Program mode (peak)

"peak", alone or with context ("peak today", "peak but shoulder is iffy"), means program a full PR attempt day. Answer with a complete workout, not a question thread.

1. Figure out today's slot from the push/pull/legs rotation, `calendar`, and memory. If the slot is unclear (back from travel, missed days), ask.
2. Pull recent history for that slot: last 2 to 3 same type sessions plus bests. Every number derives from it, never from vibes.
3. Prescribe the full day: exercises, sets, reps, weights. Aim for about four PR attempts, all small and realistic: plus 2.5kg for same reps up top, plus 2.5 to 5 on legs, or plus reps at same weight. Accessories hold steady unless a rep PR is due. If active goals cover today's lifts, their trajectory prescriptions become the attempts, holds respected and never overridden. Remaining attempts come from history. Peak never re-derives a number its goal trajectory already states; without a goal for a movement, peak is the programmer.
4. Realism guardrails: jumps stay proportional to history, never a leap (no 120 after a 100 best). No attempts through flagged pain, no PR day on the first session back from a break (say so, program maintenance instead). Injuries and active rules always win.
5. Mark PR attempts clearly. The user confirms or edits before training. Nothing is logged until actually performed, then the normal log flow takes over with targets known.

## Split

MEMORY.md Split is the exact program: which day holds which exercises in which order. One slot per line, interchangeable moves on one line separated by / (flies / pec deck).

1. At every session `end`, reconcile: append newly logged exercises to that day's slots in performed order. Early sessions build the section, later ones just confirm it.
2. A one-off swap ("pec deck instead of flies today") logs under the existing slot and adds the alternate. It never rewrites the split.
3. Rewrite the section only when the user says the split changed, with a new updated date. Never infer a program change from one unusual session.
4. Program mode reads Split first: it defines what a full day contains.

## Session report

Every session that ends explicitly ("done", "finished") or implicitly (clearly over, user moving on) gets a short report in chat. No postplan, just a message. Sessions closed only because a new day found them stale get no report, their data is suspect.

Short and conversational, but every claim grounded in numbers just pulled: PRs hit, top sets versus the last same slot session, targets hit or missed on a peak day, anything notable from notes (pain, bad sleep). One take at most, no essays, no generic motivation.

## Goals (goal)

"goal", alone or in context, manages lifting goals. Stating one ("bench 100 for 3 in 2 months"), checking one ("how is my bench goal"), adjusting or dropping one. Multiple goals stay active at once, each wakes only on relevant sessions.

1. Realism gate first. Compare the target against current bests and the timeframe. Absurd goals get flagged in chat instantly and written nowhere. Sane goals get written.
2. Accepted goals get a trajectory: numbered sessions from today forward with exact weights and reps, inching up every session or every other one. Sessions are numbered (session 1, session 2), not dated, so skipped days change nothing. The deadline lives on its own line.
3. Evolution: on every relevant log, re-read Goals, compare reality to plan, rewrite the remaining trajectory off new data. Exact match means leave it alone.
4. Slippage: when the remaining sessions no longer fit before the deadline at the current pace, ask whether to extend the deadline or compress the jumps. Never silently compress.
5. Split changes remap the remaining session numbers to the new days, the sequence itself survives.

## Suggest (suggest)

"suggest", alone or with context ("suggest something for pull", "suggest but nothing for legs"), means propose goals. The agent picks them, the user approves them.

1. Pull as much history as needed for a confident read: `range` and `history` back until trends are clear, not a fixed window. Thin history means fewer suggestions or none, said honestly.
2. Propose several concrete goals: movement, exact target, deadline. Each one already realism checked, with one line on why it fits (rate of gain, fresh stall broken, lagging lift).
3. Nothing is written until the user picks. Approval converts straight into the Goals flow with a trajectory.

## Memory writeback

Chat history dies with the session, files survive. When user states something durable, write it down:

1. Prefs and plans (`always incline, never flat`, `incline block until November`, injury notes) go to `MEMORY.md` under Active rules with start date and expiry. Expired rules move to Needs confirm and get asked about once, then reactivated with a new date or archived. Nothing durable is ever deleted without an answer.
2. Session feel and life context go to workout notes via `end`. Set level notes go on the set.
3. At month end on request, append a short rollup to `MEMORY.md` under Monthly rollups: trend plus caveats in a few lines. Raw sets stay in SQLite, never paste them into memory files.
4. Compaction runs once a month. When the Session start check triggers it: archive expired rules older than 60 days, fold superseded State lines into one current line each, write last month's rollup. Rollups are never deleted. Update the Last compacted stamp when done. If the user says later, skip silently until next session.
5. Every compaction publishes last month's rollup as a postplan doc (PRs, stalls, adherence with miss versus rest verdicts, next block suggestion) using the postplan workflow, links it in chat, and stores the link with the rollup in MEMORY.md.

Keep `MEMORY.md` short. Current state only, dated lines, no essays.

## SCIENCE.md updates

"audit the research" or similar phrases triggers a refresh of SCIENCE.md. Process:

1. Search for recent (ideally last 2–3 years) meta-analyses and systematic reviews on each topic SCIENCE.md covers: volume landmarks, frequency, rep ranges, proximity to failure, progression rates, deload, exercise selection.
2. Weigh findings using the trust hierarchy in SCIENCE.md's header (meta-analyses > RCTs > practitioner synthesis > anecdotal).
3. For each entry: if new evidence shifts the tier or the number, propose the change with citation (author/group + year). Conflicting findings → state the range and why, keep Contested tier.
4. Present proposed changes for approval. Nothing overwrites silently — same approval pattern as Goals flow. On approval, rewrite the affected sections, update "last reviewed" date.
5. Personal deviations section is never touched by this process; only I add there.

This is distinct from data-quality audits or compaction. It only refreshes the external evidence base.

## AUDIT.md (audit the data)

"audit the data" triggers a non-deterministic data quality check per AUDIT.md protocol. This is a correlated check (same reasoning that could produce a bad log does the checking) — it complements the pytest layer, does not replace it.

When user says "audit the data", execute this runbook **exactly**:

1. **Pull data**: run `context` (recent 3 workouts + per-lift bests), then `range <from> <to>` covering last 90 days (or `export` if history is thin). Also `calendar` for gaps. Also `exercises` for name list.
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

`context`, `stats`, `calendar`, `session`, `range`, and `history <exercise>` give ground truth numbers. Gym mode reasons from `context` only. Review mode may pull hundreds of sessions at once with `range` or `notes`, that output feeds agent reasoning for chat answers and postplan docs, it is never shown raw. Then add your own read on top: trend, e1RM direction, volume per muscle, 3 on 1 off adherence from `calendar` dates and gaps (raw dates in, verdict out, travel and sick notes from memory decide miss versus planned rest), PRs, stalls, caveats (small sample, pain notes, missed sessions). Keep it short and honest. Numbers first, take second.

Volume is anatomical by muscle group, and one set can count for several groups at once. Tracked groups live in MEMORY.md under Tracked muscles (currently chest, back, shoulders, biceps, triceps, quads, hamstrings, glutes, abs; never neck, calves, forearms, traps). Per lift attribution lives in Lift mapping. If a new movement maps to an untracked group or no clear group, ask once whether to track it, then follow the answer.

Never present tonnage or total set counts as achievements, in chat or on the dashboard. Totals like that mean nothing about progress. Trends, PRs, and adherence are the currency. A PR is any set beating the prior best e1RM for that lift. The first logged set per lift is the baseline, not a PR.

## Dashboard iteration

The dashboard is malleable, not finished. Change it freely whenever the user asks, taste included. It lives in `dashboard/src/` (10 modular files: index.ts, html.ts, utils.ts, charts.ts, liftChart.ts, miniChart.ts, bwChart.ts, stackedChart.ts, date.ts, tip.ts) and deploys with `wrangler deploy` from `dashboard/` (auth via CLOUDFLARE_API_TOKEN read from `~/.config/reps/cf_token` plus the account id, both already on this machine). Verify live with curl on `/snapshot` and the root page after every deploy.

Every UI change gets verified with dark screenshots before reporting done: phone width plus desktop width, checking the changed view. Harness is `node shot.js` in `~/.shot/` (playwright-core driving the cached chrome-headless-shell with dark emulation). No unit tests for the dashboard file yet, screenshots are the test.

Conventions: keep charts honest (e1RM is weight times 1 plus reps over 30), keep the snapshot schema forward compatible (the worker ignores unknown fields, so the CLI can add new sections without breaking the page). Each set carries its own muscle list, the volume chart reads it directly and one set can credit several groups. The worker muscleOf patterns stay only as fallback for sets logged before attribution existed, and mirror MEMORY.md Tracked muscles. Lifts matching nothing are left out entirely. The trend section is small multiples, one mini chart per lift on its own scale with PR trophies and tap-through to the lift page, visibility follows toggle chips (top 8 on by default, All and None buttons, picks persist), palette holds 24 colors. Zero weight sets are excluded from trend lines. Session tables use real thead and tbody. Saved legend prefs prune names missing from the snapshot on load. Never use backslash escapes in dashboard/src/\*, the deploy pipeline strips them and silently breaks the page. Prefer graphs over headline numbers. PR marker is the trophy icon everywhere (session tables, calendar corner, lift chart canvas), never dots, rings, stars, or pills.

## Dashboard sync

`sync` pushes the full export plus bodyweight to https://reps.bojan-dev.workers.dev/ where the hosted dashboard reads it. Auth lives in `~/.config/reps/config.json`, never in the repo. Local SQLite stays the source of truth, and it is tracked in git: commit and push it after every sync. Test CLI flows with `REPS_DB` pointed at /tmp, never the real db. A poisoned session is reverted with `git checkout` on the db, no manual surgery. If a push ever conflicts (two sessions writing at once), pull first, then push.
