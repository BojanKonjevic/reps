# AUDIT.md

Data quality audit protocol. Trigger: "audit the data" (distinct from "audit the research" which refreshes SCIENCE.md).

**Limitation**: this is a correlated check, not an independent one. The same reasoning that could produce a bad log is doing the checking. Do not over-trust a clean result. It complements the pytest layer; it does not replace it.

Run every check against actual pulled data (`session_context`, `session_history`, `session_range`, `session_calendar`). Every flagged item must cite specific rows/dates/ids. Output format: report only — list of flagged items with cited evidence, severity (high/medium/low), one-line suggested fix. Never auto-correct.

After run: log one line in MEMORY.md under State: `YYYY-MM-DD: audit ran, N flags (X high, Y medium, Z low)`.

## Checklist

### 1. Exercise name duplicates

- Pull `exercises` list. Flag near-identical names (Levenshtein ≤ 2, or same root + suffix like "bench" vs "bench press", singular/plural, obvious typos).
- Evidence: the two names and their set counts.
- Fix: `muscle_rename`.

### 2. Missing muscle tags — impossible

Enforced at log time (new exercises require `muscles`, known ones inherit the mapping) and at `session_end` (gate precondition 2). No manual pass.

### 3. Muscle mapping drift — impossible

The mapping table is authoritative: per-set overrides are refused at log time and per-set muscle edits do not exist. No manual pass.

### 4. Implausible progression jumps

- For each exercise in `session_history` (recent 30 sets), compute session-to-session e1RM change. The deterministic `audit_data` tool flags jumps above the rep-band bound for the current session best's reps:

<!--rep_bands-->
| reps | jump |
| ---- | ---- |
| to 6 | 4% |
| to 10 | 5% |
| to 15 | 8% |
| above 15 | no bound (informational) |
<!--/rep_bands-->

Drops over <!--const thresholds.progression_drop_pct|pctabs-->50%<!--/const--> flag as `progression_drop` (medium) by the same rule. A +1 rep gain is always 2.2%+ e1RM, so flat science-rate bounds would flag every routine rep PR. Skips jumps where set or workout notes on either session explain them (keywords: deload, return, program change, injury, technique, sick, travel).
- The agent's manual pass may apply the finer per-type bounds (novice compound 2%/session, intermediate 1%, advanced 0.5%, isolation 1.5%) on top.
- Evidence: set ids, dates, weights, reps, e1RM before/after, % jump, bound used.
- Fix: verify data entry, add explanatory note, or `session_update_set` weight/reps.

### 5. Goal trajectory divergence

- Deterministic: `audit_data` computes this from the goals tables (same code as `goal_show`). Manual pass only double-checks the numbers. For each active goal: logged top-set e1RM per session (last pre-goal date anchors session 1) against trajectory checkpoints. Flags `goal_divergence` if ≥ 2 consecutive sessions fall short by > <!--const thresholds.goal_divergence_pct-->5<!--/const-->% e1RM (one-sided, overperformance never misses) with no slippage/extend/compress note, `goal_slippage` if remaining sessions no longer fit before the deadline at split frequency. Sessions whose set or workout notes contain "deload" are excluded from the miss count (a deload session deliberately deviates; its trajectory resumes after, never compressed).
- Evidence: goal target, trajectory sessions vs logged sessions, divergence %.
- Fix: `goal_rewrite`, or add slippage decision.

### 6. Unreconciled split slots — impossible

Enforced by the `session_end` gate (precondition 4): a session with an exercise missing from every active split day cannot close without `program_split_reconcile`. No manual pass.

### 7. Stale open workouts

- Run `session_today`. If open workout exists with `age_days ≥ <!--const thresholds.stale_workout_days-->1<!--/const-->` or `last_set_created` gap > <!--const thresholds.stale_workout_hours-->8<!--/const-->h, and it appears in `session_calendar`/`session_stats`/`snapshot_export` counts.
- Evidence: workout id, date, age_days, last_set_created.
- Fix: `session_end` with note, or `session_delete_workout` if empty.

### 8. Volume vs MEV

`audit_data` uses the same completed-workout volume as the plan and Coach Notes. Each window has the current rotation length, including the planned rest slots. Windows end at the as-of date and cover up to the <!--const thresholds.volume_window_weeks-->8<!--/const-->-week lookback, extended when needed to fit the minimum number of windows. Weekly landmarks in `constants.json` are converted to sets per rotation.

- `volume_zero` (high) flags at least <!--const thresholds.volume_bad_rotations-->4<!--/const--> windows with zero sets.
- `volume_low` (medium) flags at least <!--const thresholds.volume_bad_rotations-->4<!--/const--> windows with some sets below MEV.
- Windows before the log or muscle training begins are excluded. For a muscle with no sets, use the overall logged history once it covers enough windows. A muscle with MEV zero needs no minimum sets.
- A `deprioritize` tier lowers the severity by one. Check active rules and deloads for intentional reductions before changing volume.

---

Severity guide:

- High: data loss risk (stale workout counted), goal silently broken, implausible jump with no note.
- Medium: volume below MEV.
- Low: near-duplicate exercise names, minor trajectory miss.
- A muscle marked `deprioritize` in the priority table flags one tier lower than the above implies (`volume_zero` medium, `volume_low` low).
