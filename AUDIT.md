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

### 2. Missing muscle tags

- Pull `range` (last 6 months) or `export`. Find sets where `muscles` is empty or `""`.
- Evidence: set ids, exercise, date.
- Fix: `retag <exercise> <muscles>` or per-set `update <id> muscles <...>`.

### 3. Muscle mapping drift

- For each exercise in `history` (recent 20 per lift), compare its logged `muscles` against MOVEMENTS.md Lift mapping for that exercise.
- Flag mismatches (extra groups not in mapping, missing groups that are in mapping).
- Evidence: exercise, logged muscles vs MOVEMENTS.md mapping.
- Fix: `retag` or update Lift mapping.

### 4. Implausible progression jumps

- For each exercise in `history` (recent 30 sets), compute session-to-session e1RM change. The deterministic `audit` command flags jumps above a rep-band bound read off the current session best's reps: 4% at 1-6 reps, 5% at 7-10, 8% at 11-15. Above 15 reps e1RM is informational only and never flags. Drops over 50% flag as `progression_drop` (medium) by the same rule. A +1 rep gain is always 2.2%+ e1RM, so flat science-rate bounds would flag every routine rep PR. Skips jumps where set or workout notes on either session explain them (keywords: deload, return, program change, injury, technique, sick, travel).
- The agent's manual pass may apply the finer per-type bounds (novice compound 2%/session, intermediate 1%, advanced 0.5%, isolation 1.5%) on top.
- Evidence: set ids, dates, weights, reps, e1RM before/after, % jump, bound used.
- Fix: verify data entry, add explanatory note, or `update` weight/reps.

### 5. Goal trajectory divergence

- For each active goal in GOALS.md: pull `history` for that exercise since goal start. Compare logged top-set e1RM per session against trajectory session numbers. Flag if ≥ 2 consecutive sessions miss trajectory by > 5% e1RM and no slippage conversation triggered (search notes for "slippage", "extend", "compress").
- Evidence: goal target, trajectory sessions vs logged sessions, divergence %.
- Fix: `goal` to rewrite trajectory, or add slippage decision.

### 6. Unreconciled split slots

- Compare exercises logged in `range` (last 3 months) against MOVEMENTS.md Split for their day type. Flag any exercise that appears ≥ 3 times but is not listed in the corresponding Split section (including interchangeable `/` entries).
- Evidence: exercise, day type, occurrence count, Split section content.
- Fix: add to Split at next `end`, or `retag` if misclassified.

### 7. Stale open workouts

- Run `today`. If open workout exists with `age_days ≥ 1` or `last_set_created` gap > 8h, and it appears in `calendar`/`stats`/`export` counts.
- Evidence: workout id, date, age_days, last_set_created.
- Fix: `end` with note, or `delete-workout` if empty.

### 8. Volume vs MEV (rolling 8-week window)

- For each tracked muscle in MOVEMENTS.md Tracked muscles: compute weekly sets for each of the last 8 weeks (current week + 7 back) from `range`. Weeks with no logged sets count as 0, not as absent. Two separate flags, counted over the whole window (a good week in between does not reset the count):
  - `volume_zero` (high): 0 sets in ≥ 4 of the last 8 weeks.
  - `volume_low` (medium): 0 < sets < MEV in ≥ 4 of the last 8 weeks.
- MEV comes from the SCIENCE.md volume landmarks. Flags with no Active rule in MEMORY.md explaining intentional reduction (injury, deload block, specialization) stand; explained ones are still listed, not silently dropped.
- Evidence: muscle, bad-week count out of 8, per-week set counts, MEV.
- Fix: add volume, or add Active rule explaining.

---

Severity guide:

- High: data loss risk (stale workout counted), goal silently broken, implausible jump with no note.
- Medium: mapping drift, missing muscles, unreconciled split, volume below MEV.
- Low: near-duplicate exercise names, minor trajectory miss.
