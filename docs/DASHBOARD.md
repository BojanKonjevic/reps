# Dashboard

Dashboard code, deploys, and sync. Only for dashboard work. Training protocol lives in `LOGGING.md` and `PROGRAMMING.md` (same folder). Paths below are repo-root relative.

## Iteration

The dashboard is malleable, not finished. Change it freely whenever the user asks, taste included. It lives in `dashboard/` and deploys with `pnpm --dir dashboard run deploy`. Verify live with curl on `/snapshot` and the root page after every deploy.

Every UI change gets verified before reporting done: `scripts/verify.sh`, then `pnpm --dir dashboard exec playwright test`, phone width plus desktop width, checking the changed view.

Architecture (details in `ARCHITECTURE.md`): Svelte 5 pages and components render a validated snapshot. Server state flows through TanStack Query (`snapshot` query key); remote JSON is runtime-validated by Zod schemas at the boundary, never `any` into the app. Chart math (scales, extents, ticks) uses D3 primitives; canvas rendering stays bespoke Reps code. Data helpers live in query/data modules, formatting in presentation helpers, never inside components.

Conventions: keep charts honest (e1RM is defined in `reps/e1rm.py` and emitted per set and per session, the dashboard never computes it), keep the snapshot schema strict (Python validates every field, the worker rejects wrong versions, the dashboard shows resync needed on mismatch). Sets are embedded once inside `sessions`, muscle facts arrive in `lifts`, `muscles`, and `volume_history` views, and one set can credit several groups. There is no name-pattern fallback anywhere: unmapped lifts are left out entirely until the agent maps them via `muscle_map_set`. The trend section is small multiples, one mini chart per lift on its own scale with tap-through to the lift page, visibility follows toggle chips (the snapshot `trend_top_lifts` cutoff on by default, All and None buttons, picks persist), palette holds 24 colors. Charts carry no PR markers, a new high on the line is the PR; the trophy icon marks PR days on the calendar, PR sets in session tables, and PR-this-month on movement cards only. The calendar marks missed rotation days distinctly from rest and untracked days (hollow red ring, from the snapshot's `adherence` section; nothing renders when no anchor is set). List pages (`#/lifts`, `#/muscles`) follow the trend-grid pattern: small multiples, filter chips, tap-through to the full page. New snapshot fields fail the build until generated code is refreshed (`scripts/gen.py --check` in CI). Zero weight sets are excluded from trend lines. Session tables use real thead and tbody. Saved legend prefs prune names missing from the snapshot on load. Never use backslash escapes in dashboard/src/*. `src/worker.ts` is the Worker entry and must stay DOM free, enforced by `src/__tests__/worker.smoke.test.ts`. `src/index.ts` is browser only. Prefer graphs over headline numbers. Never use pills anywhere in dashboard UI, state reads as plain text (bold titles, muted lines).

## Sync

`sync_push` publishes the full validated export plus bodyweight to https://reps.bojan-dev.workers.dev/ where the hosted dashboard reads it. The payload is validated against `reps/models.py` before publication; the dashboard validates it again with Zod on receipt. Auth lives in `~/.config/reps/config.json`, never in the repo. Local SQLite stays the source of truth. The `workouts.db` binary is gitignored; instead `sync_push` dumps a text SQL dump (`workouts.sql`) which is committed to git. This gives clean diffs and readable history. `maintenance_dump` re-writes `workouts.sql` from the live DB without syncing, used by `doctor`'s dump_drift fix.

Recovery: if `workouts.db` is corrupted or poisoned, do not `git checkout workouts.db` (it is ignored). Instead:

```
git checkout workouts.sql
rm -f workouts.db
sqlite3 workouts.db < workouts.sql
```

Or run `maintenance_restore` which does this automatically.

Test backend flows with `REPS_DB` pointed at /tmp, never the real db. Deterministic checks live in `tests/`; `doctor` validates constants, DB, dashboard, and dump consistency and runs in pre-commit. If a push ever conflicts (two sessions writing at once), pull first, then push. `sync_push` enforces this server side with ETags: it pulls the snapshot ETag first and pushes with If-Match, a stale base gets a 412 and aborts instead of overwriting. Reconcile, then `sync_push` with force true to overwrite deliberately.

## Temporal context

Existing charts should be enhanced before creating new analytics surfaces.

The dashboard consumes semantic observations; it does not recreate domain meaning.

Charts stay primary. History appears as subordinate ticks on lift and muscle canvases (`drawEventTicks` in `dashboard/src/charts.ts`, the single canvas primitive; geometry per chart module via `layoutOf`), with one accessible HTML companion strip per chart (`EventStrip`). Selecting an event opens the shared `ChangeDetail` inline (title, date, before/after envelopes, evidence, reversal links), never a modal and never raw JSON. "View training state on {date}" opens the shared `TrainingState` panel: the backend-folded bundle for that date (`history_states`), with a compare-with-today toggle that shows only materially changed fields. The As-of control offers Today (default, the charts themselves) plus recorded event dates; there is no free date picker because the frontend never folds history chains, it only selects backend-folded states. Unknown stays unknown: unrecorded sections read "Historical state unavailable before {date}." (priority defaults read "maintain (default)" until recorded, per the backend rule that absence means maintain).

Relevance lives in one place (`dashboard/src/lib/temporal.ts`): lift pages show goal/program/priority/deload events touching the lift, muscle pages show priority/program/goal/deload events touching the muscle, rotation and anchor events stay global (adherence context, program page, history page) so no chart collects every event. Selection state is shared too (`dashboard/src/lib/eventSelection.svelte.ts`).

Home has a compact What changed section (five newest events, inline detail). `#/history` is the only dedicated history surface: chronological list with domain and date-range filters, reusing the same detail and state components. Goal cards and lift pages keep trajectory history as text (before target, after target), so a rewrite never rewrites the past; the session-numbered goal canvas carries no overlay because trajectories of different lengths cannot share that axis honestly. Bodyweight points open nearby training changes (±7 days, no causality claims). Consistency days open expected/actual/classification plus nearby rotation context. Every chart card carries a Provenance disclosure rendering the backend-owned observation definition and sources verbatim (`observation_defs`, owned by `reps/observations.py`).

Read model: `reps/snapshot.py` `history_view` embeds described events (title, summary, `affects_*` hints built with the sanctioned `parse_movements` reader), one `training_state_at` bundle per event date (folded by `reps/history.py`), coverage dates, and observation defs. The Worker stays transport-only and serves the snapshot verbatim. Snapshot views are the materialized observations: lift sessions are the lift_trend metric, weekly volume is the muscle_volume metric, goal actuals plus checkpoints are the goal_trajectory metric, adherence days are the adherence_summary metric, weigh-ins are the bodyweight_trend metric. Adding a metric means a domain computation plus one observation def, never a frontend formula.

Responsive: strips wrap, before/after columns stack under 900px, grid children carry `min-width: 0`, state reads as plain text. Phone and desktop layouts are covered by `dashboard/e2e/history.spec.ts` (event appears, selection, detail, as-of, unknown history, history page, no horizontal scroll).
