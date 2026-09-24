# reps

Chat first workout log. Code owns what is derivable or enforceable, the agent owns what is judgment.

Precedence, highest first: Active rules and injuries beat everything; my logged data beats `docs/SCIENCE.md` defaults for my specific lifts; `docs/SCIENCE.md` defaults beat agent instinct. Raw history never overrides an Active rule.

Universal rules, every agent, every session:

- Single source of truth is a hard rule. Before adding any constant, type, enum, formula, color, route, doc number, or fixture, read `docs/SSOT.md` and reuse the existing owner. Never create a second mechanism for something that already has an owner; if you think you must, the justification procedure in `docs/SSOT.md` applies and the answer is almost always no.
- Weights are kg unless I say otherwise. Never invent sets. A wrong log poisons every future analysis, a question costs nothing. When unsure about exercise, weight, reps, or which rule applies, ask first or verify with a query. Never guess into the db.
- Talk stays short and conversational. Numbers first, take second. No generic motivation, no essays.
- Never present tonnage or total set counts as achievements, in chat or on the dashboard. Trends, PRs, and adherence are the currency. A PR is any set beating the prior best e1RM for that lift. The first logged set per lift is the baseline, not a PR.
- Operate Reps through MCP tools. There is no shell command language: no `log.py <command>` syntax exists, and prose must never invent one. `log.py` at the repo root is maintenance only (dump, restore, export, doctor for local recovery), never the agent workflow.

## File map

Protocol and state live in `docs/`, domain logic in `reps/`, the agent interface in `reps/mcp/`:

- `docs/LOGGING.md` — session protocol: starting, logging sets, naming, muscle attribution, closing sessions, memory writeback. The logging agent needs this and nothing else.
- `docs/PROGRAMMING.md` — program design: split, goals and trajectories, prioritize, split review, deload, evidence refreshes. Needed for planning and program changes, not for logging sets.
- `docs/DASHBOARD.md` — dashboard code, deploys, and sync. Only for dashboard work.
- `docs/ARCHITECTURE.md` — layers, module homes, validation boundaries, what owns what. Read before changing code structure or adding a feature.
- `docs/SSOT.md` — ownership register, decision procedure, good and bad examples. Read before any code change.
- `docs/MEMORY.md` — durable judgment state (injuries, sleep, life context, rollups). Short, current only.
- `docs/SCIENCE.md` — evidence reference with trust tiers. Read for defaults, never for what I already logged.
- `constants.json` — single source of truth for muscles, MEV/MAV/MRV, thresholds. Edited via the `constants_set` tool, never by hand.
- `docs/AUDIT.md` — data quality protocol. `docs/ISSUES.md` — agent behavior issue log.
- `reps/` — the domain implementation, one module per domain (module list in `docs/ARCHITECTURE.md`). `reps/mcp/` adapts domain operations into typed MCP tools; handlers stay thin, invariants live in the domain modules. Backend paths (`workouts.db`, `constants.json`, `docs/MEMORY.md`) resolve from the repo root, never the cwd. Rotation schedule state lives in the `rotation` and `rotation_anchor` tables (via `program_rotation_set`); per-date verdicts come from `program_rotation_status` and `plan`'s `adherence`, never from hand-counting dates.

## Triggers

Phrases that switch modes, each documented where it lives:

- "audit the data" — full data quality check, runbook in `docs/AUDIT.md`.
- "audit the research" — refresh the evidence base, process in `docs/PROGRAMMING.md`.
- "review the split" — check the program against the evidence, process in `docs/PROGRAMMING.md`.
- "suggest" — propose goals, flow in `docs/PROGRAMMING.md`.
- "prioritize X" — bring up a muscle, flow in `docs/PROGRAMMING.md`.
- "add a setting / constant / enum / color / route / field" — follow `docs/SSOT.md` decision procedure (A.2).
- Explicit agent complaints ("that's wrong", "log this issue") — append to `docs/ISSUES.md` per its template.

## Reasoning modes

`session_context`, `session_stats`, `session_calendar`, `session_get`, `session_range`, and `session_history` give ground truth numbers. Gym mode reasons from `plan` state, `docs/MEMORY.md`, `session_today`, and the `lifts` array only. Rotation adherence is computed (`plan`'s `adherence`, `program_rotation_status` for ranges); drift asks for a re-anchor, it never re-anchors silently. Review mode may pull hundreds of sessions at once with `session_range` or `session_notes`, that output feeds agent reasoning for chat answers and postplan docs, it is never shown raw. Then add your own read on top: trend, e1RM direction, volume per muscle, PRs, stalls, caveats (small sample, pain notes, missed sessions). Keep it short and honest. Numbers first, take second.

## Development

MCP is the sole normal interface; code changes serve it, never a second one:

- Run the MCP server locally with `python -m reps.mcp` (stdio). Discover capabilities through tool names and their schemas; results carry `ok` plus `data`, refusals carry `ok: false` plus `error`. Never operate Reps through shell commands, and never parse process output.
- New agent-facing capability means a domain function first (in the owning module under `reps/`, returning data and raising `RepsError` on refusal), then a thin tool in `reps/mcp/` calling it directly with a descriptive docstring (`Literal` for closed vocabularies). Never new business logic in the handler and never a shell command.
- Tests for both layers: domain behavior in `tests/` (pytest, direct calls, `pytest.raises(RepsError)` for refusals), MCP exposure in `tests/test_mcp.py` (through `call_tool`/`list_tool_names`). `tests/test_architecture.py` pins the boundaries; keep it passing.
- Domain truth lives in `reps/` behind plain functions, validated by Pydantic models in `reps/models.py`; the dashboard validates the same snapshot with matching schemas on its side. Docs teach when and why to call things, MCP schemas declare what to call with. Details in `docs/ARCHITECTURE.md`.
- Verify with `scripts/verify.sh` (gen check + ssot_check + py tests + dashboard lint/typecheck/unit + doctor). `scripts/test-py.sh` runs the Python suite alone. Dashboard: `pnpm --dir dashboard run test` for unit, `pnpm --dir dashboard exec playwright test` for e2e; deploy with `pnpm --dir dashboard run deploy` after any frontend change and verify live.
- `log.py` stays four maintenance ops (doctor, dump, restore, export). Do not grow it back into an application interface, and do not add Click, Typer, argparse wrappers, or any other command framework.
