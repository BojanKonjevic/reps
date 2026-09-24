# SSOT owner: closed vocabularies (workout status, verdict, direction, tier, deload scope,
# adherence status, severity, volume status, split variant, autoreg action, rule/goal status).
# Consumers: SQL CHECK lists (generated in db.SCHEMA assembly), Pydantic Literals,
# MCP tool schemas, generated Zod. Consumers derive, never redefine.

"""Single definition of every closed vocabulary."""

from enum import Enum


class StrEnum(str, Enum):
    def __str__(self) -> str:  # keep JSON/tool payloads as plain strings
        return self.value


class WorkoutStatus(StrEnum):
    OPEN = "open"
    DONE = "done"
    REST = "rest"


class Verdict(StrEnum):
    HIT = "hit"
    MISS = "miss"
    HOLD = "hold"
    BASELINE = "baseline"


class Direction(StrEnum):
    UP = "up"
    FLAT = "flat"
    DOWN = "down"


class PriorityTier(StrEnum):
    PRIORITY = "priority"
    MAINTAIN = "maintain"
    DEPRIORITIZE = "deprioritize"


class DeloadScope(StrEnum):
    LIFT = "lift"
    SLOT = "slot"


class AdherenceStatus(StrEnum):
    DONE = "done"
    SWAPPED = "swapped"
    EXTRA = "extra"
    REST_OK = "rest_ok"
    REST_LOGGED = "rest_logged"
    MISSED = "missed"


class Severity(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class VolumeStatus(StrEnum):
    BELOW_MEV = "below_mev"
    IN_RANGE = "in_range"
    ABOVE_MRV = "above_mrv"


class SplitVariant(StrEnum):
    ACTIVE = "active"
    BASELINE = "baseline"


class AutoregAction(StrEnum):
    TRIM = "trim"
    SWAP = "swap"
    ADD = "add"


class RuleStatus(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


class GoalStatus(StrEnum):
    ACTIVE = "active"
    DROPPED = "dropped"
    DONE = "done"


class MarkKind(StrEnum):
    GOAL = "goal"
    STALLING = "stalling"
    SLIPPING = "slipping"
    FOCUS = "focus"
    AUTOREG = "autoreg"
    GROUPED = "grouped"


def values(enum_cls) -> list[str]:
    return [m.value for m in enum_cls]
