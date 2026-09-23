"""reps.mcp package: MCP is the sole normal agent interface to Reps."""

from .server import call_tool, list_tool_names, mcp

__all__ = ["call_tool", "list_tool_names", "mcp"]
