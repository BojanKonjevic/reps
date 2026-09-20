#!/usr/bin/env python3
"""Multi-word names work unquoted; flags delimit values (Fix 13)."""

import io
import json
from contextlib import redirect_stdout

import pytest


def _main(log, *argv):
    import sys
    buf = io.StringIO()
    old = sys.argv
    sys.argv = ["log.py", *argv]
    try:
        with redirect_stdout(buf):
            try:
                log.main()
            except SystemExit as e:
                if e.code not in (None, 0):
                    raise
    finally:
        sys.argv = old
    return buf.getvalue()


def test_unquoted_log_progression_priority(log_module):
    log = log_module
    _main(log, "map", "set", "incline", "barbell", "bench", "press", "chest,front", "delt")
    _main(log, "split", "set", "Upper", "A", "1", "incline", "barbell", "bench", "press", "3")
    _main(log, "priority", "set", "side", "delt", "priority")
    _main(log, "start", "test")
    out = _main(log, "log", "incline", "barbell", "bench", "press", "80", "6")
    assert json.loads(out)["set_id"] == 1
    out = _main(log, "progression", "set", "incline", "barbell", "bench", "press",
                "--verdict", "baseline", "--next", "80x6", "--direction", "flat")
    assert json.loads(out)["progression"] == "incline barbell bench press"
    out = _main(log, "split", "move", "Upper", "A", "incline", "barbell", "bench", "press", "--to", "1")
    assert json.loads(out)["moved"] == "incline barbell bench press"
    out = _main(log, "split", "reconcile", "--day", "Upper", "A")
    assert json.loads(out)["reconciled"] == "Upper A"


def test_priority_set_names_quoting_on_tier_error(log_module):
    log = log_module
    with pytest.raises(SystemExit, match="tier must be"):
        log.cmd_priority_set("side", "delt", None)


def test_dump_and_meta_show(log_module):
    log = log_module
    out = _main(log, "meta", "set", "compaction_postponed_until", "2030-01-01")
    assert json.loads(out)["value"] == "2030-01-01"
    out = _main(log, "meta", "show")
    assert json.loads(out)["compaction_postponed_until"] == "2030-01-01"
    with pytest.raises(SystemExit, match="Mon D YYYY"):
        log.cmd_meta_set("last_compacted", "yesterday")
    out = _main(log, "dump")
    assert json.loads(out)["dumped"].endswith("workouts.sql")


def test_flag_add_unquoted_subject(log_module):
    log = log_module
    log.cmd_retag("bench", "chest")
    out = _main(log, "flag", "add", "bench", "watch", "the", "arch")
    assert json.loads(out)["subject"] == "bench"
    out = _main(log, "flag", "list")
    assert json.loads(out)[0]["reason"] == "watch the arch"
