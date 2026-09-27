# ISSUES.md

Running log of problems noticed during sessions that need fixing later. Each entry: date, one-line summary, example/trigger, severity.

Severity: high (blocks logging/analysis), medium (wrong but workaroundable), low (cosmetic/nice-to-have).

---

## Template for new entries:

- YYYY-MM-DD: [severity] Summary
  Example: what was said vs what happened
  Fix: brief note on what needs changing

---

## Entries

- 2026-09-27: [medium] Hardening report filed (~70 findings, F01-F70 + U01-U04); Round 1-2 backend fixes implemented, dashboard/UX pass pending
  Example: /tmp/reps-hardening-report.md investigation notes
  Fix: work the suggested implementation order; log justified deviations here
- 2026-09-27: [low] Restore with FK enforcement at load time fails on valid dumps (iterdump table order)
  Example: INSERT INTO progression runs before CREATE TABLE workouts exists
  Fix: FIXED, load with FK OFF then foreign_key_check + version check before replace (reps/sync.py)
- 2026-09-27: [low] Epley unbounded past 12 reps fed PRs/stall/goals
  Example: 13-rep set could fake-PR over a heavy best
  Fix: FIXED, e1rm_cap_reps 12 tunable + is_e1rm_counting_set at all consumers (reps/e1rm.py)
- 2026-09-27: [low] MEV tiers marked settled on Schoenfeld-2017-derived dose landmarks
  Example: chest/back/side/biceps/triceps/quads claimed settled status
  Fix: FIXED, downgraded to contested with corrected sources (via constants_set)
- 2026-09-27: [high] New tests hit the real workouts.db when written without the log_module fixture
  Example: test_end_gate_behavior_literal created open workout 10 + 5 bench sets in the live DB
  Fix: FIXED, tests rewritten on log_module/tmp_db; stray rows deleted, integrity + FK check clean. Rule: every test that writes uses fixtures, never bare `import reps` writes
- 2026-09-27: [high] Refusal-after-write leaked open transactions into "database is locked" (busy_timeout 30s)
  Example: consume_flag UPDATE then rowcount refusal held the lock; next writer blocked 30s
  Fix: FIXED, check-then-act in consume_flag, drop_goal, rename_lift, update_workout (refusal precedes any write). Rule: no write before the last refusal in a function
- 2026-09-27: [medium] Snapshot scaling cliffs remain (correct at current size, slow at 3-year scale)
  Example: bodyweight_view O(n2) rescan, calendar day-loop from first date, plan ledger per-muscle queries
  Fix: OPEN, get_calendar batched; rest deferred until a 3-year synthetic perf test exists (generate, do not hand-write)
- 2026-09-27: [low] Canvas paint cost unmeasured (per-chart listeners, double paint, no observers)
  Example: TrendMini bare canvas vs hardcoded 860x250 charts fighting fluid CSS
  Fix: OPEN, measure before optimizing per report; responsive contract documented in DASHBOARD.md
- 2026-09-27: [low] glutes mev 6 vs personal no-direct-glute-work deviation can flag below_mev
  Example: constants glutes mev 6, SCIENCE personal deviation says RDL + leg press judged sufficient
  Fix: OPEN, reconcile with an Active rule or a deprioritize tier, do not silently adjust the number
- 2026-09-27: [low] DB connections never closed, no busy_timeout
  Example: conn() per call with no close, no busy_timeout
  Fix: FIXED partially, busy_timeout 30s + NULL-safe e1RM UDF + corruption check on multiple open workouts; full close discipline deferred (single-writer local app, GC closes short-lived handles)
