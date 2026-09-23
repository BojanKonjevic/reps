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

from typing import Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, StrictFloat, StrictInt, StrictStr, field_validator, model_validator


class MuscleEntry(BaseModel):
    """Per-muscle dose landmarks. mav/mrv stay optional: some groups
    (e.g. forearms) have no trusted landmarks, plan falls back to mev."""

    model_config = ConfigDict(extra="allow", strict=False)

    mev: StrictInt = Field(ge=0)
    mav: Optional[list[Union[StrictInt, StrictFloat]]] = None
    mrv: Optional[Union[StrictInt, StrictFloat]] = None
    freq: list[Union[StrictInt, StrictFloat]] = Field(min_length=2, max_length=2)
    tier: Literal["settled", "contested", "opinion"]
    source: StrictStr
    color: StrictStr = Field(pattern=r"#[0-9a-fA-F]{6}")

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


class ConstantsModel(BaseModel):
    """Canonical validated form of constants.json."""

    model_config = ConfigDict(extra="allow")

    version: StrictInt = 1
    muscles: dict[str, MuscleEntry] = Field(min_length=1)
    untracked: list[StrictStr] = Field(default_factory=list)
    rep_bands: list[RepBand] = Field(min_length=1)
    thresholds: Thresholds
    explained_keywords: list[StrictStr] = Field(default_factory=list)
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


class SnapshotWorkout(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: StrictInt
    date: StrictStr
    status: StrictStr
    notes: StrictStr = ""


class SnapshotSet(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: StrictInt
    workout_id: StrictInt
    exercise: StrictStr
    weight: Union[StrictInt, StrictFloat]
    reps: StrictInt
    note: StrictStr = ""
    created: StrictStr = ""
    muscles: StrictStr = ""


class SnapshotBodyweight(BaseModel):
    model_config = ConfigDict(extra="allow")

    date: StrictStr
    kg: Union[StrictInt, StrictFloat]
    note: StrictStr = ""


class SnapshotVolumeEntry(BaseModel):
    model_config = ConfigDict(extra="allow")

    weekly: list[Union[StrictInt, StrictFloat]]
    mev: Union[StrictInt, StrictFloat]
    mav: Optional[list[Union[StrictInt, StrictFloat]]] = None
    mrv: Optional[Union[StrictInt, StrictFloat]] = None
    freq: Optional[list[Union[StrictInt, StrictFloat]]] = None
    status: StrictStr


class SnapshotAnchor(BaseModel):
    model_config = ConfigDict(extra="allow")

    date: StrictStr
    index: StrictInt


class SnapshotAdherence(BaseModel):
    model_config = ConfigDict(extra="allow")

    anchor: Optional[SnapshotAnchor] = None
    days: list = Field(default_factory=list)
    drift: bool = False
    drift_days: Union[StrictInt, StrictFloat] = 0
    drift_threshold: Union[StrictInt, StrictFloat] = 0


class SnapshotAutoreg(BaseModel):
    model_config = ConfigDict(extra="allow")

    permitted: bool
    holds: list = Field(default_factory=list)
    miss_streaks: list = Field(default_factory=list)
    drop_watch: list = Field(default_factory=list)
    grouped: dict = Field(default_factory=dict)
    program_volume: dict = Field(default_factory=dict)


class SnapshotModel(BaseModel):
    """Canonical validated form of the synchronized dashboard payload.

    Core fact collections are required; forward-evolved sections default
    so an older payload still parses where the dashboard renders
    null-safe. Unknown top-level sections are tolerated (extra="allow")
    so the backend can extend the snapshot without breaking validation.
    """

    model_config = ConfigDict(extra="allow")

    exported: StrictStr
    workouts: list[SnapshotWorkout]
    sets: list[SnapshotSet]
    bodyweight: list[SnapshotBodyweight] = Field(default_factory=list)
    split_active: list = Field(default_factory=list)
    rotation: list[StrictStr] = Field(default_factory=list)
    constants: Optional[ConstantsModel] = None
    progression: dict = Field(default_factory=dict)
    goals: list = Field(default_factory=list)
    priority: dict = Field(default_factory=dict)
    deload: list = Field(default_factory=list)
    rules: list = Field(default_factory=list)
    flags: list = Field(default_factory=list)
    mapping: list = Field(default_factory=list)
    movement_notes: list = Field(default_factory=list)
    adherence: Optional[SnapshotAdherence] = None
    signals: list = Field(default_factory=list)
    autoreg: Optional[SnapshotAutoreg] = None
    autoreg_changes: list = Field(default_factory=list)
    volume: dict[str, SnapshotVolumeEntry] = Field(default_factory=dict)


class SnapshotValidationError(ValueError):
    """Raised when a built snapshot fails schema validation (a bug: the
    sync layer must not publish an arbitrary dict)."""


def validate_snapshot(payload):
    """Validate a snapshot candidate against SnapshotModel.

    Returns the validated SnapshotModel. Raises SnapshotValidationError
    with the first defect; unknown sections are tolerated, known shapes
    are strict.
    """
    from pydantic import ValidationError as _ValidationError

    try:
        return SnapshotModel.model_validate(payload)
    except _ValidationError as e:
        first = e.errors()[0]
        loc = ".".join(str(p) for p in first["loc"]) if first.get("loc") else "root"
        raise SnapshotValidationError(f"snapshot invalid: {loc}: {first['msg']}")
