# SSOT owner: personal-record definition. Consumers: snapshot is_pr, session reports, MCP.
# Definition: order by (created, id); first set per exercise is baseline (not a PR);
# a PR is strictly greater e1RM than the running best.

"""Single PR computation."""

from .e1rm import e1rm


def personal_records(sets: list[dict]) -> dict:
    """Map set id -> bool is_pr for one exercise's sets in chronological order.

    Caller passes sets for a single exercise ordered by (created, id).
    First set is baseline (False). Later sets are True iff e1RM strictly
    exceeds the running best before them.
    """
    ordered = sorted(sets, key=lambda s: (s.get("created", ""), s.get("id", 0)))
    out: dict = {}
    best = None
    for i, s in enumerate(ordered):
        v = e1rm(s["weight"], s["reps"])
        if i == 0:
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
