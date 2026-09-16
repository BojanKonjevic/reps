# reps

Chat first training log. Talk in t3code, agent stores via `log.py` into local SQLite.

See AGENTS.md for the agent protocol. Dashboard lives in `dashboard/` as a read only Cloudflare Worker at https://reps.bojan-dev.workers.dev/ over snapshots pushed with `log.py sync`. Morning weight goes in with `log.py weigh`.
