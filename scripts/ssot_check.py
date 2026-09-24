#!/usr/bin/env python3
"""SSOT gate catalog: every check fails with the owner to use instead.

Gates flip from warn to hard per phase (see spec section 6.1). Until their
phase lands, gates marked warn-only report but exit 0. Promote by moving the
gate id from WARN_ONLY to enforced.

Usage: scripts/ssot_check.py [--warn-only-ok] (pre-commit and verify.sh run it plain).
"""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Gates whose phase has not landed yet: reported, do not fail the build.
# G3/G4/G5 stay advisory here: they are enforced by scripts/gen-check.sh,
# scripts/sync_docs.py --check, and tests/test_docs.py (all wired into
# pre-commit and scripts/verify.sh). Everything else is hard.
WARN_ONLY = {
    "G3", "G4", "G5",
}

FAILURES: list[str] = []


def fail(gate: str, msg: str) -> None:
    line = f"[{gate}] {msg}"
    if gate in WARN_ONLY:
        print(f"WARN {line}")
    else:
        FAILURES.append(line)
        print(f"FAIL {line}")


def rg(pattern: str, paths: list[str], globs: list[str] | None = None) -> list[str]:
    cmd = ["rg", "-n", "--no-heading", pattern, *paths]
    for g in globs or []:
        cmd += ["--glob", g]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    except FileNotFoundError:
        print("ssot_check: ripgrep (rg) is required but not installed", file=sys.stderr)
        sys.exit(2)
    if p.returncode not in (0, 1):
        print(f"ssot_check: rg failed ({p.returncode}): {p.stderr.strip()}", file=sys.stderr)
        sys.exit(2)
    return [ln for ln in p.stdout.splitlines() if ln.strip()]


def check_g1() -> None:
    """e1RM formula lives in reps/e1rm.py only."""
    for ln in rg(r"reps ?/ ?30", ["reps", "dashboard/src"]):
        if "reps/e1rm.py" in ln or "/tests/" in ln or "tests/" in ln:
            continue
        fail("G1", f"e1RM arithmetic outside reps/e1rm.py: {ln} (use reps/e1rm.py)")
    for ln in rg(r"CASE WHEN reps ?= ?1", ["reps"]):
        fail("G1", f"inline e1RM CASE outside reps/e1rm.py: {ln} (use the e1rm() UDF)")


def check_g2() -> None:
    """Threshold values live in constants.json only.

    Keys may appear as ConstantsModel field definitions (models.py, the
    owner) or as string-key reads (thresholds.X / .get('X') / markers).
    A bare identifier use is a second definition of the value.
    """
    keys = ["stall_window_sessions", "stall_decline_pct", "stall_flat_sessions",
            "stall_min_sessions", "bodyweight_gap_days", "bodyweight_avg_days",
            "recent_notes_count", "trend_top_lifts"]
    pat = re.compile(r"(?<![.'\"\w])(" + "|".join(keys) + r")(?![\"'\w])")
    strlit = re.compile(r"'[^']*'|\"[^\"]*\"")
    for p in (ROOT / "reps").rglob("*.py"):
        if "__pycache__" in p.parts or p.name == "models.py":
            continue  # sanctioned: models.py owns the Thresholds definitions
        for i, line in enumerate(p.read_text().splitlines(), 1):
            code = strlit.sub("", line.split("#")[0])
            m = pat.search(code)
            if m:
                fail("G2", f"threshold-like literal in {p.name}:{i}: {m.group(0)} "
                           f"(use constants.json)")


def check_g12() -> None:
    """No string-splitting of DB columns; no TEXT muscles/movements columns."""
    for ln in rg(r'\.split\("(,|/)"\)', ["reps"]):
        if "sanctioned:" in ln:
            continue
        fail("G12", f"DB column string-split in reps/: {ln} (use WS3 normalized tables)")
    for ln in rg(r"TEXT.*(muscles|movements)", ["reps/db.py"]):
        fail("G12", f"denormalized TEXT column: {ln} (use lift_muscle / split_slot_lift)")


