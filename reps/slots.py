# SSOT owner: slot match ("which split day was this session") and next slot in rotation.
# Consumers: plan, adherence, sessions.best_split_day, snapshot next_up/calendar.
# Tie rule: a tie is None (ambiguous) with candidates listed, never silent first-wins.

"""Single slot-matching and rotation-walk implementation."""


def slot_of_session(exercises: list[str], days: dict) -> dict:
    """Match a session's exercises against split days.

    Returns {"day": str | None, "candidates": [...], "score": int}.
    A tie (or no overlap) yields day None with all top-scoring candidates.
    """
    trained = set(exercises)
    scored = [(day, len(trained & set(moves))) for day, moves in days.items()]
    scored = [(d, s) for d, s in scored if s > 0]
    if not scored:
        return {"day": None, "candidates": [], "score": 0}
    best = max(s for _, s in scored)
    cands = sorted(d for d, s in scored if s == best)
    if len(cands) == 1:
        return {"day": cands[0], "candidates": cands, "score": best}
    return {"day": None, "candidates": cands, "score": best}


def next_slot(last_day, rotation: list) -> dict:
    """Day following last_day in rotation, skipping rest entries.

    Returns {"day": str | None, "basis": str}. None when rotation is
    empty/unparseable or last_day is not in it.
    """
    if not rotation or not last_day:
        return {"day": None, "basis": "no rotation or no last day"}
    try:
        idx = list(rotation).index(last_day)
    except ValueError:
        return {"day": None, "basis": f"{last_day} not in rotation"}
    skipped = []
    j = (idx + 1) % len(rotation)
    guard = 0
    while str(rotation[j]).lower() == "rest" and guard < len(rotation):
        skipped.append(rotation[j])
        j = (j + 1) % len(rotation)
        guard += 1
    if guard >= len(rotation):
        return {"day": None, "basis": "rotation is all rest"}
    basis = f"last trained {last_day}, rotation {last_day}->{rotation[j]}"
    if skipped:
        basis += " (rest day sits between)"
    return {"day": rotation[j], "basis": basis}
