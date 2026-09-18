# memory

Durable training memory. Fresh agents read this first. Keep it short, current state only.

Last compacted: never.

## Needs confirm

Empty. Rules whose date passed move here, never deleted silently. Agent asks once, then reactivates or archives.

## Active rules

- Sep 18 2026: straps on anything grip-limited, including wrapping straps around cable attachments instead of handles. Grip is never a limiter.
  Format: start date, rule, expiry if any.
  Example: Sep 1 2026 incline barbell bench press is the main press until Nov 1 2026, flat only on request.

## Program

Upper/Lower rotation, no fixed weekdays: Upper A, Lower A, Upper B, rest, Upper C, Lower B, rest, repeat. Brand new as of Sep 18 2026, moving here from 3.5 years of PPL. Experimental until stated otherwise.

## Split

Slots in training order, one per line, interchangeable moves on one line separated by /. Reconciled at every session end, rewritten only when the user says the split changed.

### Upper A

1. incline barbell bench press
2. hammer strength row
3. pec deck
4. low to high row (hammer strength)
5. machine shoulder press
6. cable lat raise
7. bayesian curl
8. overhead cable extension
9. cable reverse curl
10. face pull / cable rear delt fly

### Lower A

1. leg extension
2. hack squat
3. leg press (feet low)
4. seated leg curl
5. adductor machine
6. crunch machine
7. cable lat raise
8. machine lat raise

### Upper B

1. machine shoulder press
2. straight bar pulldown
3. incline dumbbell press
4. hammer strength row
5. cable lat raise
6. machine lat raise
7. incline dumbbell curl
8. ezbar skullcrusher
9. unilateral cable pushdown
10. cable wrist curl

### Upper C

1. cable fly
2. hammer strength press
3. cable pullover
4. machine row
5. preacher curl
6. rope hammer curl
7. overhead cable extension
8. cable lat raise
9. cable wrist extension
10. face pull

### Lower B

1. rdl
2. leg press (feet high)
3. hack squat
4. leg extension
5. seated leg curl
6. crunch machine

## Tracked muscles

chest, back, shoulders, biceps, triceps, quads, hamstrings, glutes, abs, forearms. Never neck, calves, traps. New movements mapping elsewhere get asked about once.

## Goals

Triggered by the word "goal". One block per goal: target, deadline, trajectory as numbered sessions (dates float, sessions don't).

None yet.

## Lift mapping

Exercise to muscle groups, asked once and recorded. Form dependent entries note the form.

- back squat -> quads, glutes
- dips -> triceps (their form, elbows tucked, triceps main)
- flat barbell bench press -> chest (chest only by convention, no shoulder or tricep credit)
- lat pulldown -> back

## State

Bodyweight, injuries, sleep, motivation notes that carry over. One line each, newest last.

## Monthly rollups

One short block per month, written on request at month end. Trend plus caveats, not raw sets. Raw sets stay in SQLite.