def check_g13() -> None:
    """No sys.exit/print in domain modules."""
    for ln in rg(r"sys\.exit|print\(", ["reps"], ["!log.py"]):
        fail("G13", f"process-edge call in domain: {ln} (use Refusal/returned models)")


def check_g14() -> None:
    """pnpm everywhere; no npm invocations, no package-lock.json."""
    for ln in rg(r"\bnpm ", ["scripts", "docs", ".github", "AGENTS.md", "README.md", ".pre-commit-config.yaml"]):
        if "scripts/ssot_check.py" in ln:
            continue  # sanctioned: the gate enforcing the rule names it
        fail("G14", f"npm reference (use pnpm): {ln}")
    if (ROOT / "dashboard" / "package-lock.json").exists():
        fail("G14", "dashboard/package-lock.json present (pnpm owns JS deps)")


def check_g15() -> None:
    """Python tests run through scripts/test-py.sh only."""
    for ln in rg(r"uv run --with", ["."]):
        if "scripts/" in ln or "pyproject.toml" in ln:
            continue
        fail("G15", f"inline test invocation (use scripts/test-py.sh): {ln}")


def check_g16() -> None:
    """Every owner module in the register exists and carries its header."""
    owners = [
        "reps/e1rm.py", "reps/records.py", "reps/slots.py", "reps/trends.py",
        "reps/weeks.py", "reps/vocab.py", "docs/SSOT.md",
    ]
    markers = {
        "reps/e1rm.py": "SSOT owner: e1RM",
        "reps/records.py": "SSOT owner: personal-record",
        "reps/slots.py": "SSOT owner: slot match",
        "reps/trends.py": "SSOT owner: stall",
        "reps/weeks.py": "SSOT owner: week bucketing",
        "reps/vocab.py": "SSOT owner: closed vocabularies",
    }
    for rel in owners:
        if not (ROOT / rel).exists():
            fail("G16", f"register owner missing: {rel}")
    for rel, marker in markers.items():
        p = ROOT / rel
        if p.exists() and marker not in p.read_text():
            fail("G16", f"owner header missing in {rel} (add '# {marker}...')")


def check_g17() -> None:
    """Every constants key is read by code or referenced by a doc marker."""
    import json
    consts = json.loads((ROOT / "constants.json").read_text())

    def keys(d: dict, prefix="") -> list[str]:
        out = []
        for k, v in d.items():
            out.append(prefix + k)
            if isinstance(v, dict):
                out += keys(v, prefix + k + ".")
        return out
    all_keys = [k for k in keys(consts) if "." in k]
    # muscles.* leaves are data rows keyed by dict iteration (volume_block
    # loops constants.muscles), not identifiers; only thresholds/leaf keys
    # need a code or marker reference.
    all_keys = [k for k in all_keys if not k.startswith("muscles.")]
    corpus = ""
    for p in list((ROOT / "reps").rglob("*.py")) + list((ROOT / "docs").glob("*.md")):
        if "__pycache__" in p.parts:
            continue
        try:
            corpus += p.read_text() + "\n"
        except OSError:
            pass
    for k in all_keys:
        leaf = k.split(".")[-1]
        if leaf not in corpus and k not in corpus:
            fail("G17", f"unread constants key: {k} (read it in code or reference via doc marker)")


def check_g18() -> None:
    """No second-owner file names."""
    for ln in rg(r"", []):
        pass
    bad = ["utils2", "helpers", "common", "misc", "constants2"]
    for p in list((ROOT / "reps").rglob("*.py")) + list((ROOT / "dashboard" / "src").rglob("*.ts")):
        stem = p.stem.lower()
        if stem in bad:
            fail("G18", f"second-owner file name: {p} (see docs/SSOT.md decision procedure)")


def main() -> int:
    check_g1()
    check_g2()
    check_g12()
    check_g13()
    check_g14()
    check_g15()
    check_g16()
    check_g17()
    check_g18()
    # G3/G4/G5/G6/G7/G8/G9/G10/G11 are enforced by gen.py --check, sync_docs.py
    # --check, test_docs.py, and ESLint respectively; presence here is a reminder.
    if FAILURES:
        print(f"\nssot_check: {len(FAILURES)} hard gate failure(s)")
        return 1
    print("ssot_check: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
