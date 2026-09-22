# SCIENCE.md

Hypertrophy training reference. Precedence: my logged data in MEMORY.md > SCIENCE.md defaults > agent instinct. Every entry tagged by confidence tier: Settled (near-consensus), Contested (real disagreement), Opinion (mine, thin evidence). Trust hierarchy: 1) meta-analyses/systematic reviews, 2) individual RCTs, 3) practitioner-researcher synthesis (RP/Israetel, Helms, Trexler), 4) anecdotal/forum — tier 4 only as color, never sole basis for a number.

Last reviewed: Sep 18 2026

## Volume landmarks (sets/week)

Numbers live in `constants.json` (single source of truth, edited via `log.py constants set` on approval). MEV = minimum effective volume, MAV = maximum adaptive volume, MRV = maximum recoverable volume. Ranges wide because individual variance is large; treat as starting bounds, not prescriptions.

Front delt: MEV 0 assumes regular chest pressing (most intermediates grow front delts with no direct work, RP). If pressing stops, treat direct MEV as ~4. Direct prioritization range is 4–12 sets/week across 2–4 sessions (RP via LiftVault 2024).

Rear delts: MEV 6 direct sets/week for intermediate-advanced lifters (RP). MRV scales with sessions: ~18 at 2x, ~25 at 3x, ~30 at 4x, up to ~35 at 5–6x (RP). Maintenance needs no direct work while back pulling continues.

Adductors: no trusted direct-volume landmarks, literature too thin for numbers. Adductor magnus grows from squat-pattern work (Plotkin et al. 2023 RCT: adductor mCSA up ~2.5 cm² after 9 weeks of back squat; Kubo et al. 2019, MRI volume gains), with wider stance increasing adductor recruitment (McCaw & Melrose; Hopkins 2024). Current plan uses ~4 direct machine sets/week across 2 exposures on top of leg press and hack squat indirect work (Opinion).

Forearms: no trusted landmarks, literature too thin for numbers. Current plan uses ~6 sets/week across 3 exposures (Opinion). Small, slow-twitch dominant, low systemic cost, same logic as abs guidance.

## Frequency guidance

Sessions/week per muscle lives in `constants.json` (`freq`, edited via `log.py constants set` on approval). Basis: Schoenfeld 2016 meta (2+ beats 1 at equal volume), RP guides, damage/recovery profiles.

Higher frequency mainly matters when weekly volume exceeds ~15 sets/muscle; below that, 1x and 2x are similar. Upper muscles at ~3.5x and legs at ~1.75x (current 8-day rotation) fall inside the settled range. Side delts at ~3.5x sit inside the range above, no deviation. Rear delts at ~3.5x sit inside the range above, no deviation.

## Rep range guidance

| Goal                  | Range | Tier    | Source                                 |
| --------------------- | ----- | ------- | -------------------------------------- |
| Hypertrophy (primary) | 6–12  | Settled | Schoenfeld 2017 meta, Morton 2019 RCT  |
| Hypertrophy (full)    | 5–20  | Settled | Same — near-equivalent if near failure |
| Strength-biased       | 3–6   | Settled | Rhea 2003 meta, ACSM position          |
| Strength-specific     | 1–3   | Settled | Neural adaptations dominant            |

No magic threshold; 5–20 all work if RPE 8–10. Below 5 shifts to strength, above 20 shifts to local endurance/metabolic. Compound lifts gravitate 5–10, isolation 8–15.

## Proximity to failure

| Guidance                                                   | Tier                             | Source                                                       |
| ---------------------------------------------------------- | -------------------------------- | ------------------------------------------------------------ |
| 0–2 RIR (RPE 8–10) for hypertrophy                         | Settled                          | Helms 2016, 2018; Grgic 2018; Morton 2019 RCT                |
| 0 RIR (true failure) not required, equal growth at 1–2 RIR | Contested                        | Some RCTs show equivalence, others slight edge to 0          |
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

## Deload / fatigue management

| Guidance                                                                                 | Tier      | Source                                    |
| ---------------------------------------------------------------------------------------- | --------- | ----------------------------------------- |
| Deload every 4–8 weeks (reduce volume 40–60%, intensity same)                            | Contested | Practitioner consensus, little direct RCT |
| Reactive deload: when performance drops 5%+ across 2 sessions                            | Opinion   | RP, Helms autoregulation                  |
| Passive rest after U2 and after U4 (2 per 8-day rotation), active deload every 4–6 weeks | Opinion   | Fits current rotation structure           |
| No evidence for "deload week" vs "deload session" superiority                            | Opinion   | Unstudied                                 |

## Exercise selection principles

| Principle                                                                                                   | Tier      | Source                                         |
| ----------------------------------------------------------------------------------------------------------- | --------- | ---------------------------------------------- |
| 1–2 compounds + 1–2 isolations per muscle/session                                                           | Opinion   | RP, Helms template                             |
| Movement pattern variety across week (vertical/horizontal push/pull)                                        | Settled   | Joint health, motor unit coverage              |
| Delt heads split: front via pressing, side and rear via direct isolation                                    | Opinion   | RP delt guides                                 |
| Lengthened-position bias for hypertrophy (stretch under load)                                               | Contested | Pedrosa 2022, Kassiano 2023 — growing evidence |
| Fly/pec deck variations — consider lengthened-position option (cable fly, pullover) if stretch bias desired | Opinion   | Pedrosa 2022, Kassiano 2023                    |

## Personal deviations

- Sep 20 2026: 8-day rotation U1, L1, U2, rest, U3, L2, U4, rest (uppers every 2 days, lowers every 4), Opinion
- Sep 20 2026: side delts 4x per 8 days (~3.5x/week), 16 sets per 8 days (14 weekly) across cable/machine/dumbbell pool, inside MAV 12-18, Opinion
- Sep 20 2026: not training calves, not as important for aesthetics, Opinion
- Sep 18 2026: delts tracked as front/side/rear heads; front MEV 0 via pressing volume, rear MEV 6 direct, Opinion
- Sep 18 2026: adductors tracked at ~4 direct sets/week across 2 exposures plus leg press/hack squat indirect work, Opinion
- Sep 18 2026: no direct glute work, RDL plus leg press judged sufficient, Opinion
- Sep 17 2026: Every set taken to failure (my style right now) → volume managed accordingly, Opinion
