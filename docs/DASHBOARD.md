# Dashboard

Dashboard code, deploys, and sync. Only for dashboard work. Training protocol lives in `LOGGING.md` and `PROGRAMMING.md` (same folder). Paths below are repo-root relative.

## Iteration

The dashboard is malleable, not finished. Change it freely whenever the user asks, taste included. It lives in `dashboard/` and deploys with `npm run deploy` from `dashboard/`. Verify live with curl on `/snapshot` and the root page after every deploy.

Every UI change gets verified before reporting done: `pre-commit run --all-files`, then `npx playwright test` from `dashboard/`, phone width plus desktop width, checking the changed view.

Architecture (details in `ARCHITECTURE.md`): Svelte 5 pages and components render a validated snapshot. Server state flows through TanStack Query (`snapshot` query key); remote JSON is runtime-validated by Zod schemas at the boundary, never `any` into the app. Chart math (scales, extents, ticks) uses D3 primitives; canvas rendering stays bespoke Reps code. Data helpers live in query/data modules, formatting in presentation helpers, never inside components.

Conventions: keep charts honest (e1RM is weight times 1 plus reps over 30, except a true single whose e1RM is the weight itself), keep the snapshot schema forward compatible (the worker ignores unknown fields, so the backend can add new sections via `reps/sync.py` without breaking the page). Each set carries its own muscle list, the volume chart reads it directly and one set can credit several groups. There is no name-pattern fallback anywhere: unmapped lifts are left out entirely until the agent maps them via `muscle_map_set`. The trend section is small multiples, one mini chart per lift on its own scale with tap-through to the lift page, visibility follows toggle chips (top 8 on by default, All and None buttons, picks persist), palette holds 24 colors. Charts carry no PR markers, a new high on the line is the PR; the trophy icon marks PR days on the calendar, PR sets in session tables, and PR-this-month on movement cards only. The calendar marks missed rotation days distinctly from rest and untracked days (hollow red ring, from the snapshot's `adherence` section; nothing renders when no anchor is set). List pages (`#/lifts`, `#/muscles`) follow the trend-grid pattern: small multiples, filter chips, tap-through to the full page. New snapshot fields must stay null-safe: the worker serves the last synced payload, which can predate them. Zero weight sets are excluded from trend lines. Session tables use real thead and tbody. Saved legend prefs prune names missing from the snapshot on load. Never use backslash escapes in dashboard/src/*. `src/worker.ts` is the Worker entry and must stay DOM free, enforced by `src/__tests__/worker.smoke.test.ts`. `src/index.ts` is browser only. Prefer graphs over headline numbers. Never use pills anywhere in dashboard UI, state reads as plain text (bold titles, muted lines).

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
