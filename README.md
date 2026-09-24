# reps

Single source of truth is documented in `docs/SSOT.md`: every fact has exactly one owner.

Chat first training log. You talk, the agent stores every set in local SQLite through MCP tools.

## Why this exists

Most training logs make you pick. Either a rigid tracker that stores every set perfectly and understands nothing, or a chatbot coach that talks well and remembers nothing.

reps does both at once. You talk the way you'd text a training partner. "Squat 90 5/5/7, last to failure" between sets, questions when you have them, done at the end. Underneath, every set lands in SQLite with exact weight, reps, muscles, and notes, and the same agent that logs also coaches: rep targets from your history, progression that adjusts when you miss, goals with session-by-session trajectories.

The combination is the point. Facts alone can't tell you what to do next, and agent reasoning left to itself drifts, misremembers, and invents. So the reasoning here runs on rails. Code owns what is derivable or enforceable (volume landmarks, thresholds, the close gate), the database owns judgment state (program, progression, goals, rules), the markdown holds protocol and reasons, and every claim has to ground out in stored sets. You get the judgment without the failure mode that usually comes with it.

The split is deliberate. The database holds facts and state, `constants.json` holds the numbers, the markdown holds the protocol, MCP tools carry the calls, the agent does the thinking, and you just train and talk.

## How a session looks

You open a chat with an MCP-capable agent and say you're training. I run it in t3code, but any environment where the agent can reach the Reps MCP server works. The agent figures out which slot is up, tells you what to hit, and you send sets as you go. "Squat 90 5/5/7, last to failure" is enough, it fans out into three logged sets. Ask questions between sets, say done at the end, and you get a short report plus a synced dashboard.

You never touch the machinery yourself. The MCP tools are the agent's vocabulary, not yours. That is the whole idea: zero logging friction, full data underneath.

## How it works

Module ownership lives in `docs/ARCHITECTURE.md`; fact ownership lives in `docs/SSOT.md`. The one-line version:

**The database holds facts.** The `reps/` package (`sessions`, `program`, `plan`, `goals`, `autoreg`, `adherence`, `signals`, `audit`, `sync`, plus `db`, `constants`, `muscles`, `memory`, `progression`, `models`) stores workouts, sets with weight, reps, muscles and notes, bodyweight, plus program state: splits, mappings, progression, flags, priorities, deloads, rules, goals. The agent reaches it through typed MCP tools in `reps/mcp/`, never through a shell command language. Derivable numbers (ledger, volume, e1RM, slot guess) are computed on read by `plan`, never stored. Non-negotiable rules fail loudly at the point of violation (the `end` gate, mapping authority, loud `constants.json`). The binary stays gitignored. A `workouts.sql` text dump is committed instead, so history reads as clean diffs and doubles as the backup.

**The markdown holds the rules.** AGENTS.md is the map: `docs/LOGGING.md` runs sessions, `docs/PROGRAMMING.md` designs the program, `docs/DASHBOARD.md` owns the frontend, `docs/ARCHITECTURE.md` maps the code. `docs/MEMORY.md` carries your state, the program and goals live in SQLite behind MCP tools. `docs/SCIENCE.md` pins the evidence-based defaults. This is what keeps the agent honest.

**The dashboard shows it back.** `sync_push` publishes a validated snapshot to a read-only Cloudflare Worker. Graphs over headline numbers: e1RM trends per lift, volume by muscle, calendar, PRs.

## Repo map

- `reps/`, the backend (module list in `docs/ARCHITECTURE.md`).
- `docs/`, protocol and state: `LOGGING.md` (sessions), `PROGRAMMING.md` (program design), `DASHBOARD.md` (frontend), `ARCHITECTURE.md` (code map), `SCIENCE.md` (evidence), `AUDIT.md` (data quality), `ISSUES.md` (issue log), `MEMORY.md` (training state).
- `AGENTS.md`, the agent map. `constants.json`, the evidence numbers.
- `dashboard/`, the Cloudflare Worker frontend, live at https://reps.bojan-dev.workers.dev.
- `tests/`, the deterministic pytest suite for everything the backend enforces.

## Backup and recovery

Every session ends with a `data: <date>` commit of `workouts.sql`. If the local database ever gets corrupted, `maintenance_restore` rebuilds it from the dump. The commit history is the undo button.

## Tests

Python: `scripts/test-py.sh`. Dashboard needs Node 22 or newer (`engines` in `dashboard/package.json`, same version CI uses): `pnpm --dir dashboard run test` for unit, `pnpm --dir dashboard exec playwright test` for e2e. Full check: `scripts/verify.sh`.
