"""Stdio entry point: `python -m reps.mcp` serves Reps over MCP."""

import asyncio

from .server import mcp


def main() -> None:
    asyncio.run(mcp.run_stdio_async())


if __name__ == "__main__":
    main()
