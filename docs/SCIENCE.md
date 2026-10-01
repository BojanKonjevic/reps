# SCIENCE.md

Hypertrophy training reference. Precedence: my logged data in MEMORY.md > SCIENCE.md defaults > agent instinct. Every entry tagged by confidence tier: Settled (near-consensus), Contested (real disagreement), Opinion (mine, thin evidence). Trust hierarchy: 1) meta-analyses/systematic reviews, 2) individual RCTs, 3) practitioner-researcher synthesis (RP/Israetel, Helms, Trexler), 4) anecdotal/forum — tier 4 only as color, never sole basis for a number.

Last reviewed: Oct 01 2026

## Volume landmarks (sets/week)

Numbers live in `constants.json` (single source of truth, edited via the `constants_set` tool on approval). MEV = minimum effective volume, MAV = maximum adaptive volume, MRV = maximum recoverable volume. Ranges wide because individual variance is large; treat as starting bounds, not prescriptions. Oct 01 2026 refresh: Pelland et al. 2025 Sports Med meta-regression (67 studies, 2058 lifters, fractional counting for indirect sets) finds volume increases size and strength with diminishing returns (stronger flattening for strength); ACSM overview notes hypertrophy plateau around 18-20 weekly sets. Supports current landmarks, no number change.

Front delt: MEV 0 assumes regular chest pressing (most intermediates grow front delts with no direct work, RP). If pressing stops, treat direct MEV as ~4. Direct prioritization range is <!--const muscles.front delts.mav-->[4, 12]<!--/const--> sets/week across 2–4 sessions (RP via LiftVault 2024).

Rear delts: MEV 6 direct sets/week for intermediate-advanced lifters (RP). MRV scales with sessions: ~18 at 2x, ~25 at 3x, ~30 at 4x, up to ~35 at 5–6x (RP). Maintenance needs no direct work while back pulling continues.

Adductors: no trusted direct-volume landmarks, literature too thin for numbers. Adductor magnus grows from squat-pattern work (Plotkin et al. 2023 RCT: adductor mCSA up ~2.5 cm² after 9 weeks of back squat; Kubo et al. 2019, MRI volume gains), with wider stance increasing adductor recruitment (McCaw & Melrose; Hopkins 2024). Current plan uses ~4 direct machine sets/week across 2 exposures on top of leg press and hack squat indirect work (Opinion).

Forearms: no trusted landmarks, literature too thin for numbers. Current plan uses ~6 sets/week across 3 exposures (Opinion). Small, slow-twitch dominant, low systemic cost, same logic as abs guidance.

## Frequency guidance

Sessions/week per muscle lives in `constants.json` (`freq`, edited via the `constants_set` tool on approval). Basis: Schoenfeld 2016 meta (2+ beats 1 at equal volume), RP guides, damage/recovery profiles. Oct 01 2026 refresh: Pelland et al. 2025 (frequency effect on hypertrophy compatible with negligible, positive for strength with diminishing returns) and Tao et al. 2026 (47 studies, volume-equated frequency no meaningful hypertrophy difference) confirm volume-equated frequency matters little for growth.

Higher frequency mainly matters when weekly volume exceeds ~15 sets/muscle; below that, 1x and 2x are similar. Upper muscles at ~3.5x and legs at ~1.75x (current 8-day rotation) fall inside the settled range. Side delts at ~3.5x sit inside the range above, no deviation. Rear delts at ~3.5x sit inside the range above, no deviation.

## Rep range guidance

| Goal                  | Range | Tier    | Source                                 |
| --------------------- | ----- | ------- | -------------------------------------- |
| Hypertrophy (primary) | 6–12  | Settled | Schoenfeld 2017 meta, Morton 2019 RCT  |
| Hypertrophy (full)    | 5–20  | Settled | Same — near-equivalent if near failure |
| Strength-biased       | 3–6   | Settled | Rhea 2003 meta, ACSM position          |
| Strength-specific     | 1–3   | Settled | Neural adaptations dominant            |

No magic threshold; 5–20 all work if RPE 8–10. Below 5 shifts to strength, above 20 shifts to local endurance/metabolic. Compound lifts gravitate 5–10, isolation 8–15. Oct 01 2026 refresh: Carvalho et al. 2022 meta (volume-matched loads, hypertrophy similar across loads, strength favors heavy) and Cumming et al. 2025 in trained lifters confirm, no change.

