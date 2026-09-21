# Programming

Program design: split, goals, priorities, deloads, evidence refreshes. Needed for planning and program changes, not for logging sets. Session mechanics live in `LOGGING.md`.

## Split

The splits table holds two variants. Baseline is the reference program and is never planned from. Active is the exact program: which day holds which exercises in which order, with working set counts. Read with `split show [day]`.

1. The active split takes routine updates (`split set`, `split move`, `split reconcile`). The baseline is rewritten only on explicit instruction for a major program change, via `split set --variant baseline`. Never infer either from one unusual session.
2. A one-off swap logs under the existing active slot and adds the alternate via `split set`. It never rewrites the program.
3. Session planning reads the active split first (`plan` includes the guessed day's slots): it defines what a full day contains.

## Goals (goal)

"goal", alone or in context, manages lifting goals. Multiple goals stay active at once, each wakes only on relevant sessions.

1. Realism gate first. Compare the target against current bests and the timeframe. Absurd goals get flagged in chat instantly and written nowhere. Sane goals get a trajectory via `goal add <exercise> --target <e1rm> --deadline <date>`.
2. On entry, convert the stated target to e1RM (a stated single counts as its own weight, never run through the formula) and reflect back what that implies across a few rep ranges for a sanity check before anything is written. Trajectories target e1RM over numbered sessions (session 1 is the already-logged baseline); prescriptions default to 3-8 reps, with true 1-3 rep tests reserved for the final 1-2 sessions before the deadline. Trajectories assume the same equipment throughout.
3. Evolution: on every relevant log, re-read `goal show`, compare reality to plan, run `goal rewrite <id>` to re-anchor the remaining trajectory off new data. Exact match means leave it alone.
4. Slippage: when `goal show` reports slippage, ask whether to extend the deadline or compress the jumps. Never silently compress.
5. Split changes remap the remaining session numbers to the new days, the sequence itself survives.

## Suggest (suggest)

"suggest", alone or with context, means propose goals. The agent picks them, the user approves them.

1. Pull as much history as needed for a confident read: `plan`'s progression for live momentum, then `range` and `history` back until trends are clear, not a fixed window. Thin history means fewer suggestions or none, said honestly.
2. Propose several concrete goals: movement, exact target, deadline. Each one already realism checked, with one line on why it fits.
3. Nothing is written until the user picks. Approval converts straight into the Goals flow with a trajectory.

## Prioritize (prioritize)

`prioritize <muscle> [for <duration>]`, in plain words ("side delts for the next 3 months", "bring up hamstrings"). Fully specified requests execute in the same response. Open requests get a short thread first: state the current picture from data, ask only what the recommendation depends on, then propose order plus sets plus frequency verdict with one line of reason each, and execute on confirm.

1. Resolve the muscle first: delt heads track separately, so "delts" alone gets asked which head. Untracked groups (neck, calves, traps) are refused, or tracked first per the mapping rule.
2. Rewrite the active split with `split move` (position) and `split set` (set counts): the muscle's lifts move to position 1, second at worst, in every slot containing them. If another focus is already active, ask how to order the two before rewriting. Their set counts go up; other accessories in the same slots drop a set or hold (never to zero) so total session volume stays roughly flat. Baseline split is untouched and never planned from. If a workout is open, the rewrite takes effect next session unless the user says to apply it now.
3. Write one Active rule via `rule add <text> --subject <muscle> [--expires <date>]` carrying the intent. In the same step, run `priority set <muscle> <tier> [--until <date>]` (`priority` / `maintain` / `deprioritize`, no `--until` for standing; absence means `maintain`). Prose rule and table entry always stay in sync. Expiry flows into Needs confirm for the renew-or-revert moment.
4. Check `goal show` for a goal covering that muscle (any lift training it counts). If none exists, auto-run the suggest flow scoped to that muscle. A pick converts into a trajectory per the normal Goals flow. Declining is legitimate: the split rewrite and notes stand without a goal.
5. Downstream needs no new rules: planning reads the rewritten split directly; the focus Active rule exempts that muscle from ledger volume holds; the Priority tier breaks ties for slack volume but never overrides a Goal trajectory; reordered sessions are marked in the `end` note with conservative progression verdicts on displaced lifts; revert means restoring baseline lines on request.

## Deload

Deloads are state, not just narration. Scope is per lift (`deload set --scope lift <exercise>`) or per slot (`--scope slot <day>`).

1. Watch: per `constants` deload_watch_pct, two consecutive same-slot drops mean one more like this triggers a reactive deload per SCIENCE.md. Rare by design.
2. While active, affected lifts train at reduced volume per SCIENCE.md deload guidance, trajectories resume next session. Planning reads deload state from `plan` and it outranks everything except Active rules and injuries.
3. The `end` note for a session trained under Deload state must include the word `deload` (the gate enforces this). After `end` completes, run `deload clear` (it appends the dated State line itself).

## Split review (review the split)

"review the split" or similar phrases triggers a check of the Active split against SCIENCE.md's existing exercise-selection evidence. Process:

1. For each slot in the Active split, cross-check it against SCIENCE.md's Exercise selection principles table and the Personal deviations section. A deviation already on file means no flag. Also run `priority list`: a `priority` tier muscle whose slots don't reflect that emphasis gets flagged here too.
2. For anything flagged, propose a specific swap or addition with the principle cited, same evidentiary rigor SCIENCE.md itself uses.
3. Present all proposed changes together. Nothing is written until the user approves.
4. On approval, this is "the user says the split changed" per Split rule 1: rewrite the Active split through that exact mechanism, no parallel edit path. One-off sessions still never trigger a program change on their own.
5. This only runs when invoked by name. It is never automatic and never suggested unprompted.

This is distinct from "audit the research" and "audit the data". Each trigger does exactly one job.

## Evidence refresh (audit the research)

"audit the research" or similar phrases triggers a refresh of SCIENCE.md. Process:

1. Search for recent (ideally last 2–3 years) meta-analyses and systematic reviews on each topic SCIENCE.md covers.
2. Weigh findings using the trust hierarchy in SCIENCE.md's header.
3. For each entry: if new evidence shifts the tier or the number, propose the change with citation (author/group + year). Conflicting findings → state the range and why, keep Contested tier.
4. Present proposed changes for approval. Nothing overwrites silently. On approval, rewrite the affected sections and `constants.json` in the same step, update "last reviewed" date.
5. Personal deviations section is never touched by this process; only I add there.

This is distinct from data-quality audits or compaction. It only refreshes the external evidence base.
