# SSOT owner: week bucketing (Monday-start ISO weeks). Consumers: volume, audit, signals, snapshot.

"""One week-bucketing implementation. Monday-start ISO weeks, always."""

from datetime import date, timedelta


def monday_of(day: date) -> date:
    """Monday starting the ISO week containing day."""
    return day - timedelta(days=day.weekday())


def week_starts(n: int, today=None) -> list[str]:
    """Oldest-first ISO dates of the Mondays starting the last n weeks (incl. this one)."""
    today = today or date.today()
    base = monday_of(today)
    return [((base - timedelta(weeks=n - 1 - i)).isoformat()) for i in range(n)]


def week_start_of(day_iso: str) -> str:
    """Monday-start bucket key for an ISO date string."""
    return monday_of(date.fromisoformat(day_iso)).isoformat()


def weekly_counts(dates: list[str], starts: list[str]) -> list[int]:
    """Count date strings per week bucket. Dates outside the window are ignored."""
    idx = {s: i for i, s in enumerate(starts)}
    out = [0] * len(starts)
    for d in dates:
        try:
            key = week_start_of(d)
        except ValueError:
            continue
        if key in idx:
            out[idx[key]] += 1
    return out
