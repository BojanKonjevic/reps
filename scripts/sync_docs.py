#!/usr/bin/env python3
"""Fill value markers in docs/*.md from constants.json and reps/vocab.py.

Markers (invoked by scripts/gen.py; CI diffs via --check):

    <!--const thresholds.goal_divergence_pct-->5<!--/const-->
    <!--const thresholds.deload_volume_reduction|pctrange-->40-60%<!--/const-->
    <!--enum Verdict-->hit | miss | hold | baseline<!--/enum-->
    <!--rep_bands--> ... generated table ... <!--/rep_bands-->

Usage: scripts/sync_docs.py [--check]
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

CHECK = "--check" in sys.argv[1:]


def load_constants():
    return json.loads((ROOT / "constants.json").read_text())


def const_value(path):
    node = load_constants()
    for part in path.split("."):
        node = node[part]
    return node


def render_const(path, fmt):
    v = const_value(path)
    if fmt == "pctrange":
        lo, hi = v
        return f"{int(lo * 100)}-{int(hi * 100)}%"
    if fmt == "pct":
        return f"{int(v * 100)}%"
    if fmt == "pctabs":
        # Thresholds stored as percent points (e.g. -5, -50): render magnitude.
        return f"{abs(v):g}%"
    if fmt == "dashrange":
        lo, hi = v
        return f"{lo}-{hi}"
    if isinstance(v, list):
        return json.dumps(v)
    return str(v)


def enum_values(name):
    import reps.vocab as vocab
    cls = getattr(vocab, name)
    return " | ".join(m.value for m in cls)


def rep_bands_table():
    bands = load_constants()["rep_bands"]
    top = max(b["max_reps"] for b in bands if b["max_reps"] is not None)
    lines = ["| reps | jump |", "| ---- | ---- |"]
    for b in bands:
        if b["max_reps"] is None:
            lines.append(f"| above {top} | no bound (informational) |")
        else:
            lines.append(f"| to {b['max_reps']} | {b['jump_pct']:g}% |")
    return "\n".join(lines)


def sync_text(text):
    def const_repl(m):
        spec, _old = m.group(1), m.group(2)
        path, _, fmt = spec.partition("|")
        return f"<!--const {spec}-->{render_const(path, fmt)}<!--/const-->"

    def enum_repl(m):
        name, _old = m.group(1), m.group(2)
        return f"<!--enum {name}-->{enum_values(name)}<!--/enum-->"

    def bands_repl(m):
        _old = m.group(1)
        return f"<!--rep_bands-->\n{rep_bands_table()}\n<!--/rep_bands-->"

    text = re.sub(r"<!--const ([^>]+)-->(.*?)<!--/const-->", const_repl, text, flags=re.DOTALL)
    text = re.sub(r"<!--enum ([^>]+)-->(.*?)<!--/enum-->", enum_repl, text, flags=re.DOTALL)
    text = re.sub(r"<!--rep_bands-->(.*?)<!--/rep_bands-->", bands_repl, text, flags=re.DOTALL)
    return text


def main():
    dirty = []
    for doc in sorted((ROOT / "docs").glob("*.md")):
        text = doc.read_text()
        synced = sync_text(text)
        if synced != text:
            if CHECK:
                dirty.append(doc.name)
            else:
                doc.write_text(synced)
                print(f"sync_docs: updated {doc.name}")
    if CHECK and dirty:
        print(f"sync_docs: stale markers in {dirty} (run scripts/sync_docs.py)")
        return 1
    if not CHECK and not dirty:
        print("sync_docs: markers current")
    return 0


if __name__ == "__main__":
    sys.exit(main())
