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

Slots in training order with working set counts, one per line, interchangeable moves on one line separated by /. Reconciled at every session end, rewritten only when the user says the split changed.

### Upper A

1. incline barbell bench press x3
2. hammer strength row x2
3. pec deck x2
4. low to high row x2
5. machine shoulder press x2
6. cable lat raise x2
7. bayesian curl x2
8. overhead cable extension x2
9. cable reverse curl x2
10. face pull / cable rear delt fly x2

### Lower A

1. leg extension x3
2. hack squat x3
3. leg press (feet low) x2
4. seated leg curl x2
5. adductor machine x2
6. crunch machine x2-3
7. cable lat raise x2
8. machine lat raise x2

### Upper B

1. straight bar pulldown x3
2. reverse-grip smith incline press x3
3. machine shoulder press x2
4. hammer strength row x2
5. cable lat raise x2
6. machine lat raise x2
7. incline dumbbell curl x2
8. ezbar skullcrusher x2
9. unilateral cable pushdown x3
10. cable wrist curl x2

### Upper C

1. cable fly x3
2. hammer strength press x2
3. cable pullover x2
4. machine row x2
5. preacher curl x2
6. rope hammer curl x2
7. overhead cable extension x2
8. cable lat raise x2
9. cable wrist extension x2
10. face pull x2

### Lower B

1. rdl x3
2. leg press (feet high) x2
3. hack squat x2
4. leg extension x2
5. seated leg curl x2
6. crunch machine x2

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
- reverse-grip smith incline press -> chest (upper chest emphasis)

## State

Bodyweight, injuries, sleep, motivation notes that carry over. One line each, newest last.

## Monthly rollups

One short block per month, written on request at month end. Trend plus caveats, not raw sets. Raw sets stay in SQLite.
