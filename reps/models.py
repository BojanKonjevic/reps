"""reps.models: canonical Pydantic representations of structured Reps data.

This module owns structural validation. Business rules live in the domain
modules (sessions, program, plan, ...), never here.

Two boundaries are modelled:

- ``ConstantsModel``: validates constants.json, the single source of truth
  for taxonomy and thresholds. Replaces procedural type-checking with
  declarative field constraints; cross-field invariants use explicit
  validators.
- ``SnapshotModel``: validates the synchronized dashboard payload built by
  reps.sync.build_snapshot before publication. Unknown sections are
  tolerated (forward compatibility: the worker serves the last synced
  payload, which can predate new fields); known fields and their shapes
  are validated strictly so a malformed snapshot fails loudly instead of
  propagating arbitrary JSON to TypeScript.

Strictness is deliberate: strict scalar types reject silent coercion
(e.g. bools where ints belong, strings where numbers belong) that could
hide invalid Reps data.
"""

from typing import Optional, Union

from .vocab import (AdherenceStatus, AutoregAction, CalendarKind, DeloadScope,
                     Direction, EvidenceTier, GoalStatus, HistoryDomain, MarkKind, PriorityTier,
                     RuleStatus, Severity, Verdict, VolumeStatus, WorkoutStatus)

from pydantic import BaseModel, ConfigDict, Field, StrictFloat, StrictInt, StrictStr, field_validator, model_validator


class MuscleEntry(BaseModel):
    """Per-muscle dose landmarks. mav/mrv stay optional: some groups
    (e.g. forearms) have no trusted landmarks, plan falls back to mev."""

    model_config = ConfigDict(extra="allow", strict=False)

    mev: StrictInt = Field(ge=0)
    mav: Optional[list[Union[StrictInt, StrictFloat]]] = None
    mrv: Optional[Union[StrictInt, StrictFloat]] = None
    freq: list[Union[StrictInt, StrictFloat]] = Field(min_length=2, max_length=2)
    tier: EvidenceTier
    source: StrictStr
    color: StrictStr = Field(pattern=r"^#[0-9a-fA-F]{6}$")

    @field_validator("mav")
    @classmethod
    def _mav_pair(cls, v):
        if v is None:
            return v
        if len(v) != 2 or v[0] > v[1]:
            raise ValueError("mav must be [lo, hi] with lo <= hi")
        return v

    @field_validator("mrv")
    @classmethod
    def _mrv_non_negative(cls, v):
        if v is not None and v < 0:
            raise ValueError("mrv must be non-negative")
        return v

    @field_validator("freq")
    @classmethod
    def _freq_pair(cls, v):
        if v[0] > v[1]:
            raise ValueError("freq must be [lo, hi] with lo <= hi")
        return v


class RepBand(BaseModel):
    """One progression jump band. Both fields null is the open-ended
    terminator above the top band; otherwise max_reps ascends and
    jump_pct is positive."""

    model_config = ConfigDict(extra="allow")

    max_reps: Optional[StrictInt] = None
    jump_pct: Optional[Union[StrictInt, StrictFloat]] = None

    @model_validator(mode="after")
    def _both_or_neither(self):
        if (self.max_reps is None) != (self.jump_pct is None):
            raise ValueError("rep_bands entries need both max_reps and jump_pct, or neither (terminator)")
        if self.max_reps is not None and self.max_reps <= 0:
            raise ValueError("rep_bands max_reps must be positive")
        if self.jump_pct is not None and self.jump_pct <= 0:
            raise ValueError("rep_bands jump_pct must be positive")
        return self


