"""reps.errors: explicit domain/application exceptions.

Domain operations refuse expected failures by raising RepsError, never by
exiting the process. The message is agent-facing: it names what was
refused and the fix. MCP translates these into error results; log.py (the
maintenance boundary) prints them and exits nonzero. Anything else
(bugs, sqlite errors) propagates as-is.
"""


class RepsError(Exception):
    """Expected domain refusal: invalid input, missing row, or a business
    invariant (mapping authority, end gate, MEV floor, holds)."""
