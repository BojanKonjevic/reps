#!/usr/bin/env python3
"""Architectural guardrails: prevent regression into the old CLI design.

These tests pin intent, not style. Each one maps to a convergence-spec
requirement: one agent interface (MCP), one domain implementation with
structured returns, explicit models, no dead legacy.
"""

import asyncio
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
REPS = ROOT / "reps"


def _sources():
    return [p for p in REPS.rglob("*.py") if "__pycache__" not in p.parts]


def test_no_cmd_terminology_in_domain():
    """Command names existed only for the shell interface."""
    for p in _sources():
        text = p.read_text()
        assert "cmd_" not in text, f"{p.name} still uses cmd_ terminology"


def test_no_process_exit_in_domain():
    """Refusals are RepsError; only log.py owns process termination."""
    offenders = [p.name for p in _sources()
                 if p.name != "__main__.py" and "sys.exit" in p.read_text()]
    assert offenders == [], f"sys.exit in domain layer: {offenders}"


def test_no_stdout_api_in_domain_or_mcp():
    """Domain returns values; MCP never captures stdout."""
    offenders = [p.name for p in _sources()
                 if "redirect_stdout" in p.read_text() or "capture_stdout" in p.read_text()]
    assert offenders == [], f"stdout capture in: {offenders}"
    for p in _sources():
        for i, line in enumerate(p.read_text().splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("print(") or stripped.startswith("print ("):
                raise AssertionError(f"{p.name}:{i} prints instead of returning")


def test_mcp_stays_thin():
    """Handlers translate values and exceptions, nothing else."""
    text = (REPS / "mcp" / "server.py").read_text()
    for banned in (".execute(", "sqlite3", "sys.exit", "SystemExit", "redirect_stdout",
                   "CREATE TABLE", "INSERT INTO", "RepsError("):
        assert banned not in text, f"MCP layer must not contain {banned!r}"
    assert text.count("call_domain(") >= 60


def test_mcp_tools_are_domain_shaped():
    from reps.mcp.server import list_tool_names
    names = set(asyncio.run(list_tool_names()))
    assert len(names) >= 50
    for banned in ("cmd_", "execute", "sql", "shell", "command"):
        assert not any(banned in n for n in names), f"tool surface leaked {banned!r}"
    for expected in ("session_log_set", "session_range", "goal_add", "progression_set",
                     "program_rotation_status", "autoreg_apply", "snapshot_export"):
        assert expected in names


def test_snapshot_sections_are_modeled():
    """Known snapshot sections have real schemas, not bare containers."""
    from reps.models import SnapshotModel
    bare = [name for name, field in SnapshotModel.model_fields.items()
            if field.annotation in (list, dict)]
    assert bare == [], f"unmodeled snapshot sections: {bare}"


def test_load_constants_is_canonical():
    from reps.constants import load_constants
    from reps.models import ConstantsModel
    assert isinstance(load_constants(), ConstantsModel)


def test_legacy_entrypoints_absent():
    """The old imperative dashboard entry and CLI parser are gone."""
    assert not (ROOT / "dashboard" / "src" / "index.ts").exists()
    assert not (REPS / "cli.py").exists()


def test_docs_teach_mcp_not_cli():
    """Agent docs must route through MCP, never shell command syntax."""
    corpus = "\n".join(
        (ROOT / f).read_text()
        for f in ("AGENTS.md", "README.md", "docs/LOGGING.md", "docs/PROGRAMMING.md",
                  "docs/DASHBOARD.md", "docs/ARCHITECTURE.md", "docs/AUDIT.md"))
    assert "MCP" in corpus
    for pattern in ("cmd_", "log.py start", "log.py log ", "log.py sync", "log.py plan",
                    "quoting never needed"):
        assert pattern not in corpus, f"docs still teach CLI via {pattern!r}"
    assert 'force "<reason>"' not in corpus, "docs still teach the force-flag syntax"
    for m in re.finditer("argparse", corpus):
        context = corpus[max(0, m.start() - 60):m.end()].lower()
        assert "do not" in context or "don't" in context or "no cli framework" in context, \
            "docs mention argparse outside a prohibition"


def test_maintenance_stays_four_ops():
    """log.py must not grow back into an application interface."""
    text = (ROOT / "log.py").read_text()
    for op in ("doctor", "dump", "restore", "export"):
        assert f'"{op}"' in text, f"log.py lost maintenance op {op}"
    assert "argparse" not in text and "Click" not in text and "Typer" not in text
