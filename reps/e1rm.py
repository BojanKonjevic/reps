# SSOT owner: e1RM formula. Consumers: SQL UDF e1rm(w, r), snapshot fields, tests as literal oracles.

"""Single definition of the Epley-style e1RM used everywhere."""

import math


MAX_E1RM_REPS = 30
MAX_WEIGHT = 1000.0


def _check_weight(weight) -> float:
    try:
        w = float(weight)
    except (TypeError, ValueError):
        from .errors import RepsError
        raise RepsError("weight must be a number")
    if not math.isfinite(w):
        from .errors import RepsError
        raise RepsError("weight must be finite (nan/inf rejected)")
    if w < 0:
        # ValueError keeps the SQL UDF path from surfacing as a raw
        # OperationalError traceback; domain entry points convert to RepsError.
        raise ValueError("weight cannot be negative")
    if w > MAX_WEIGHT:
        from .errors import RepsError
        raise RepsError(f"weight {w:g}kg is implausible (over {MAX_WEIGHT:g}kg), confirm the value")
    return w


def _check_reps(reps) -> int:
    if isinstance(reps, bool):
        from .errors import RepsError
        raise RepsError("reps must be an integer")
    try:
        r = int(reps)
    except (TypeError, ValueError):
        from .errors import RepsError
        raise RepsError("reps must be an integer")
    if isinstance(reps, float) and r != reps:
        from .errors import RepsError
        raise RepsError("reps must be an integer")
    if r <= 0:
        raise ValueError("reps must be a positive integer")
    return r


def e1rm(weight, reps) -> float:
    """Estimated one-rep max. reps == 1 returns weight unchanged."""
    w = _check_weight(weight)
    r = _check_reps(reps)
    if r == 1:
        return float(w)
    return float(w) * (1 + r / 30.0)


def check_weight_entry(weight) -> float:
    """Domain entry-point weight check: finite, non-negative, plausible bound."""
    from .errors import RepsError
    try:
        w = _check_weight(weight)
    except ValueError as e:
        raise RepsError(str(e))
    return w


def check_reps_entry(reps) -> int:
    """Domain entry-point reps check: positive integer."""
    from .errors import RepsError
    try:
        return _check_reps(reps)
    except ValueError as e:
        raise RepsError(str(e))


def cap_reps() -> int:
    """Max reps counting toward e1RM-derived decisions (constants.json tunable)."""
    try:
        from .constants import load_constants
        v = getattr(load_constants().thresholds, "e1rm_cap_reps", 12)
        return int(v)
    except Exception:
        return 12


def is_e1rm_counting_set(reps) -> bool:
    """True when a set's reps are in-domain for Epley comparisons (reps <= cap)."""
    try:
        return int(reps) <= cap_reps()
    except (TypeError, ValueError):
        return False


def e1rm_for_comparison(weight, reps):
    """e1RM for PR/progression/stall/slip/goal decisions, or None when out-of-domain."""
    if not is_e1rm_counting_set(reps):
        return None
    return e1rm(weight, reps)
