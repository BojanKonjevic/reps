# SSOT owner: typed domain results and refusals. Consumers: MCP tools, log.py.
# Tool names referenced from code travel as Fix(tool=...) and are verified
# against the MCP registry at import time (tests/test_docs.py).

"""reps.errors: explicit domain/application exceptions.

Domain operations refuse expected failures by raising RepsError, never by
exiting the process. The message is agent-facing: it names what was
refused and the fix. MCP translates these into error results; log.py (the
maintenance boundary) prints them and exits nonzero. Anything else
(bugs, sqlite errors) propagates as-is.
"""

from dataclasses import dataclass, field


class RepsError(Exception):
    """Expected domain refusal: invalid input, missing row, or a business
    invariant (mapping authority, end gate, MEV floor, holds)."""


@dataclass(frozen=True)
class Fix:
    """A validated tool reference: the fix for a refusal.

    `tool` must name a registered MCP tool; `args` are its arguments;
    `detail` is free human text appended after the rendered call.
    Renders as "call `tool` with ..." from the real name, never prose
    that invents a command syntax.
    """

    tool: str
    args: dict = field(default_factory=dict)
    detail: str = ""

    def render(self) -> str:
        if self.args:
            rendered = f"call `{self.tool}` with " + ", ".join(
                f"{k} {v!r}" for k, v in self.args.items())
        else:
            rendered = f"call `{self.tool}`"
        return f"{rendered} {self.detail}".rstrip() if self.detail else rendered


@dataclass
class Refusal(RepsError):
    """A structured refusal: machine-readable code, human message, optional fix."""

    code: str = ""
    message: str = ""
    fix: Fix | None = None

    def __post_init__(self) -> None:
        Exception.__init__(self, self.message or self.code)

    def __str__(self) -> str:
        base = self.message or self.code
        if self.fix is not None:
            return f"{base} ({self.fix.render()})"
        return base


@dataclass(frozen=True)
class GateItem:
    """One session_end gate item: what blocks, how to fix, whether force skips it."""

    item: str
    fix: Fix
    hard: bool = False

    def as_dict(self) -> dict:
        out = {"item": self.item, "fix": self.fix.render(),
               "fix_tool": self.fix.tool, "fix_args": dict(self.fix.args)}
        if self.hard:
            out["hard"] = True
        return out


@dataclass(frozen=True)
class GateReport:
    """Typed session_end gate result: empty items means ready to close."""

    workout_id: int
    items: tuple = ()

    @property
    def ready(self) -> bool:
        return not self.items

    def as_dict(self) -> dict:
        return {"ready": self.workout_id, "items": [i.as_dict() for i in self.items]}
