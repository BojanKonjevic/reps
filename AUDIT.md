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
- For each exercise in `history` (recent 20 per lift), compare its logged `muscles` against MEMORY.md Lift mapping for that exercise.
- Flag mismatches (extra groups not in mapping, missing groups that are in mapping).
- Evidence: exercise, logged muscles vs MEMORY.md mapping.
- Fix: `retag` or update Lift mapping.

### 4. Implausible progression jumps
- For each exercise in `history` (recent 30 sets), compute session-to-session e1RM change. Flag any jump > SCIENCE.md rate-of-progression upper bound for that lift type (novice compound 2%/session, intermediate 1%, advanced 0.5%, isolation 1.5%) unless the set note contains "deload", "return", "program change", "injury", or similar.
- Evidence: set ids, dates, weights, reps, e1RM before/after, % jump, bound used.
- Fix: verify data entry, add explanatory note, or `update` weight/reps.

### 5. Goal trajectory divergence
- For each active goal in MEMORY.md Goals: pull `history` for that exercise since goal start. Compare logged top-set e1RM per session against trajectory session numbers. Flag if ≥ 2 consecutive sessions miss trajectory by > 5% e1RM and no slippage conversation triggered (search notes for "slippage", "extend", "compress").
- Evidence: goal target, trajectory sessions vs logged sessions, divergence %.
- Fix: `goal` to rewrite trajectory, or add slippage decision.

### 6. Unreconciled split slots
- Compare exercises logged in `range` (last 3 months) against MEMORY.md Split for their day type. Flag any exercise that appears ≥ 3 times but is not listed in the corresponding Split section (including interchangeable `/` entries).
- Evidence: exercise, day type, occurrence count, Split section content.
- Fix: add to Split at next `end`, or `retag` if misclassified.

### 7. Stale open workouts
- Run `today`. If open workout exists with `age_days ≥ 1` or `last_set_created` gap > 8h, and it appears in `calendar`/`stats`/`export` counts.
- Evidence: workout id, date, age_days, last_set_created.
- Fix: `end` with note, or `delete-workout` if empty.

### 8. Volume vs frequency guidance
- For each tracked muscle in MEMORY.md Tracked muscles: compute weekly sets/week from `range` (last 8 weeks). Compare against SCIENCE.md frequency guidance (2–3 for upper, 2 for legs, 3–4 for abs). Flag muscle groups averaging < MEV (from SCIENCE.md volume landmarks) for ≥ 4 consecutive weeks with no Active rule in MEMORY.md explaining intentional reduction (injury, deload block, specialization).
- Evidence: muscle, weekly sets/week for each week, MEV, Active rules.
- Fix: add volume, or add Active rule explaining.

---

Severity guide:
- High: data loss risk (stale workout counted), goal silently broken, implausible jump with no note.
- Medium: mapping drift, missing muscles, unreconciled split, volume below MEV.
- Low: near-duplicate exercise names, minor trajectory miss.