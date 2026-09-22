#!/usr/bin/env python3
"""reps: workout log. Code owns what is derivable or enforceable, the agent owns what is judgment.

CLI entry point. The implementation lives in the reps/ package; this module
re-exports its surface so `python log.py ...` and `import log` keep working.
"""

from reps import *  # noqa: F401,F403
from reps.cli import main  # noqa: F401

if __name__ == "__main__":
    main()
