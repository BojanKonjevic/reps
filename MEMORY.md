# memory

Durable training memory: injuries, sleep, life context, monthly rollups. Program config and goals live in SQLite (read via `plan`, `split show`, `map show`, `goal show`). Keep it short, current state only.

## State

Bodyweight, injuries, sleep, motivation notes that carry over. One line each, newest last.

- Sep 18 2026: no scale at home, bodyweight measured on gym scale (not fasted, less consistent, not every day).
- Sep 20 2026: block plan. Weeks 1-6 flat to failure on U1-U4/L1-L2, no goals, no prios, calibrate RIR by predicting then verifying to failure. Week 7 deload. Then build RIR tracking plus mesocycle planning into log.py, and plan the next 6 weeks with a mesocycle, few prios and goals.

## Monthly rollups

One short block per month, written on request at month end. Trend plus caveats, not raw sets. Raw sets stay in SQLite.
