# reps

Chat first workout log. The agent owns meaning, `log.py` only stores.

## Session start

Fresh agents have no chat memory, so rebuild it from files first:

1. Read `MEMORY.md`. Active rules there beat default mappings and beat raw history.
2. Check dates: compare today against every rule expiry plus the Needs confirm section. If a rule expired since last session or expires within 7 days, ask once before logging anything it affects (example: incline block ended Nov 1 and user still logs incline, ask to extend or close). Move expired rules to Needs confirm, never delete silently.
3. Run `context` (last 3 workouts plus per lift last and best). That is your working memory, enough for most sessions.
4. Only drill down with `history <exercise>` or `today` when the question needs it. Never load full `export` into chat, it is for the dashboard file only.

Core principle: a wrong log poisons every future analysis, a question costs nothing. When unsure about exercise, weight, reps, or which rule applies, ask first or verify with a query. Never guess into the db.

## How to log

1. On any training message, run `today` to see if a workout is open.
2. If none open and user is training, run `start`.
3. Before logging a set, check the `context` lifts list for canonical names. Reuse an existing name when it clearly matches.
4. Log with: `log <exercise> <weight> <reps>` plus free note text.
5. RPE is not tracked. Never ask for it, never log it. Feel goes in plain words in the note instead.
6. Morning weight goes with `weigh <kg>` plus optional note, for example `weigh 84.2 fasted`. One entry per day is enough, latest wins on the chart.
7. On `done`, `finished`, or clear end of session, run `end` with a short session summary (feel, sleep, pain, what moved well). That note is how future sessions remember the qualitative side. Then run `sync` to push the dashboard.

Units are kg unless user says otherwise. Never invent sets. If a message is ambiguous, hold the log and ask. Partial logging is allowed only when the clear part is unambiguous, the unclear part waits for an answer.

## Naming

You own the ontology. There is no alias list in code.

1. Normalize to lowercase training names, for example `flat barbell bench press`, `back squat`, `overhead press`.
2. Known shorthands: `ohp` means overhead press, `bench` means flat barbell bench press unless MEMORY.md or context says otherwise (for example an active incline block), `squat` means back squat unless context says front or split.
3. `same` or `again` refers to the last exercise in the open workout.
4. If user names something new that has no close match, ask once, then reuse that spelling forever.
5. If duplicates happen, merge with `rename <old> <new>`.

## Memory writeback

Chat history dies with the session, files survive. When user states something durable, write it down:

1. Prefs and plans (`always incline, never flat`, `incline block until November`, injury notes) go to `MEMORY.md` under Active rules with start date and expiry. Expired rules move to Needs confirm and get asked about once, then reactivated with a new date or archived. Nothing durable is ever deleted without an answer.
2. Session feel and life context go to workout notes via `end`. Set level notes go on the set.
3. At month end on request, append a short rollup to `MEMORY.md` under Monthly rollups: trend plus caveats in a few lines. Raw sets stay in SQLite, never paste them into memory files.

Keep `MEMORY.md` short. Current state only, dated lines, no essays.

## Analysis

`context`, `stats`, and `history <exercise>` give ground truth numbers. Do the math from those, then add your own read on top: trend, e1RM direction, volume per muscle, 3 on 1 off adherence, PRs, stalls, caveats (small sample, grindy notes, missed sessions). Keep it short and honest. Numbers first, take second.

Never present tonnage or total set counts as achievements, in chat or on the dashboard. Totals like that mean nothing about progress. Trends, PRs, and adherence are the currency. A PR is any set beating the prior best e1RM for that lift. The first logged set per lift is the baseline, not a PR.

## Dashboard iteration

The dashboard is malleable, not finished. Change it freely whenever the user asks, taste included. It lives in one file, `dashboard/src/index.ts`, and deploys with `wrangler deploy` from `dashboard/` (auth via CLOUDFLARE_API_TOKEN read from `~/.config/reps/cf_token` plus the account id, both already on this machine). Verify live with curl on `/snapshot` and the root page after every deploy.

Conventions: keep everything in the single file, keep charts honest (e1RM is weight times 1 plus reps over 30), keep the snapshot schema forward compatible (the worker ignores unknown fields, so the CLI can add new sections without breaking the page). Muscle groups for the volume chart live in the worker muscleOf patterns, lifts that match nothing are left out entirely, extend the patterns when the split changes. Never use backslash escapes in dashboard/src/index.ts, the deploy pipeline strips them and silently breaks the page. Prefer graphs over headline numbers.

## Dashboard sync

`sync` pushes the full export plus bodyweight to https://reps.bojan-dev.workers.dev/ where the hosted dashboard reads it. Auth lives in `~/.config/reps/config.json`, never in the repo. Local SQLite stays the source of truth. Sync after every session close and every weigh in that matters.
