# memory

Durable training memory. Fresh agents read this first. Keep it short, current state only.

Last compacted: never.

## Needs confirm

Empty. Rules whose date passed move here, never deleted silently. Agent asks once, then reactivates or archives.

## Active rules

Format: start date, rule, expiry if any.

- Sep 18 2026: straps on anything grip-limited, including wrapping straps around cable attachments instead of handles. Grip is never a limiter.
- Sep 19 2026: hammer strength row logged as total both sides (45 per side = 90).
- Sep 19 2026: unilateral sets capped by first hand when lower, always log weaker side reps with L/R in note when diverged.
- Sep 19 2026: end notes stay lean, one line, only what numbers cannot explain (returns, new lifts, rep scheme shifts, bad sleep, pain). DB holds weights, MEMORY holds setups. Pain/sleep silent when fine.
  Example: Baseline Upper A. Shoulder press first time in a year. First session pushing higher reps on isolations. Reverse curl new.
- Sep 19 2026: height means cable height or seat height setup, ask if unsure, repeat it in every next-exercise reminder.
- Sep 19 2026: at every session end, audit that session only (all sets have muscles, set counts match the split slot, canonical names). Never a full-DB audit unless asked.

## Program

Upper/Lower rotation, no fixed weekdays: Upper A, Lower A, Upper B, rest, Upper C, Lower B, rest, repeat. Brand new as of Sep 18 2026, moving here from 3.5 years of PPL. Experimental until stated otherwise.

## Split

Slots in training order with working set counts, one per line, interchangeable moves on one line separated by /. Reconciled at every session end, rewritten only when the user says the split changed.

### Upper A

1. incline barbell bench press x3
2. hammer strength row x2
3. pec deck x2
4. straight bar pulldown x2
5. machine shoulder press x2
6. cable lat raise x2
7. bayesian curl x2
8. preacher curl x2
9. cable pushdown x2
10. cable reverse curl x2
11. face pull / cable rear delt fly x2

### Lower A

1. hack squat x2
2. leg extension x3
3. leg press x2
4. seated leg curl x3
5. adductor machine x2
6. crunch machine x3
7. machine lat raise x2
8. cable wrist curl x2

### Upper B

1. straight bar pulldown x3
2. reverse-grip smith incline press x3
3. hammer strength row x2
4. machine shoulder press x2
5. cable lat raise x2
6. ezbar curl x2
7. ezbar skullcrusher x2
8. unilateral cable pushdown x3
9. face pull / cable rear delt fly x2

### Upper C

1. hammer strength press x2
2. hammer strength row x2
3. pec deck x3
4. cable pullover x2
5. bayesian curl x2
6. preacher curl x2
7. cable pushdown x2
8. machine lat raise x2
9. cable wrist extension x2
10. face pull x2

### Lower B

1. rdl x3
2. leg press x3
3. hack squat x2
4. leg extension x2
5. seated leg curl x2
6. adductor machine x2
7. crunch machine x3
8. cable lat raise x2
9. cable wrist curl x2

## Tracked muscles

chest, back, front delt, side delt, rear delt, biceps, triceps, quads, hamstrings, glutes, abs, forearms, adductors. Never neck, calves, traps. New movements mapping elsewhere get asked about once.

## Goals

Triggered by the word "goal". One block per goal: target, deadline, trajectory as numbered sessions (dates float, sessions don't).

None yet.

## Lift mapping

Exercise to muscle groups, asked once and recorded. Form dependent entries note the form.

- back squat -> quads, glutes
- dips -> triceps (my form, elbows tucked, triceps main)
- flat barbell bench press -> chest, front delt (triceps excluded by convention)
- incline barbell bench press -> chest, front delt
- reverse-grip smith incline press -> chest (upper chest emphasis)
- hammer strength press -> chest
- machine shoulder press -> front delt (neutral grip, slight lean for upper chest)
- pec deck -> chest
- hammer strength row -> back
- straight bar pulldown -> back (attachment matters, logged under this name, not lat pulldown)
- cable pullover -> back
- face pull -> rear delt (max height)
- cable rear delt fly -> rear delt
- cable lat raise -> side delt
- machine lat raise -> side delt
- hack squat -> quads
- leg press -> quads, glutes
- rdl -> hamstrings, glutes
- leg extension -> quads
- seated leg curl -> hamstrings
- lying leg curl -> hamstrings
- adductor machine -> adductors
- crunch machine -> abs
- bayesian curl -> biceps (cable below 8)
- preacher curl -> biceps
- ezbar curl -> biceps
- incline dumbbell curl -> biceps
- rope hammer curl -> biceps, forearms
- cable reverse curl -> forearms
- cable pushdown -> triceps
- unilateral cable pushdown -> triceps
- ezbar skullcrusher -> triceps
- cable wrist curl -> forearms
- cable wrist extension -> forearms

## State

Bodyweight, injuries, sleep, motivation notes that carry over. One line each, newest last.

- Sep 18 2026: no scale at home, bodyweight measured on gym scale (not fasted, less consistent, not every day).
- Sep 19 2026: straight bar pulldown stack jumps 10kg (47, 57, 67, 77, 87, 97, 107, 117, 127).

## Monthly rollups

One short block per month, written on request at month end. Trend plus caveats, not raw sets. Raw sets stay in SQLite.