class Thresholds(BaseModel):
    """Numeric guardrails. Only the invariants the backend enforces are
    constrained here; keys the code reads opaquely stay permissive."""

    model_config = ConfigDict(extra="allow")

    stale_workout_hours: Union[StrictInt, StrictFloat] = Field(gt=0)
    stale_workout_days: Union[StrictInt, StrictFloat] = Field(gt=0)
    break_days: Union[StrictInt, StrictFloat] = Field(gt=0)
    e1rm_warn_ratio: Union[StrictInt, StrictFloat] = Field(gt=0)
    duplicate_name_distance: Union[StrictInt, StrictFloat] = Field(gt=0)
    volume_window_weeks: StrictInt = Field(gt=0)
    volume_bad_weeks: StrictInt = Field(gt=0)
    ledger_retention_days: StrictInt = Field(gt=0)
    default_new_slot_sets: StrictInt = Field(gt=0)
    adherence_drift_days: StrictInt = Field(gt=0)
    progression_drop_pct: Union[StrictInt, StrictFloat] = Field(lt=0)
    deload_watch_pct: Union[StrictInt, StrictFloat] = -5
    goal_divergence_pct: Union[StrictInt, StrictFloat] = 5
    stall_window_sessions: StrictInt = 3
    stall_decline_pct: Union[StrictInt, StrictFloat] = 1.0
    stall_flat_sessions: StrictInt = 6
    stall_min_sessions: StrictInt = 4
    bodyweight_gap_days: StrictInt = 14
    bodyweight_avg_days: StrictInt = 7
    recent_notes_count: StrictInt = 6
    trend_top_lifts: StrictInt = 8
    deload_volume_reduction: list[Union[StrictInt, StrictFloat]] = Field(
        default_factory=lambda: [0.4, 0.6])


class ConstantsModel(BaseModel):
    """Canonical validated form of constants.json."""

    model_config = ConfigDict(extra="allow")

    version: StrictInt = 1
    muscles: dict[str, MuscleEntry] = Field(min_length=1)
    untracked: list[StrictStr] = Field(default_factory=list)
    rep_bands: list[RepBand] = Field(min_length=1)
    thresholds: Thresholds
    explained_keywords: list[StrictStr] = Field(
        default_factory=lambda: ["deload", "return", "program change", "injury",
                                 "technique", "sick", "travel"])
    rep_scheme_default: list[StrictInt] = Field(default_factory=lambda: [3, 8])

    @model_validator(mode="after")
    def _bands_ascend(self):
        prev = -1
        for band in self.rep_bands:
            if band.max_reps is None:
                continue
            if band.max_reps <= prev:
                raise ValueError("rep_bands must order ascending max_reps")
            prev = band.max_reps
        return self



Real = Union[StrictInt, StrictFloat]

SNAPSHOT_SCHEMA_VERSION = 2

STRICT = ConfigDict(extra="forbid")


class LiftSession(BaseModel):
    """One trained date for a lift: top set, its e1RM, PR flag, delta vs prior best."""

    model_config = STRICT

    date: StrictStr
    workout_id: StrictInt
    weight: Real
    reps: StrictInt
    e1rm: Real
    is_pr: bool
    delta_e1rm: Optional[Real]


class LiftBest(BaseModel):
    model_config = STRICT

    weight: Real
    reps: StrictInt
    e1rm: Real
    date: StrictStr


class LiftLast(BaseModel):
    model_config = STRICT

    weight: Real
    reps: StrictInt
    date: StrictStr


class LiftProgression(BaseModel):
    model_config = STRICT

    verdict: Verdict
    next: StrictStr
    next_weight: Real
    next_reps: StrictInt
    direction: Direction
    note: StrictStr
    next_e1rm: Real


class LiftMark(BaseModel):
    """Structured mark: kind plus payload, no display text (present.ts renders)."""

    model_config = STRICT

    kind: MarkKind
    payload: dict[str, Union[StrictStr, StrictInt, StrictFloat, bool, None]]


class Lift(BaseModel):
    model_config = STRICT

    exercise: StrictStr
    muscles: list[StrictStr]
    notes: list[StrictStr]
    sessions: list[LiftSession]
    best: Optional[LiftBest]
    last: Optional[LiftLast]
    last_pr_date: Optional[StrictStr]
    days_since_pr: Optional[StrictInt]
    progression: Optional[LiftProgression]
    goal_id: Optional[StrictInt]
    tags: list[StrictStr]
    marks: list[LiftMark]
    rank_default: StrictInt
    rank_attention: StrictInt


class MuscleBands(BaseModel):
    model_config = STRICT

    mev: Real
    mav: Optional[list[Real]]
    mrv: Optional[Real]


