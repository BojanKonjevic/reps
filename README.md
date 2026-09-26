# reps

Chat first training log. You train and talk, the agent stores every set in local SQLite through MCP tools.

## Why I built it

Most logs force a choice. Either a rigid tracker that stores everything and understands nothing, or a chatbot coach that talks well and remembers nothing.

I wanted both. I text between sets the way I would text a training partner, then ask questions when I have them. Underneath, every set lands with exact weight, reps, muscles and notes, and the same agent that logs also coaches. It suggests targets from my history, adjusts when I miss, and plots goals session by session.

Code owns what is derivable or enforceable, the agent owns judgment. That split keeps the reasoning honest. Claims have to ground out in stored sets, rules fail loudly instead of drifting, and my logged data beats any default.

## What it feels like in the gym

You open a chat and say you are training. I run it in t3code, any setup where the agent can reach the Reps MCP server works. The agent tells you what is up, lift by lift, with weight, reps and sets. Then you send sets as you go.

A message like "squat 90 5/5/7, last to failure" fans out into three logged sets. Most logs are shorter, a "6" or "8 again", and an ambiguous "same" gets one clarifying question, never a guess. Replies stay terse mid workout, something like "logged 3x". You ask questions between sets, say done at the end, and you get a short report plus a synced dashboard.

This handles gym mess well, because gyms are messy. You load too much per side by accident and grind out 8 ugly reps. You try reverse grip pressing for the first time and your wrists want to roll until the groove clicks. You come in slightly sore, two days since bench instead of the usual three. The Smith is taken, so two lifts flip order with no program change. You are in a hurry, so it tells you 4 sets left. You write all of it in plain words and training continues. Warmups never get logged, RPE never gets asked for, failure is the silent default. Only what is off gets a note.

The agent remembers the boring parts so you do not have to. It reuses canonical lift names, asks once which muscles a new movement trains, then never asks again. Setup details live on the movement, seat height, attachment, stack steps, uni or bilateral, and surface once as a reminder mid session. Cable micros of .625, a preacher guess of 1.75, an unmarked EZ bar called 7.5, all saved once with the uncertainty stated. Pounds convert to kilos with the conversion stated. Weighted dips log extra weight only, bodyweight pullups log zero with a flag.

It also protects the history. Implausible jumps stop and ask before anything is written. Corrections need an exact set id, so "second squat was 92.5" gets confirmed in chat first. Once I asked it to log 5 reps with no note for a set where I really did 8 with bad form, to test its willingness to say no, and it refused twice, because a fake 5 still PRs on e1RM and lies about reps while the true 8 with a note keeps the standard honest. A wrong log poisons every future analysis, a question costs nothing.

## What you get out

Targets that fit your week. A first session gets conservative openers with a rep range per new movement, then seeds every baseline from set one. First session back after a break stays light on purpose. PR attempts get marked. Only each lift's first work set is judged against plan, the rest are expected to fade, and a clear overperformance bumps the remaining sets once. Pulldown going 77x12 against a 77x8 plan becomes 87 for what is left. A lift trained late reading lower than the same lift trained fresh reads as order fatigue, never as a stall.

Goals with a path. You pick a target and a deadline, it lays out e1RM session by session and re-anchors after every relevant log. When reality slips it asks whether to extend the deadline or compress the jumps. It never compresses silently.

Volume that stays in range. Muscles track against MEV, MAV and MRV from the evidence base. A muscle under its floor gets folded into the day when it fits an existing slot, otherwise it shows up as a one line note. Priorities reorder the split, top sets move to position one, accessories drop a set so session length stays flat.

Cuts that wait for evidence. Two bad sessions in a row flag deload watch, a third triggers a reactive deload. Autoregulation trims a set from accessories first, never below the floor, and brings volume back slower than it left. Anything goal related goes through the goals flow, nothing rewrites the program on its own.

Short reports, honest ones. PRs, top sets versus last time on the same slot, targets hit or missed, plus feel notes when you state them. A PR means beating your prior best e1RM on a lift, the first logged set is the baseline, never a PR. When I admitted my first baselines were intentionally undershot, later jumps got read as recalibration, not strength. Every close shows what got written versus chat-only thoughts, so the record stays checkable. No tonnage celebrations, no total set counts as achievements. Trends, PRs and adherence are the currency.

A dashboard you can check on your phone. e1RM trends per lift, volume by muscle, calendar with rest days kept distinct from missed days, trophy marks on PR days. Bodyweight comes from the gym scale when you remember, about one entry a day, latest wins on the chart.

A program you can change in words. Bring up side delts, swap an exercise, ask for goal ideas, review the split against the evidence, audit the data when something looks off. Month end writes a short rollup, trend plus caveats, never raw sets.

## How it works

Three parts. The database holds facts and state, workouts and sets plus program, progression, goals, rules and flags, reached through typed MCP tools. The markdown holds protocol, logging runs sessions, programming designs the program, science pins the defaults, memory carries injuries and life context. The dashboard shows it back, a validated snapshot published to a read-only Cloudflare Worker.

Derivable numbers compute on read, e1RM, ledger, volume, slot guess, and never get stored. Non negotiable rules refuse at the point of violation, the session close gate is one example. Ownership of every fact lives in docs/SSOT.md, module boundaries live in docs/ARCHITECTURE.md.

## Repo map

- reps, the backend, one module per domain.
- docs, protocol and state. LOGGING for sessions, PROGRAMMING for program design, DASHBOARD for the frontend, ARCHITECTURE for the code map, SCIENCE for evidence, AUDIT for data quality, ISSUES for agent behavior, MEMORY for training state.
- AGENTS.md, the agent map. constants.json, the evidence numbers.
- dashboard, the Cloudflare Worker frontend, live at https://reps.bojan-dev.workers.dev.
- tests, the deterministic pytest suite for everything the backend enforces.
