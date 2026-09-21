# AUDIT.md

Data quality audit protocol. Trigger: "audit the data" (distinct from "audit the research" which refreshes SCIENCE.md).

**Limitation**: this is a correlated check, not an independent one. The same reasoning that could produce a bad log is doing the checking. Do not over-trust a clean result. It complements the pytest layer; it does not replace it.

Run every check against actual pulled data (`context`, `history`, `range`, `calendar`). Every flagged item must cite specific rows/dates/ids. Output format: report only — list of flagged items with cited evidence, severity (high/medium/low), one-line suggested fix. Never auto-correct.

After run: log one line in MEMORY.md under State: `YYYY-MM-DD: audit ran, N flags (X high, Y medium, Z low)`.

## Checklist

### 1. Exercise name duplicates

- Pull `exercises` list. Flag near-identical names (Levenshtein ≤ 2, or same root + suffix like "bench" vs "bench press", singular/plural, obvious typos).
- Evidence: the two names and their set counts.
- Fix: `rename <old> <new>`.

### 2. Missing muscle tags — impossible

Enforced at log time (new exercises require `muscles=`, known ones inherit the mapping) and at `end` (gate precondition 2). No manual pass.

### 3. Muscle mapping drift — impossible

The mapping table is authoritative: per-set overrides are refused at log time and `update <id> muscles` no longer exists. No manual pass.

### 4. Implausible progression jumps

- For each exercise in `history` (recent 30 sets), compute session-to-session e1RM change. The deterministic `audit` command flags jumps above a rep-band bound read off the current session best's reps: 4% at 1-6 reps, 5% at 7-10, 8% at 11-15. Above 15 reps e1RM is informational only and never flags. Drops over 50% flag as `progression_drop` (medium) by the same rule. A +1 rep gain is always 2.2%+ e1RM, so flat science-rate bounds would flag every routine rep PR. Skips jumps where set or workout notes on either session explain them (keywords: deload, return, program change, injury, technique, sick, travel).
- The agent's manual pass may apply the finer per-type bounds (novice compound 2%/session, intermediate 1%, advanced 0.5%, isolation 1.5%) on top.
- Evidence: set ids, dates, weights, reps, e1RM before/after, % jump, bound used.
- Fix: verify data entry, add explanatory note, or `update` weight/reps.

### 5. Goal trajectory divergence

- Deterministic since Phase 4: `audit` computes this from the goals tables (same code as `goal show`). Manual pass only double-checks the numbers. For each active goal: logged top-set e1RM per session (last pre-goal date anchors session 1) against trajectory checkpoints. Flags `goal_divergence` if ≥ 2 consecutive sessions fall short by > 5% e1RM (one-sided, overperformance never misses) with no slippage/extend/compress note, `goal_slippage` if remaining sessions no longer fit before the deadline at split frequency. Sessions whose set or workout notes contain "deload" are excluded from the miss count (a deload session deliberately deviates; its trajectory resumes after, never compressed).
- Evidence: goal target, trajectory sessions vs logged sessions, divergence %.
- Fix: `goal rewrite <id>`, or add slippage decision.

### 6. Unreconciled split slots — impossible

Enforced by the `end` gate (precondition 4): a session with an exercise missing from every active split day cannot close without `split reconcile`. No manual pass.

### 7. Stale open workouts

- Run `today`. If open workout exists with `age_days ≥ 1` or `last_set_created` gap > 8h, and it appears in `calendar`/`stats`/`export` counts.
- Evidence: workout id, date, age_days, last_set_created.
- Fix: `end` with note, or `delete-workout` if empty.

### 8. Volume vs MEV (rolling 8-week window)

Backstop for the live plan-time volume check (LOGGING.md Session start step 8), not the primary mechanism. The live check covers every tracked muscle each session and nudges volume conversationally; this deterministic check runs the same computation on a different code path and catches anything the live check misses (a bug in the live logic, a session logged outside the normal chat flow, manual DB edits). Expected to rarely fire on a well-planned block; when it does, treat it as a signal the live check failed, not just that volume is low.

- For each tracked muscle in `constants.json`: compute weekly sets for each of the last 8 weeks (current week + 7 back) from `range`. Weeks with no logged sets count as 0, not as absent. Two separate flags, counted over the whole window (a good week in between does not reset the count):
  - `volume_zero` (high): 0 sets in ≥ 4 of the last 8 weeks.
  - `volume_low` (medium): 0 < sets < MEV in ≥ 4 of the last 8 weeks.
- MEV comes from `constants.json`. Flags with no Active rule in MEMORY.md explaining intentional reduction (injury, deload block, specialization) stand; explained ones are still listed, not silently dropped. A `deload completed` line in State explains a deload week's dip the same way. A muscle marked `deprioritize` in the priority table is still listed but one severity level lower with the reason annotated (the deterministic `audit` command does this automatically; the manual pass must do the same).
- Evidence: muscle, bad-week count out of 8, per-week set counts, MEV.
- Fix: add volume, or add Active rule explaining.

---

Severity guide:

- High: data loss risk (stale workout counted), goal silently broken, implausible jump with no note.
- Medium: volume below MEV.
- Low: near-duplicate exercise names, minor trajectory miss.
- A muscle marked `deprioritize` in the priority table flags one tier lower than the above implies (`volume_zero` medium, `volume_low` low).
