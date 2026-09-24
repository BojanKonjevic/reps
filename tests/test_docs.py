#!/usr/bin/env python3
"""Docs are derived or referential: markers current, references real, no bare values."""

import ast
import json
import pathlib
import re
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _tools():
    import asyncio
    import sys
    sys.path.insert(0, str(ROOT))
    from reps.mcp.server import list_tool_names
    return set(asyncio.run(list_tool_names()))


TOOLS = _tools()

TOOL_PAT = re.compile(
    r"`((?:session|program|muscle|goal|progression|autoreg|constants|sync|maintenance)_[a-z_]+"
    r"|plan|doctor|audit_data|snapshot_export)`")

CONST_PATH_PAT = re.compile(r"`((?:thresholds|muscles|rep_bands|untracked|explained_keywords|rep_scheme_default)(?:\.[\w ]+)*)`")

REPO_PATH_PAT = re.compile(r"`((?:docs|reps|dashboard|scripts|tests)/[\w./-]+|constants\.json|log\.py|pyproject\.toml)`")

ENUM_CONTEXT = re.compile(r"verdict|direction|tier|scope|status|action|variant|severity|kind", re.I)


def _docs():
    return sorted((ROOT / "docs").glob("*.md")) + [ROOT / "AGENTS.md", ROOT / "README.md"]


def test_doc_markers_current():
    r = subprocess.run([__import__("sys").executable, "scripts/sync_docs.py", "--check"],
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout


def test_docs_reference_real_tools():
    import reps.vocab as vocab
    enum_values = {m.value for cls in
                   (vocab.Verdict, vocab.Direction, vocab.PriorityTier, vocab.DeloadScope,
                    vocab.AdherenceStatus, vocab.Severity, vocab.VolumeStatus,
                    vocab.SplitVariant, vocab.AutoregAction, vocab.RuleStatus, vocab.GoalStatus,
                    vocab.MarkKind, vocab.WorkoutStatus)
                   for m in cls}
    modules = {p.stem for p in (ROOT / "reps").glob("*.py")} | {"mcp"}
    tables = set(re.findall(r"CREATE TABLE IF NOT EXISTS (\w+)",
                            (ROOT / "reps" / "db.py").read_text()))
    tables |= {"set_muscle"}  # view over lift_muscle
    checks = set(re.findall(r'"check": "([\w]+)"', (ROOT / "reps" / "audit.py").read_text()))
    problems = []
    for doc in _docs():
        if doc.name == "SSOT.md":
            continue  # the register teaches with hypothetical values by design
        for i, line in enumerate(doc.read_text().splitlines(), 1):
            for m in TOOL_PAT.finditer(line):
                name = m.group(1)
                if name in checks or name in tables:
                    continue  # audit-check and table names are their own owners
                if name not in TOOLS:
                    problems.append(f"{doc.name}:{i}: unknown tool `{name}`")
            for m in CONST_PATH_PAT.finditer(line):
                if not _const_path_exists(m.group(1)):
                    problems.append(f"{doc.name}:{i}: unknown constants path `{m.group(1)}`")
            for m in REPO_PATH_PAT.finditer(line):
                target = m.group(1).split("#")[0]
                if target and not (ROOT / target).exists():
                    problems.append(f"{doc.name}:{i}: missing path `{m.group(1)}`")
            for m in re.finditer(r"`([a-z][a-z0-9_]*)`", line):
                word = m.group(1)
                if TOOL_PAT.match(m.group(0)) or CONST_PATH_PAT.match(m.group(0)):
                    continue
                if word in enum_values:
                    continue
                if word in modules or word in tables or word in checks:
                    continue  # module, table, and audit-check names are their own owners
                if ENUM_CONTEXT.search(line) and _looks_enum(word):
                    problems.append(f"{doc.name}:{i}: enum value `{word}` not in vocab.py")
    assert problems == [], "\n".join(problems)


def _looks_enum(word):
    return word in {"hit", "miss", "hold", "baseline", "up", "flat", "down", "priority",
                    "maintain", "deprioritize", "lift", "slot", "done", "swapped", "extra",
                    "rest_ok", "rest_logged", "missed", "high", "medium", "low", "info",
                    "below_mev", "in_range", "above_mrv", "active", "expired", "superseded",
                    "archived", "dropped", "trim", "swap", "add", "open", "rest",
                    "goal", "stalling", "slipping", "focus", "autoreg", "grouped",
                    "deferred", "smashed", "sideways", "urgent", "planet"}


def _const_path_exists(path):
    node = json.loads((ROOT / "constants.json").read_text())
    for part in path.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return False
    return True


def test_docs_have_no_constant_literals():
    """Curated bare-value phrases must live inside markers only."""
    denylist = [
        r"4% at 1-6 reps", r"5% at 7-10", r"8% at 11-15", r"Above 15 reps",
        r"Above 15 reps, e1RM", r"> 5% e1RM", r"Drops over 50%",
        r"gap > 8h", r"age_days ≥ 1", r"rolling 8-week",
        r"last 8 weeks", r"≥ 4 of the last", r"3-8 reps",
        r"reduce volume 40-60%", r"drops 5%\+ across",
        r"weight times 1 plus reps over 30",
    ]
    span = re.compile(r"<!--(?:const|enum|rep_bands)[^>]*-->.*?<!--/(?:const|enum|rep_bands)-->",
                      re.DOTALL)
    problems = []
    for doc in _docs():
        text = span.sub("", doc.read_text())
        for pat in denylist:
            if re.search(pat, text):
                problems.append(f"{doc.name}: bare constant literal /{pat}/ outside markers")
    assert problems == [], "\n".join(problems)


def test_no_cli_phrasing_in_domain_strings():
    """Domain string literals never invent command syntax (WS7.3)."""
    pat = re.compile(r"\b(map|split|meta|rotation|deload|priority|flag|rule) "
                     r"(set|show|clear|add|anchor)\b")
    problems = []
    for mod in (ROOT / "reps").rglob("*.py"):
        if "__pycache__" in mod.parts:
            continue
        tree = ast.parse(mod.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if pat.search(node.value):
                    problems.append(f"{mod.name}:{node.lineno}: {node.value[:70]}")
    assert problems == [], "\n".join(problems)


def test_fix_tool_names_are_registered():
    """end_gate fix_tool references resolve to real MCP tools (WS8)."""
    import sys
    sys.path.insert(0, str(ROOT))
    from reps.errors import RepsError  # noqa: F401  (import surface intact)
    import inspect
    import reps.sessions as sessions
    src = inspect.getsource(sessions.end_gate_items)
    for m in re.finditer(r'"fix_tool": "([^"]+)"', src):
        assert m.group(1) in TOOLS, f"fix_tool {m.group(1)} is not a registered tool"