class MuscleLiftShare(BaseModel):
    model_config = STRICT

    exercise: StrictStr
    sets: StrictInt
    share: StrictFloat


class Muscle(BaseModel):
    model_config = STRICT

    muscle: StrictStr
    bands: MuscleBands
    weekly: list[StrictInt]
    status: VolumeStatus
    tier: PriorityTier
    grouped: list[StrictStr]
    lift_share: list[MuscleLiftShare]
    trained_weeks: StrictInt
    avg_recent: Real


class SetView(BaseModel):
    """One set, embedded once, inside its session.

    Short keys: sets are the only unbounded collection and dominate the
    payload budget (under 1.5 MB for 3 years of daily training).
    """

    model_config = STRICT

    n: StrictInt
    w: Real
    r: StrictInt
    e: Real
    pr: bool
    note: StrictStr


class SessionExercise(BaseModel):
    model_config = STRICT

    exercise: StrictStr
    deload: bool
    sets: list[SetView]


class SessionView(BaseModel):
    model_config = STRICT

    date: StrictStr
    workout_id: StrictInt
    status: WorkoutStatus
    slot_label: Optional[StrictStr]
    notes: StrictStr
    exercises: list[SessionExercise]
    duration_min: Optional[Real]


class CalendarHover(BaseModel):
    model_config = STRICT

    lines: list[StrictStr]


class CalendarDay(BaseModel):
    model_config = STRICT

    date: StrictStr
    kind: CalendarKind
    slot_label: Optional[StrictStr]
    has_pr: bool
    break_after_gap: bool
    adherence_status: Optional[StrictStr]
    expected: Optional[StrictStr]
    hover: CalendarHover


class VolumeHistory(BaseModel):
    model_config = STRICT

    week_starts: list[StrictStr]
    by_muscle: dict[str, list[StrictInt]]


class BodyweightPoint(BaseModel):
    model_config = STRICT

    date: StrictStr
    kg: Real
    avg7: Optional[Real]
    gap_before: Optional[StrictInt]
    gap: bool


class ProgramSlot(BaseModel):
    model_config = STRICT

    slot: StrictInt
    moves: list[StrictStr]
    sets: StrictInt
    muscles: list[StrictStr]
    focus: list[StrictStr]


class ProgramDay(BaseModel):
    model_config = STRICT

    day: StrictStr
    muscles: list[StrictStr]
    slots: list[ProgramSlot]


class ProgramAnchor(BaseModel):
    model_config = STRICT

    date: StrictStr
    index: StrictInt


class ProgramView(BaseModel):
    model_config = STRICT

    rotation: list[StrictStr]
    anchor: Optional[ProgramAnchor]
    days: list[ProgramDay]


class NextUpRow(BaseModel):
    model_config = STRICT

    movement: StrictStr
    last: Optional[LiftLast]
    target: Optional[StrictStr]


class StatusView(BaseModel):
    """Today and break facts for the now-lines. TS reads, never computes."""

    model_config = STRICT

    open_today: bool
    rest_today: bool
    last_trained: Optional[StrictStr]
    break_days: Optional[StrictInt]
    on_break: bool


class NextUp(BaseModel):
    model_config = STRICT

    day: Optional[StrictStr]
    basis: StrictStr
    rows: list[NextUpRow]
    empty: Optional[StrictStr]


class GoalTop(BaseModel):
    model_config = STRICT

    weight: Real
    reps: StrictInt


class GoalActual(BaseModel):
    model_config = STRICT

    date: StrictStr
    e1rm: Real


class Goal(BaseModel):
    model_config = STRICT

    id: StrictInt
    exercise: StrictStr
    target_e1rm: Real
    target_desc: StrictStr
    deadline: StrictStr
    status: GoalStatus
    created: StrictStr
    checkpoints: list[Real]
    completed: StrictInt
    actuals: list[GoalActual]
    consecutive_misses: StrictInt
    on_track: bool
    remaining: StrictInt
    slippage: bool
    next_checkpoint: Optional[Real]
    percent: Optional[Real]
    top_by_date: dict[str, GoalTop]


class Priority(BaseModel):
    model_config = STRICT

    tier: PriorityTier
    since: StrictStr
    until: Optional[StrictStr]


