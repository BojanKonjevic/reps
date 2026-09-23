# Architecture

Where things belong and what owns what. Read before changing code structure or adding a feature. `AGENTS.md` stays the map; this is the longer form.

## Layers

```text
                          AGENT
                            │
                           MCP
                            │
                ┌───────────┴───────────┐
                │                       │
         agent documentation       MCP schemas/tools
         "when / why"              "how / what"
                │                       │
                └───────────┬───────────┘
                            ▼
                     Reps Domain Core
                     /      |       \
                    /       |        \
                 SQLite   models     tests
                            │
                         Pydantic
                            │
                     serialized state
                            │
                            ▼
                     Cloudflare Worker
                            │
                         snapshot
                            │
                     TanStack Query
                            │
                           Zod
                            │
                         Svelte 5
                       /    │     \
                  pages  components  charts
                                        │
                                   D3 primitives
                                        │
                                     Canvas
```

- SQLite owns durable facts and state. Explicit SQL, no ORM. Derivable values are computed on read, never stored redundantly.
- `reps/` owns deterministic business logic and enforced invariants, behind plain functions. One module per domain: `sessions`, `program`, `plan`, `goals`, `autoreg`, `adherence`, `signals`, `audit`, `sync`, plus `db`, `constants`, `muscles`, `memory`, `progression`.
- `reps/models.py` owns structural validation (Pydantic): `ConstantsModel` for constants.json, `SnapshotModel` for the published payload. Domain and business rules stay out; they live in the domain modules.
- `reps/mcp/` is the sole normal agent interface: thin tools calling domain operations directly. No business logic in handlers, no shell command language anywhere.
- `docs/` owns protocol and reasoning rules: when a capability is used, how capabilities sequence, domain concepts, safety requirements.
- The dashboard presents backend state. It never reconstructs domain semantics that belong in Python.
- The agent owns judgment and conversational reasoning, grounded in numbers pulled through MCP.

## Module homes

- Svelte pages and views: `dashboard/src/pages/` (one per route). Independently understandable; UI state lives in the component model, not global mutable DOM state.
- Reusable UI components: `dashboard/src/components/`. Canvas components share the lifecycle in `dashboard/src/lib/canvas.ts`; hover and tooltip bodies stay per chart. Bespoke styling stays; this is not a component-library app.
- Server state: `dashboard/src/queries/` (TanStack Query query functions, `snapshot` query key, invalidation and refetch instead of bespoke refresh). The snapshot is published state, not live data: no window-focus refetch, no realtime transport. Updates arrive through `sync_push`, the query only reads.
- Data and domain math for the dashboard: `dashboard/src/lib/dashboard.ts` (derived view models), plus the long-standing source modules at `dashboard/src/` root (`forward.ts`, `prs.ts`, `utils.ts`, `date.ts`, `charts.ts` and the chart renderers). New cross-cutting helpers go in `lib/`; do not re-home the root modules their tests import.
- Runtime schemas: `dashboard/src/schemas/` (Zod; inferred types flow into components, no redundant interfaces). Zod models what the dashboard can render: core facts strict, stale-tolerant sections partial, matching the dashboard's null-safe reads. Python validates strictly before publication.
- Formatting and presentation helpers: `dashboard/src/lib/` alongside chart math.
- Charting: D3 (`d3-scale`, `d3-array`) for scales, domains, extents, ticks; Reps owns canvas rendering, PR and goal visuals, hit testing, tooltips, styling.
- MCP tools: `reps/mcp/server.py`, one thin function per domain operation, sharing the `run_domain` adapter. New capability means a domain function first, then a tool.
- Tests: backend invariants in `tests/` (pytest), dashboard unit in `dashboard/src/__tests__/` (vitest), e2e in `dashboard/e2e/` (playwright). MCP tools are tested through the MCP interface (`call_tool`/`list_tool_names`), not just via the domain functions underneath.

## Validation boundaries

| Crossing | Enforced by | Fails as |
|---|---|---|
| constants.json into Python | `ConstantsModel` (`reps/models.py`) | loud exit naming file, location, reason |
| domain into snapshot | `SnapshotModel` via `build_snapshot_validated` | `SnapshotValidationError`, publish refused |
| remote JSON into TypeScript | Zod `snapshot` schema | explicit parse failure, no `any` downstream |
| agent into domain | MCP tool input schemas | typed refusal `{"ok": false, "error"}` |

Internal module boundaries use ordinary Python/TypeScript types, not unstructured dicts, wherever practical. Unknown snapshot fields stay tolerated (forward compatibility); known fields and shapes are strict.

## What not to bypass or rebuild

- Do not add business logic to MCP handlers, the Worker, or the frontend. Domain questions get answered in `reps/`, exposed through MCP, presented by the dashboard.
- Do not add a second agent interface: no CLI framework (Click, Typer, argparse wrappers), no textual RPC, no generic execute-command or run-arbitrary-SQL tool. `log.py` stays four maintenance ops (doctor, dump, restore, export) for local recovery.
- Do not replace explicit SQL with an ORM query builder, and do not replace the canvas renderer with a full charting framework.
- Do not duplicate MCP tool schemas in prose docs. Docs teach when and why; MCP declares how and what.
