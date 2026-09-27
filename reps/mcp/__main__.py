"""Stdio entry point: `python -m reps.mcp` serves Reps over MCP."""

import asyncio
import logging
import sys

from .server import mcp


def main() -> None:
    # Stderr only: stdout carries MCP stdio framing, never logs.
    logging.basicConfig(stream=sys.stderr, level=logging.WARNING,
                        format="reps-mcp %(levelname)s %(name)s: %(message)s")
    try:
        asyncio.run(mcp.run_stdio_async())
    except (BrokenPipeError, EOFError):
        # Transport went away; exit quietly so the harness sees a clean stop.
        try:
            sys.stderr.close()
        except Exception:
            pass
        sys.exit(0)
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