class Deload(BaseModel):
    model_config = STRICT

    id: StrictInt
    scope: DeloadScope
    subject: StrictStr
    set_on: StrictStr
    cleared_on: Optional[StrictStr]


class Rule(BaseModel):
    model_config = STRICT

    id: StrictInt
    subject: StrictStr
    text: StrictStr
    start_date: StrictStr
    expiry: Optional[StrictStr]
    status: StrictStr = "active"
    created: StrictStr
    needs_confirm: bool


class Flag(BaseModel):
    model_config = STRICT

    id: StrictInt
    subject: StrictStr
    reason: StrictStr
    created: StrictStr
    consumed_at: Optional[StrictStr]


class MappingRow(BaseModel):
    model_config = STRICT

    exercise: StrictStr
    muscles: StrictStr
    is_bodyweight_only: StrictInt


class MovementNote(BaseModel):
    model_config = STRICT

    id: StrictInt
    exercise: StrictStr
    note: StrictStr
    created: StrictStr


class Signal(BaseModel):
    model_config = STRICT

    severity: Severity
    text: StrictStr


class AutoregHold(BaseModel):
    model_config = STRICT

    id: StrictInt
    day: StrictStr
    movements: StrictStr
    moves: list[StrictStr]
    action: AutoregAction
    set_on: StrictStr
    hold_until: StrictStr
    reason: StrictStr


class AutoregMissStreak(BaseModel):
    model_config = STRICT

    exercise: StrictStr
    streak: StrictInt


class AutoregDropWatch(BaseModel):
    model_config = STRICT

    exercise: StrictStr
    drops_pct: list[Real]


class AutoregChange(BaseModel):
    model_config = STRICT

    id: StrictInt
    date: StrictStr
    action: AutoregAction
    day: StrictStr
    slot: StrictInt
    before_movements: StrictStr
    before_moves: list[StrictStr]
    before_sets: StrictInt
    after_movements: StrictStr
    after_moves: list[StrictStr]
    after_sets: StrictInt
    evidence: StrictStr
    reverted_on: Optional[StrictStr]


class Autoreg(BaseModel):
    model_config = STRICT

    permitted: bool
    holds: list[AutoregHold]
    miss_streaks: list[AutoregMissStreak]
    drop_watch: list[AutoregDropWatch]
    grouped: dict[str, list[StrictStr]]
    program_volume: dict[str, Real]


class AdherenceDay(BaseModel):
    """One per-date rotation verdict from classify_date."""

    model_config = STRICT

    date: StrictStr
    expected: StrictStr
    trained: Optional[StrictStr]
    status: AdherenceStatus


class AdherenceWeek(BaseModel):
    model_config = STRICT

    week_start: StrictStr
    trained: StrictInt
    expected: StrictInt


class Adherence(BaseModel):
    model_config = STRICT

    anchor: Optional[ProgramAnchor]
    days: list[AdherenceDay]
    drift: bool
    drift_days: Real
    drift_threshold: Real
    weeks: list[AdherenceWeek]


class RecentNote(BaseModel):
    model_config = STRICT

    date: StrictStr
    text: StrictStr
    hot: bool


class ProgramSlotSnapshot(BaseModel):
    """One slot inside a program day snapshot (history before/after envelope)."""

    model_config = STRICT

    slot: StrictInt
    movements: StrictStr
    sets: StrictInt


class ProgramHistoryPayload(BaseModel):
    """Full day snapshot before/after a program edit (set/move/reconcile/revert)."""

    model_config = STRICT

    variant: StrictStr
    day: StrictStr
    slots: list[ProgramSlotSnapshot]


class PriorityHistoryPayload(BaseModel):
    """Priority tier before/after; all-None means no tier (maintain by absence)."""

    model_config = STRICT

    tier: Optional[PriorityTier]
    since: Optional[StrictStr]
    until: Optional[StrictStr]


class GoalHistoryPayload(BaseModel):
    """Goal trajectory before/after; action names which transition this envelope is."""

    model_config = STRICT

    goal_id: StrictInt
    exercise: StrictStr
    action: StrictStr
    checkpoints: Optional[list[Real]] = None
    target_e1rm: Optional[Real] = None
    deadline: Optional[StrictStr] = None
    status: Optional[GoalStatus] = None
    target_desc: Optional[StrictStr] = None


