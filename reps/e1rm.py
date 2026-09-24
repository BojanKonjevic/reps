# SSOT owner: e1RM formula. Consumers: SQL UDF e1rm(w, r), snapshot fields, tests as literal oracles.

"""Single definition of the Epley-style e1RM used everywhere."""


def e1rm(weight, reps) -> float:
    """Estimated one-rep max. reps == 1 returns weight unchanged."""
    weight = float(weight)
    reps = int(reps)
    if reps <= 0:
        raise ValueError("reps must be a positive integer")
    if reps == 1:
        return weight
    return weight * (1 + reps / 30.0)
