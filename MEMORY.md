# memory

Durable training memory. Fresh agents read this first. Keep it short, current state only.

Last compacted: never.

## Needs confirm

Empty. Rules whose date passed move here, never deleted silently. Agent asks once, then reactivates or archives.

## Active rules

None yet. Add dated rules here when user states something durable.
Format: start date, rule, expiry if any.
Example: 2026-09-01 incline barbell bench press is the main press until 2026-11-01, flat only on request.

## Program

3 days on, 1 off. Current split and main lifts go here once known.

## Split

Push / pull / legs. Slots in training order, one per line, interchangeable moves on one line separated by /. Reconciled at every session end, rewritten only when the user says the split changed.

### Push

### Pull

### Legs

## Tracked muscles

chest, back, shoulders, biceps, triceps, quads, hamstrings, glutes, abs. Never neck, calves, forearms, traps. New movements mapping elsewhere get asked about once.

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