class DeloadHistoryPayload(BaseModel):
    model_config = STRICT

    scope: Optional[DeloadScope] = None
    subject: Optional[StrictStr] = None
    action: StrictStr
    active: Optional[bool] = None


class RuleHistoryPayload(BaseModel):
    model_config = STRICT

    rule_id: StrictInt
    action: StrictStr
    text: Optional[StrictStr] = None
    subject: Optional[StrictStr] = None
    expiry: Optional[StrictStr] = None
    status: Optional[RuleStatus] = None


class RotationHistoryPayload(BaseModel):
    """Rotation order and anchor before/after; None entries are rest.

    Order changes carry rotation with anchor fields None; anchor changes
    carry anchor_date/position with rotation None. The two live under
    separate history subjects ("rotation", "anchor") so folds stay homogeneous.
    """

    model_config = STRICT

    rotation: Optional[list[Optional[StrictStr]]] = None
    anchor_date: Optional[StrictStr] = None
    position: Optional[StrictInt] = None


_HISTORY_PAYLOADS = {
    HistoryDomain.PROGRAM.value: ProgramHistoryPayload,
    HistoryDomain.PRIORITY.value: PriorityHistoryPayload,
    HistoryDomain.GOAL.value: GoalHistoryPayload,
    HistoryDomain.DELOAD.value: DeloadHistoryPayload,
    HistoryDomain.RULE.value: RuleHistoryPayload,
    HistoryDomain.ROTATION.value: RotationHistoryPayload,
}


def validate_history_payload(domain: str, data: dict) -> dict:
    """Validate a state-change envelope against its domain shape (read path).

    Raises ValueError naming the defect; history._shape turns it into RepsError.
    """
    from pydantic import ValidationError as _ValidationError

    cls = _HISTORY_PAYLOADS.get(domain)
    if cls is None:
        raise ValueError(f"unknown history domain '{domain}'")
    if not isinstance(data, dict):
        raise ValueError("history payload must be an object")
    try:
        return cls.model_validate(data).model_dump()
    except _ValidationError as e:
        raise ValueError(first_error(e))


class SnapshotModel(BaseModel):
    """Canonical validated form of the synchronized dashboard payload (v2 views).

    Every field required, extra forbidden: Python always emits everything or
    fails loudly. The dashboard and worker consume generated schemas only.
    """

    model_config = STRICT

    schema_version: StrictInt
    exported: StrictStr
    as_of: StrictStr
    constants: ConstantsModel
    lifts: list[Lift]
    muscles: list[Muscle]
    sessions: list[SessionView]
    calendar: list[CalendarDay]
    volume_history: VolumeHistory
    bodyweight: list[BodyweightPoint]
    program: ProgramView
    status: StatusView
    next_up: NextUp
    goals: list[Goal]
    adherence: Optional[Adherence]
    signals: list[Signal]
    recent_notes: list[RecentNote]
    rules: list[Rule]
    flags: list[Flag]
    deload: list[Deload]
    priority: dict[str, Priority]
    autoreg: Optional[Autoreg]
    autoreg_changes: list[AutoregChange]


class SnapshotValidationError(ValueError):
    """Raised when a built snapshot fails schema validation (a bug: the
    sync layer must not publish an arbitrary dict)."""


def first_error(exc) -> str:
    """One-line location plus message for the first Pydantic defect."""
    from pydantic import ValidationError as _ValidationError

    assert isinstance(exc, _ValidationError)
    first = exc.errors()[0]
    loc = ".".join(str(p) for p in first["loc"]) if first.get("loc") else "root"
    return f"{loc}: {first['msg']}"


def validate_snapshot(payload: dict) -> SnapshotModel:
    """Validate a snapshot candidate against SnapshotModel.

    Returns the validated SnapshotModel. Raises SnapshotValidationError
    with the first defect.
    """
    from pydantic import ValidationError as _ValidationError

    try:
        return SnapshotModel.model_validate(payload)
    except _ValidationError as e:
        raise SnapshotValidationError(f"snapshot invalid: {first_error(e)}")
