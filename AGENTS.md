# reps

Chat first workout log. Code owns what is derivable or enforceable, the agent owns what is judgment.

Precedence, highest first: Active rules and injuries beat everything; my logged data beats SCIENCE.md defaults for my specific lifts; SCIENCE.md defaults beat agent instinct. Raw history never overrides an Active rule.

Universal rules, every agent, every session:

- Weights are kg unless I say otherwise. Never invent sets. A wrong log poisons every future analysis, a question costs nothing. When unsure about exercise, weight, reps, or which rule applies, ask first or verify with a query. Never guess into the db.
- Talk stays short and conversational. Numbers first, take second. No generic motivation, no essays.
- Never present tonnage or total set counts as achievements, in chat or on the dashboard. Trends, PRs, and adherence are the currency. A PR is any set beating the prior best e1RM for that lift. The first logged set per lift is the baseline, not a PR.

## File map

- `LOGGING.md` — session protocol: starting, logging sets, naming, muscle attribution, closing sessions, memory writeback. The logging agent needs this and nothing else.
- `PROGRAMMING.md` — program design: split, goals and trajectories, prioritize, split review, deload, evidence refreshes. Needed for planning and program changes, not for logging sets.
- `DASHBOARD.md` — dashboard code, deploys, and sync. Only for dashboard work.
- `MEMORY.md` — durable judgment state (injuries, sleep, life context, rollups). Short, current only.
- `SCIENCE.md` — evidence reference with trust tiers. Read for defaults, never for what I already logged.
- `constants.json` — single source of truth for muscles, MEV/MAV/MRV, thresholds. Edited via `log.py constants set`, never by hand.
- `AUDIT.md` — data quality protocol. `ISSUES.md` — agent behavior issue log.

## Triggers

Phrases that switch modes, each documented where it lives:

- "audit the data" — full data quality check, runbook in `AUDIT.md`.
- "audit the research" — refresh the evidence base, process in `PROGRAMMING.md`.
- "review the split" — check the program against the evidence, process in `PROGRAMMING.md`.
- "suggest" — propose goals, flow in `PROGRAMMING.md`.
- "prioritize X" — bring up a muscle, flow in `PROGRAMMING.md`.
- Explicit agent complaints ("that's wrong", "log this issue") — append to `ISSUES.md` per its template.

## Reasoning modes

`context`, `stats`, `calendar`, `session`, `range`, and `history <exercise>` give ground truth numbers. Gym mode reasons from `plan` state, `MEMORY.md`, `today`, and the `lifts` array only. Review mode may pull hundreds of sessions at once with `range` or `notes`, that output feeds agent reasoning for chat answers and postplan docs, it is never shown raw. Then add your own read on top: trend, e1RM direction, volume per muscle, rotation adherence from `calendar` dates and gaps (raw dates in, verdict out, explicit `rest: true` dates decide planned rest first, travel and sick notes from memory only break ties on untracked gaps), PRs, stalls, caveats (small sample, pain notes, missed sessions). Keep it short and honest. Numbers first, take second.
