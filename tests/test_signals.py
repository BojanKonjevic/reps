#!/usr/bin/env python3
"""Coach notes: deterministic warning sentences, worst first."""

import io
import json
from contextlib import redirect_stdout
from datetime import date, timedelta


def _signals(log):
    buf = io.StringIO()
    with redirect_stdout(buf):
        log.cmd_export()
    return json.loads(buf.getvalue())["signals"]


def _done(c, day, *exercises):
    cur = c.execute("INSERT INTO workouts (date, status, notes) VALUES (?, 'done', '')", (day,))
    for ex in exercises:
        cur2 = c.execute("INSERT INTO sets (workout_id, exercise, weight, reps, note, created) "
                         "VALUES (?, ?, 100, 5, '', datetime('now'))", (cur.lastrowid, ex))
        c.execute("INSERT INTO set_muscles (set_id, muscle) VALUES (?, 'chest')", (cur2.lastrowid,))
    c.commit()


def _judge(c, wid, exercise, verdict):
    c.execute("INSERT INTO progression (workout_id, exercise, verdict, next_target, direction, note, created) "
              "VALUES (?, ?, ?, '80x5', 'flat', '', datetime('now'))", (wid, exercise, verdict))
    c.commit()


def test_thin_history_reports_info_only(log_module):
    log = log_module
    c = log.conn()
    log.cmd_retag("bench", "chest")
    _done(c, date.today().isoformat(), "bench")
    signals = _signals(log)
    assert len(signals) == 1
    assert signals[0]["severity"] == "info"
    assert "not enough history" in signals[0]["text"]


def test_volume_miss_and_streak_ordering(log_module):
    log = log_module
    c = log.conn()
    log.cmd_retag("bench", "chest")
    for weeks_ago in range(8):
        day = (date.today() - timedelta(weeks=weeks_ago) - timedelta(days=date.today().weekday())).isoformat()
        _done(c, day, "bench")
    signals = _signals(log)
    by_sev = [s["severity"] for s in signals]
    assert by_sev == sorted(by_sev, key=lambda s: {"high": 0, "medium": 1, "low": 2, "info": 3}[s])
    assert any(s["severity"] == "high" for s in signals)
    assert any(s["severity"] == "medium" and "chest" in s["text"] and "under MEV" in s["text"]
               for s in signals)


def test_miss_streak_and_break_lines(log_module):
    log = log_module
    c = log.conn()
    log.cmd_retag("bench", "chest")
    log.cmd_retag("row", "back")
    d1 = (date.today() - timedelta(days=10)).isoformat()
    d2 = (date.today() - timedelta(days=9)).isoformat()
    for d in (d1, d2):
        cur = c.execute("INSERT INTO workouts (date, status, notes) VALUES (?, 'done', '')", (d,))
        cur2 = c.execute("INSERT INTO sets (workout_id, exercise, weight, reps, note, created) "
                         "VALUES (?, 'bench', 100, 5, '', datetime('now'))", (cur.lastrowid,))
        c.execute("INSERT INTO set_muscles (set_id, muscle) VALUES (?, 'chest')", (cur2.lastrowid,))
        _judge(c, cur.lastrowid, "bench", "miss")
    c.commit()
    signals = _signals(log)
    assert any("2 misses running" in s["text"] for s in signals)
    assert any("since last session" in s["text"] for s in signals)
