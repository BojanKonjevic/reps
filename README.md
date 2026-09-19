# reps

Chat first training log. Talk in t3code, agent stores via `log.py` into local SQLite.

## Why this exists

Most training logs make you pick. Either a rigid tracker that stores every set perfectly and understands nothing, or a chatbot coach that talks well and remembers nothing.

reps does both at once. You talk the way you'd text a training partner. "Squat 90 5/5/7, last to failure" between sets, questions when you have them, done at the end. Underneath, every set lands in SQLite with exact weight, reps, muscles, and notes, and the same agent that logs also coaches: rep targets from your history, progression that adjusts when you miss, goals with session-by-session trajectories.

The combination is the point. Facts alone can't tell you what to do next, and agent reasoning left to itself drifts, misremembers, and invents. So the reasoning here runs on rails. The markdown pins down naming, progression, and protocol, and every claim has to ground out in stored sets. You get the judgment without the failure mode that usually comes with it.

The split is deliberate. The database holds facts, the markdown holds the rules, the agent does the thinking, and you just train and talk.

See AGENTS.md for the agent protocol. Dashboard lives in `dashboard/` as a read only Cloudflare Worker at https://reps.bojan-dev.workers.dev/ over snapshots pushed with `log.py sync`. Morning weight goes in with `log.py weigh`.
