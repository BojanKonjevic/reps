# Dashboard protocol

Practical guide for coding agents adding training information to the dashboard. The rule underneath: the project converges on a small number of strong patterns, never one-off UI solutions.

## Canonical process

```text
Need new training information
        ↓
Find domain owner
        ↓
Reuse/create semantic observation
        ↓
Expose through dashboard read model
        ↓
Validate transport
        ↓
Enhance existing chart/page
        ↓
Add shared interaction if reusable
        ↓
Test desktop + mobile
        ↓
Update documentation
```

1. **Find domain owner.** Read `docs/SSOT.md` and `docs/ARCHITECTURE.md`. The fact you need (a formula, a state, a history) already has an owning module under `reps/`, or it needs exactly one owner created there. Never compute it in TypeScript, the Worker, or MCP handlers.
2. **Reuse/create semantic observation.** If `reps/observations.py` has a metric for it, use it. A genuinely new metric means one enum value in `reps/vocab.py`, one computation in `reps/observations.py`, one definition entry for provenance, and pytest coverage with literal oracles. A metric needing required parameters beyond subject and range gets its own tool, not a stretched signature.
3. **Expose through dashboard read model.** Add the view to `reps/snapshot.py` and the shape to `reps/models.py`, then run `scripts/gen.py` so Zod, fixtures, schemas, and doc markers refresh. History-like state goes through `reps/history.py` folds (`training_state_at`), never frontend reconstruction. Unknown stays unknown with coverage dates.
4. **Validate transport.** `build_snapshot_validated` must pass; the Worker serves the payload verbatim and gains no domain logic.
5. **Enhance existing chart/page.** New page only when no existing view can represent the information. Annotate with `EventStrip`, detail with `ChangeDetail`, historical state with `TrainingState`, definitions with `Provenance`, selection state with `createEventSelection`, relevance with `dashboard/src/lib/temporal.ts`.
6. **Add shared interaction if reusable.** A third copy of a pattern means the pattern belongs in `dashboard/src/components/` or `dashboard/src/lib/`, documented here.
7. **Test desktop + mobile.** Unit (`dashboard/src/__tests__/`), browser (`dashboard/e2e/`, both projects), no horizontal scroll.
8. **Update documentation.** `docs/DASHBOARD.md` for behavior, `docs/SSOT.md` register for new owners.

## Worked example: rest-day quality score

The user asks for a "recovery score" on the dashboard. Do not build a score card with a frontend formula.

1. Owner: recovery semantics belong in a domain module (say `reps/signals.py` if it derives from existing facts, or a new module registered in `docs/SSOT.md`).
2. Observation: add a `recovery_summary` metric only if it fits subject plus range; otherwise expose a plain domain function and a snapshot view. Either way the definition string lives in Python and the dashboard renders it through `Provenance`.
3. Read model: view builder in `reps/snapshot.py`, model in `reps/models.py`, `scripts/gen.py`, pytest with literal oracles (a stated input week yields a stated score).
4. Transport: snapshot validates, Worker untouched.
5. UI: enhance the consistency section (a marker on low weeks, detail inline), not a new page. Reuse `EventStrip` if the score has history behind it.
6. Shared: nothing new unless a second chart needs the same interaction.
7. Tests: unit for selection/formatting, e2e for desktop plus mobile, history unknown-states where applicable.
8. Docs: behavior in `docs/DASHBOARD.md`, owner row in `docs/SSOT.md`.

If any step tempts a shortcut (a TS helper "just for this page", a Worker computation, a second definition), stop: that is the defect `docs/SSOT.md` describes.

## Deliberate deviations

The spec behind temporal context allows documented judgment over mechanical
compliance. These deviations shipped with the initial implementation:

1. **As-of offers Today plus recorded event dates, not an arbitrary date
   picker.** The frontend never folds history chains, so only backend-folded
   dates are selectable. A free picker would invite invented states.
2. **Goal trajectory history reads as text, not a chart overlay.** Past and
   current trajectories have different session counts and cannot share the
   session-numbered axis honestly. The envelopes stay immutable and visible.
3. **One snapshot, not range queries.** History plus folded states ride the
   monolithic snapshot. The data is small, coherence beats cleverness, and
   TanStack caches it. Split only when measured payloads demand it.
4. **Rotation and anchor events stay global.** They appear on adherence,
   program, and history surfaces, not on every lift and muscle chart, where
   they would be noise rather than explanation.
5. **Event lane layout is a flat strip, not per-domain lanes.** One wrapped
   row of date-grouped buttons plus subordinate canvas ticks carries the
   temporal relationship without turning charts into timelines. Revisit if
   dense histories prove unreadable.
6. **Snapshot display strings render verbatim.** Titles and summaries are a
   read-model projection in `reps/snapshot.py`, not a second definition: one
   builder, every chart formats the same change the same way.
