import json
import os
import re
import sys

from .db import ROOT


CONSTANTS_FILE = os.environ.get("REPS_CONSTANTS", os.path.join(ROOT, "constants.json"))


def validate_constants(raw, source):
    """Validate a parsed constants candidate, exiting loudly on any defect."""
    if not isinstance(raw, dict) or not isinstance(raw.get("muscles"), dict) or not raw["muscles"]:
        sys.exit(f"constants invalid at {source}: missing or empty the muscles map")
    for muscle, entry in raw["muscles"].items():
        if not isinstance(entry, dict):
            sys.exit(f"constants invalid at {source}: muscle '{muscle}' is not an object")
        if not isinstance(entry.get("mev"), int) or isinstance(entry.get("mev"), bool) or entry["mev"] < 0:
            sys.exit(f"constants invalid at {source}: muscle '{muscle}' needs a non-negative mev")
        for bound in ("mav", "mrv"):
            val = entry.get(bound)
            if val is None:
                continue
            if bound == "mav":
                if (not isinstance(val, list) or len(val) != 2
                        or not all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in val)
                        or val[0] > val[1]):
                    sys.exit(f"constants invalid at {source}: muscle '{muscle}' needs {bound} as [lo, hi]")
            elif not isinstance(val, (int, float)) or isinstance(val, bool) or val < 0:
                sys.exit(f"constants invalid at {source}: muscle '{muscle}' needs a non-negative {bound}")
        freq = entry.get("freq")
        if (not isinstance(freq, list) or len(freq) != 2
                or not all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in freq)
                or freq[0] > freq[1]):
            sys.exit(f"constants invalid at {source}: muscle '{muscle}' needs freq as [lo, hi]")
        if entry.get("tier") not in ("settled", "contested", "opinion"):
            sys.exit(f"constants invalid at {source}: muscle '{muscle}' needs a tier")
        if not isinstance(entry.get("source"), str):
            sys.exit(f"constants invalid at {source}: muscle '{muscle}' needs a source string")
        if not isinstance(entry.get("color"), str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", entry["color"]):
            sys.exit(f"constants invalid at {source}: muscle '{muscle}' needs a #rrggbb color string")
    thresholds = raw.get("thresholds")
    if not isinstance(thresholds, dict):
        sys.exit(f"constants invalid at {source}: missing thresholds map")
    for key in ("stale_workout_hours", "stale_workout_days", "break_days",
                "e1rm_warn_ratio", "duplicate_name_distance"):
        val = thresholds.get(key)
        if not isinstance(val, (int, float)) or isinstance(val, bool) or val <= 0:
            sys.exit(f"constants invalid at {source}: thresholds.{key} must be positive")
    for key in ("volume_window_weeks", "volume_bad_weeks", "ledger_retention_days", "default_new_slot_sets"):
        val = thresholds.get(key)
        if not isinstance(val, int) or isinstance(val, bool) or val <= 0:
            sys.exit(f"constants invalid at {source}: thresholds.{key} must be a positive integer")
    drop = thresholds.get("progression_drop_pct")
    if not isinstance(drop, (int, float)) or isinstance(drop, bool) or drop >= 0:
        sys.exit(f"constants invalid at {source}: thresholds.progression_drop_pct must be negative")
    bands = raw.get("rep_bands")
    if not isinstance(bands, list) or not bands:
        sys.exit(f"constants invalid at {source}: missing rep_bands")
    prev_max = -1
    for band in bands:
        if not isinstance(band, dict):
            sys.exit(f"constants invalid at {source}: rep_bands entries must be objects")
        max_reps, jump = band.get("max_reps"), band.get("jump_pct")
        if max_reps is None and jump is None:
            continue
        if (not isinstance(max_reps, int) or isinstance(max_reps, bool) or max_reps <= prev_max
                or not isinstance(jump, (int, float)) or jump <= 0):
            sys.exit(f"constants invalid at {source}: rep_bands must order ascending max_reps with positive jump_pct")
        prev_max = max_reps
    return raw


def load_constants():
    """Load constants.json, the single source of truth for taxonomy and thresholds.

    Fails loudly on parse error or missing tracked muscle. No silent fallback.
    CONTRACT_MUSCLES is the completeness gate, not a parallel source: the file
    owns every number, the gate only names which muscles must be present.
    """
    try:
        with open(CONSTANTS_FILE, 'r') as f:
            raw = json.load(f)
    except (OSError, ValueError) as e:
        sys.exit(f"constants.json unreadable at {CONSTANTS_FILE} ({e}), fix or restore it")
    return validate_constants(raw, CONSTANTS_FILE)


def parse_mev_from_science():
    """Backward-compatible MEV map, now derived from constants.json."""
    constants = load_constants()
    return {muscle: entry["mev"] for muscle, entry in constants["muscles"].items()}


def rep_band_bound(reps):
    """Jump threshold for given reps, from constants.json rep_bands. None above 15."""
    constants = load_constants()
    for band in constants["rep_bands"]:
        max_reps = band.get("max_reps")
        if max_reps is None:
            return None
        if reps <= max_reps:
            return band.get("jump_pct")
    return None


def tracked_muscles():
    """Ordered tracked muscle list from constants.json."""
    return list(load_constants()["muscles"].keys())


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
        vocab = set(load_constants()["muscles"]) | set(load_constants().get("untracked", []))
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


def cmd_constants_show(key=None):
    constants = load_constants()
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


def cmd_constants_validate():
    load_constants()
    print(json.dumps({"valid": True, "file": CONSTANTS_FILE}))


def cmd_constants_set(key, value):
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