## Proximity to failure

| Guidance                                                   | Tier                             | Source                                                       |
| ---------------------------------------------------------- | -------------------------------- | ------------------------------------------------------------ |
| 0–2 RIR (RPE 8–10) for hypertrophy                         | Settled                          | Helms 2016, 2018; Grgic 2018; Morton 2019 RCT                |
| 0 RIR (true failure) not required, equal growth at 1–2 RIR | Contested                        | Refalo 2022 meta plus Robinson et al. 2024 meta-regressions (strength flat across RIR, hypertrophy improves closer to failure, exact RIR unclear) |
| Compound lifts: stop 1–2 RIR for fatigue management        | Opinion (practitioner consensus) | RP, Helms, Israetel                                          |
| Isolation: 0–1 RIR acceptable, lower systemic cost         | Opinion                          | RP, Helms                                                    |
| Training to failure every set → manage volume down         | Opinion (practitioner consensus) | RP, Helms — higher per-set fatigue, lower recoverable volume |

## Rate of progression bounds

| Lift type / training age            | %/session      | %/month         | Tier      | Source                                   |
| ----------------------------------- | -------------- | --------------- | --------- | ---------------------------------------- |
| Novice compound (squat, bench, row) | 1–2%           | 4–8%            | Settled   | Rhea 2003, Peterson 2005, Schoenfeld     |
| Intermediate compound               | 0.5–1%         | 2–4%            | Settled   | Same, adjusted for diminishing returns   |
| Advanced compound                   | 0.25–0.5%      | 1–2%            | Contested | Very sparse data, practitioner estimates |
| Isolation (all levels)              | 0.5–1.5%       | 2–6%            | Contested | Less studied, smaller absolute loads     |
| Rep progression (same weight)       | +1 rep/session | +4–8 reps/month | Opinion   | RP progression models                    |

Reference: 2.5 kg jump on upper compounds ≈ 2–3% at 80–100 kg loads (intermediate). 5 kg on legs ≈ 2–4% at 100–150 kg. A 20% jump (e.g., 100 → 120) exceeds any level's typical single-session progression.

Why `rep_bands` in `constants.json` (4/5/8%) differ from the bounds above (0.25–2%/session): the bands are jump-detection thresholds for audit flags, not progression targets. A +1 rep gain is always 2.2%+ e1RM by Epley arithmetic, so flagging every routine rep PR against a 1% science-rate bound would cry wolf on normal training. The bands answer "is this jump implausible", the table answers "how fast should I expect to gain". Different questions, different numbers, Opinion.

## e1RM validity range (Epley)

e1RM = w × (1 + r/30), single owner `reps/e1rm.py`. Validity range: reps ≤ <!--const thresholds.e1rm_cap_reps-->12<!--/const--> (Contested boundary, practitioner consensus: Epley overpredicts past ~12 and is out of scope there). Sets above the cap are stored and charted as raw volume but excluded from every e1RM-derived decision: PR flags, progression tops, stall/slip inputs, goal and audit aggregates. Any e1RM improvement on a counting set is a PR, including +0.1 kg (no min-jump, no plate-aware epsilon on the PR rule itself). Rationale: training tops out ~12, so no history rewrite; >12 is out-of-domain and must not fake-PR over heavy bests.

## Deload / fatigue management

| Guidance                                                                                 | Tier      | Source                                    |
| ---------------------------------------------------------------------------------------- | --------- | ----------------------------------------- |
| Deload every 4–8 weeks (reduce volume <!--const thresholds.deload_volume_reduction|pctrange-->40-60%<!--/const-->, intensity same)                            | Contested | Practitioner consensus, little direct RCT (Bell et al. 2023 Delphi; athlete survey 2024 reports 6.4 days every 5.6 weeks; S&C survey 2024 most cuts 0-25%, physique context may need more) |
| Reactive deload: when performance drops <!--const thresholds.deload_watch_pct|pctabs-->5%<!--/const-->+ across 2 sessions                            | Opinion   | RP, Helms autoregulation                  |
| Passive rest after U2 and after U4 (2 per 8-day rotation), active deload every 4–6 weeks | Opinion   | Fits current rotation structure           |
| No evidence for "deload week" vs "deload session" superiority                            | Opinion   | Unstudied                                 |
| Deload duration: one full rotation (8 days) at reduced volume, then ramp back over the next rotation (first session back stays light, no PR attempts until the second rotation) | Opinion | Practitioner consensus, fits 8-day structure |
| Strength-loss guard: if top sets are still >5% down after the ramp-back rotation, that is not residual fatigue, investigate programming, sleep, or pain before adding volume | Opinion | Helms autoregulation |

