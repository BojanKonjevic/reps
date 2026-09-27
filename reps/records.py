# SSOT owner: personal-record definition. Consumers: snapshot is_pr, session reports, MCP.
# Definition: order by (created, id); first set per exercise is baseline (not a PR);
# a PR is strictly greater e1RM than the running best.

"""Single PR computation."""

from .e1rm import e1rm, is_e1rm_counting_set


def personal_records(sets: list[dict]) -> dict:
    """Map set id -> bool is_pr for one exercise's sets in chronological order.

    Caller passes sets for a single exercise ordered by (created, id).
    First counting set is baseline (False). Later counting sets are True iff
    e1RM strictly exceeds the running best before them. Sets above the
    e1RM rep cap (>12, out-of-domain for Epley) never PR and never move the
    running best: they are stored and charted as raw volume, excluded from
    every e1RM-derived decision.
    """
    ordered = sorted(sets, key=lambda s: (s.get("created", ""), s.get("id", 0)))
    out: dict = {}
    best = None
    for s in ordered:
        if not is_e1rm_counting_set(s["reps"]):
            out[s["id"]] = False
            continue
        v = e1rm(s["weight"], s["reps"])
        if best is None:
            out[s["id"]] = False
            best = v
        else:
            out[s["id"]] = bool(v > best)
            if v > best:
                best = v
    return out


def last_pr_date(sets: list[dict]) -> str | None:
    """Date (workout date on each set dict as 'date') of the last PR, or None."""
    flags = personal_records(sets)
    last = None
    for s in sorted(sets, key=lambda s: (s.get("created", ""), s.get("id", 0))):
        if flags.get(s["id"]):
            last = s.get("date")
    return last
