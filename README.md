# reps

Chat first training log. You talk, the agent stores every set in local SQLite via `log.py`.

## Why this exists

Most training logs make you pick. Either a rigid tracker that stores every set perfectly and understands nothing, or a chatbot coach that talks well and remembers nothing.

reps does both at once. You talk the way you'd text a training partner. "Squat 90 5/5/7, last to failure" between sets, questions when you have them, done at the end. Underneath, every set lands in SQLite with exact weight, reps, muscles, and notes, and the same agent that logs also coaches: rep targets from your history, progression that adjusts when you miss, goals with session-by-session trajectories.

The combination is the point. Facts alone can't tell you what to do next, and agent reasoning left to itself drifts, misremembers, and invents. So the reasoning here runs on rails. Code owns what is derivable or enforceable (volume landmarks, thresholds, the close gate), the database owns judgment state (program, progression, goals, rules), the markdown holds protocol and reasons, and every claim has to ground out in stored sets. You get the judgment without the failure mode that usually comes with it.

The split is deliberate. The database holds facts and state, `constants.json` holds the numbers, the markdown holds the protocol, the agent does the thinking, and you just train and talk.

## How a session looks

You open a chat with an agent that has terminal access and say you're training. I run it in t3code, but any environment where the agent can execute `log.py` locally works. The agent figures out which slot is up, tells you what to hit, and you send sets as you go. "Squat 90 5/5/7, last to failure" is enough, it fans out into three logged sets. Ask questions between sets, say done at the end, and you get a short report plus a synced dashboard.

You never touch the CLI yourself. The commands are the agent's vocabulary, not yours. That is the whole idea: zero logging friction, full data underneath.

## How it works

Three layers, each doing one job.

**The database holds facts.** `log.py` (entry point for the `reps/` package: `sessions`, `program`, `plan`, `goals`, `autoreg`, `audit`, `sync`, `cli`) stores workouts, sets with weight, reps, muscles and notes, bodyweight, plus program state: splits, mappings, progression, flags, priorities, deloads, rules, goals. Derivable numbers (ledger, volume, e1RM, slot guess) are computed on read by `plan`, never stored. Non-negotiable rules fail loudly at the point of violation (the `end` gate, mapping authority, loud `constants.json`). The binary stays gitignored. A `workouts.sql` text dump is committed instead, so history reads as clean diffs and doubles as the backup.

**The markdown holds the rules.** AGENTS.md is the map: `docs/LOGGING.md` runs sessions, `docs/PROGRAMMING.md` designs the program, `docs/DASHBOARD.md` owns the frontend. `docs/MEMORY.md` carries your state, the program and goals live in SQLite behind `split`/`map`/`rule`/`goal` commands. `docs/SCIENCE.md` pins the evidence-based defaults. This is what keeps the agent honest.

**The dashboard shows it back.** `log.py sync` pushes a snapshot to a read-only Cloudflare Worker. Graphs over headline numbers: e1RM trends per lift, volume by muscle, calendar, PRs.

## Repo map

- `log.py`, the CLI entry point and only writer (implementation in `reps/`, one module per domain). SQLite at `workouts.db`, tracked dump at `workouts.sql`.
- `reps/`, the backend: `sessions` (logging, the `end` gate), `program` (splits, rules, flags, priorities, deloads), `plan` (the `plan` bundle), `goals`, `autoreg`, `audit` (`audit`, `doctor`), `sync` (`sync`, `dump`, `restore`, `export`), `cli` (argv parsing), plus `db`, `constants`, `muscles`, `memory`, `progression`.
- `docs/`, protocol and state: `LOGGING.md` (sessions), `PROGRAMMING.md` (program design), `DASHBOARD.md` (frontend), `SCIENCE.md` (evidence), `AUDIT.md` (data quality), `ISSUES.md` (issue log), `MEMORY.md` (training state).
- `AGENTS.md`, the agent map. `constants.json`, the evidence numbers.
- `dashboard/`, the Cloudflare Worker frontend, live at https://reps.bojan-dev.workers.dev.
- `tests/`, the deterministic pytest suite for everything the backend enforces.

## Backup and recovery

Every session ends with a `data: <date>` commit of `workouts.sql`. If the local database ever gets corrupted, `log.py restore` rebuilds it from the dump. The commit history is the undo button.

## Tests

Python: `uv run --with pytest --no-project pytest tests/ -q` (system python has no pytest, never `python -m pytest` directly). Dashboard: `npm run test` for unit, `npx playwright test` for e2e, from `dashboard/`.