## Exercise selection principles

| Principle                                                                                                   | Tier      | Source                                         |
| ----------------------------------------------------------------------------------------------------------- | --------- | ---------------------------------------------- |
| 1–2 compounds + 1–2 isolations per muscle/session                                                           | Opinion   | RP, Helms template                             |
| Movement pattern variety across week (vertical/horizontal push/pull)                                        | Settled   | Joint health, motor unit coverage              |
| Delt heads split: front via pressing, side and rear via direct isolation                                    | Opinion   | RP delt guides                                 |
| Lengthened-position bias for hypertrophy (stretch under load)                                               | Contested | Pedrosa 2022, Kassiano 2023, Strey et al. 2026 meta (long over short ES 0.28), Pedrosa 2026 review, Varovic et al. 2025 regional meta |
| Fly/pec deck variations — consider lengthened-position option (cable fly, pullover) if stretch bias desired | Opinion   | Pedrosa 2022, Kassiano 2023, Strey 2026                    |

## Bodyweight protocol

Gym scale, shoes on, non-fasted, sporadic entries (MEMORY.md). The dashboard 7-day average implies continuity it does not have: treat `avg7` as a rough smoother, not a trend. Rules: one entry per day max, latest wins; a <!--const thresholds.bodyweight_gap_days-->14<!--/const-->-day gap breaks continuity (no interpolation across it); single weigh-ins more than ±3% off the recent average get a confirming re-weigh note, not silent acceptance. No cut/bulk decisions off fewer than 14 days of entries.

## Pain and confounder policy

Pain is free-text in set and workout notes plus a `NOTE_HOT_KEYWORDS` scan (pain, sleep, sore, injury), no severity scale. Red flags that stop training talk and refer out: sharp or shooting pain, joint swelling, numbness/tingling, chest pain, head injury, pain that worsens across sets. Anything else trains around, never through: form breakdown or pain ends the lift for the day, logged with a note. Confounders (sleep, illness, travel, stress) are captured only if volunteered in notes, never prompted; systemic overtraining reads (3 lifts/2 patterns in PROGRAMMING.md) always carry the caveat that confounders were not systematically screened. Level-aware progression bounds from the table above apply to `progression_set` targets and goal trajectories: a target implying faster than the lifter's level band needs an explanatory note, never silent acceptance.

## Personal deviations- Sep 20 2026: 8-day rotation U1, L1, U2, rest, U3, L2, U4, rest (uppers every 2 days, lowers every 4), Opinion
- Sep 20 2026: side delts 4x per 8 days (~3.5x/week), 16 sets per 8 days (14 weekly) across cable/machine/dumbbell pool, inside MAV <!--const muscles.side delts.mav-->[12, 18]<!--/const-->, Opinion
- Sep 20 2026: not training calves, not as important for aesthetics, Opinion
- Sep 18 2026: delts tracked as front/side/rear heads; front MEV 0 via pressing volume, rear MEV 6 direct, Opinion
- Sep 18 2026: adductors tracked at ~4 direct sets/week across 2 exposures plus leg press/hack squat indirect work, Opinion
- Sep 18 2026: no direct glute work, RDL plus leg press judged sufficient, Opinion. Mechanism if volume ever flags below MEV: the `deprioritize` tier (`program_priority_set`), which audit and coach notes both read as intentional and downgrade one severity level, never a silent `mev` edit. `constants.json` keeps `mev: 6` as the unadjusted reference.
- Sep 17 2026: Every set taken to failure (my style right now) → volume managed accordingly, Opinion
