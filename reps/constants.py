import json
import os
import sys

from pydantic import ValidationError

from .db import ROOT
from .models import ConstantsModel, first_error


CONSTANTS_FILE = os.environ.get("REPS_CONSTANTS", os.path.join(ROOT, "constants.json"))


def validate_constants(raw, source):
    """Validate a parsed constants candidate against ConstantsModel.

    Exits loudly on any defect. Returns the raw mapping unchanged; it is
    for validating write candidates (see constants_set), not a read path.
    All reads go through load_constants(), which returns the model.
    """
    try:
        ConstantsModel.model_validate(raw)
    except ValidationError as e:
        sys.exit(f"constants invalid at {source}: {first_error(e)}")
    return raw


def load_constants() -> ConstantsModel:
    """Load constants.json as the canonical validated ConstantsModel.

    The single source of truth for taxonomy and thresholds. Fails loudly
    on parse error or constraint violation. No silent fallback, no raw
    dict: attribute access on the model is the only read path.
    """
    try:
        with open(CONSTANTS_FILE, 'r') as f:
            raw = json.load(f)
    except (OSError, ValueError) as e:
        sys.exit(f"constants.json unreadable at {CONSTANTS_FILE} ({e}), fix or restore it")
    try:
        return ConstantsModel.model_validate(raw)
    except ValidationError as e:
        sys.exit(f"constants invalid at {CONSTANTS_FILE}: {first_error(e)}")


def parse_mev_from_science():
    """Backward-compatible MEV map, now derived from constants.json."""
    constants = load_constants()
    return {muscle: entry.mev for muscle, entry in constants.muscles.items()}


def rep_band_bound(reps):
    """Jump threshold for given reps, from constants.json rep_bands. None above 15."""
    constants = load_constants()
    for band in constants.rep_bands:
        if band.max_reps is None:
            return None
        if reps <= band.max_reps:
            return band.jump_pct
    return None


def tracked_muscles():
    """Ordered tracked muscle list from constants.json."""
    return list(load_constants().muscles.keys())


def canon_muscle_name(text, vocab):
    """Canonical muscle name, tolerating a missing plural s (delt -> delts).

    Returns None for unknown names so callers can leave them through for
    audit/doctor to flag instead of guessing.
    """
    t = text.strip().lower()
    if t in vocab:
        return t
    if t + "s" in vocab:
        return t + "s"
    return None


def _join_muscles(words, vocab):
    """Reassemble muscle words into canonical names (multi-word heads re-joined)."""
    out, i = [], 0
    while i < len(words):
        two = canon_muscle_name(" ".join(words[i:i + 2]), vocab) if i + 1 < len(words) else None
        if two is not None:
            out.append(two)
            i += 2
            continue
        one = canon_muscle_name(words[i], vocab)
        out.append(one if one is not None else words[i].lower())
        i += 1
    return out


def clean_muscles(value):
    seen = set()
    out = []
    try:
        vocab = set(load_constants().muscles) | set(load_constants().untracked)
    except SystemExit:
        vocab = set()
    for p in value.split(","):
        m = p.strip().lower()
        if not m:
            continue
        c = canon_muscle_name(m, vocab) or m
        if c in seen:
            continue
        seen.add(c)
        out.append(c)
    return ",".join(out)


def constants_show(key=None):
    constants = load_constants().model_dump()
    if not key:
        print(json.dumps(constants, indent=2))
        return
    parts = key.split(".")
    node = constants
    for part in parts:
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            sys.exit(f"constants key '{key}' not found")
    print(json.dumps(node, indent=2))


def constants_validate():
    load_constants()
    print(json.dumps({"valid": True, "file": CONSTANTS_FILE}))


def constants_set(key, value):
    try:
        parsed = json.loads(value)
    except ValueError:
        parsed = value
    try:
        with open(CONSTANTS_FILE, 'r') as f:
            raw = json.load(f)
    except (OSError, ValueError) as e:
        sys.exit(f"constants.json unreadable at {CONSTANTS_FILE} ({e})")
    parts = key.split(".")
    node = raw
    for part in parts[:-1]:
        if not isinstance(node, dict) or part not in node:
            sys.exit(f"constants key '{key}' not found")
        node = node[part]
    if not isinstance(node, dict) or parts[-1] not in node:
        sys.exit(f"constants key '{key}' not found")
    node[parts[-1]] = parsed
    validate_constants(raw, f"candidate for {key}")
    import tempfile
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(CONSTANTS_FILE)), suffix=".constants")
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(raw, f, indent=2)
            f.write("\n")
        os.replace(tmp, CONSTANTS_FILE)
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass
    load_constants()
    print(json.dumps({"set": key, "value": parsed}))
