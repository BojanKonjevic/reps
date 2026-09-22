import os
import re
import sys

from .db import ROOT


MEMORY_FILE = os.path.join(ROOT, "docs", "MEMORY.md")


def append_memory_state(line):
    try:
        with open(MEMORY_FILE, 'r') as f:
            text = f.read()
    except OSError:
        sys.exit(f"cannot append State line, {MEMORY_FILE} unreadable")
    m = re.search(r"^## State\s*$", text, re.MULTILINE)
    if not m:
        sys.exit("MEMORY.md has no ## State section")
    rest = text[m.end():]
    nxt = re.search(r"^## ", rest, re.MULTILINE)
    insert_at = m.end() + (nxt.start() if nxt else len(rest))
    block = text[m.end():insert_at]
    if line in block:
        return
    if not block.endswith("\n"):
        line = "\n" + line
    text = text[:insert_at] + ("" if block.endswith("\n") else "\n") + line + "\n" + text[insert_at:]
    with open(MEMORY_FILE, 'w') as f:
        f.write(text)
