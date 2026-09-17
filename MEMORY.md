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

## Tracked muscles

chest, back, shoulders, biceps, triceps, quads, hamstrings, glutes, abs. Never neck, calves, forearms, traps. New movements mapping elsewhere get asked about once.

## State

Bodyweight, injuries, sleep, motivation notes that carry over. One line each, newest last.

## Monthly rollups

One short block per month, written on request at month end. Trend plus caveats, not raw sets. Raw sets stay in SQLite.
