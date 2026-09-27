"""Scale and batching pins: batched readers match their naive oracles with
O(1) round trips, and 3-year synthetic histories complete."""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(__file__))

from datetime import date, timedelta

from conftest import seed_lift


class QueryCounter:
    def __init__(self):
        self.selects = 0

    def __call__(self, sql):
        if sql.strip().upper().startswith("SELECT"):
            self.selects += 1


def _trace(c):
    counter = QueryCounter()
    c.set_trace_callback(counter)
    return counter


def _seed_adherence(log, c, days_back=10):
    seed_lift(c, "bench", "chest")
    seed_lift(c, "squat", "quads")
    log.set_split("Upper A", 1, "bench", 3)
    log.set_split("Lower A", 1, "squat", 3)
    log.set_rotation(["Upper A", "Lower A", "rest"])
    log.anchor_rotation((date.today() - timedelta(days=days_back)).isoformat(), "Upper A")
    return c


def test_status_range_matches_singles_and_stays_batched(log_module):
    """status_range equals per-date classify_date with a handful of queries."""
    log = log_module
    c = log.conn()
    _seed_adherence(log, c)
    rotation = log.get_rotation(c)
    anchor = log.get_anchor(c)
    start = (date.today() - timedelta(days=59)).isoformat()
    end = date.today().isoformat()
    expected = [log.classify_date(c, rotation, anchor,
                                  (date.today() - timedelta(days=i)).isoformat())
                for i in range(59, -1, -1)]
    counter = _trace(c)
    got = log.status_range(c, rotation, anchor, start, end)
    assert c.set_trace_callback(None) is None
    assert got == expected
    assert counter.selects <= 6, f"{counter.selects} SELECTs for a 60-day range"


def test_calendar_view_matches_singles(log_module):
    """calendar_view adherence verdicts equal classify_date per date."""
    from reps.snapshot import calendar_view
    log = log_module
    c = log.conn()
    _seed_adherence(log, c)
    rotation = log.get_rotation(c)
    anchor = log.get_anchor(c)
    start = (date.today() - timedelta(days=9)).isoformat()
    five = (date.today() - timedelta(days=5)).isoformat()
    cur = c.execute("INSERT INTO workouts (date, status, notes) VALUES (?, 'done', '')", (five,))
    c.commit()
    c.execute("INSERT INTO sets (workout_id, exercise, weight, reps, note, created) "
              "VALUES (?, 'bench', 100, 5, '', datetime('now'))", (cur.lastrowid,))
    c.commit()
    sessions = [{"date": five, "status": "done", "slot_label": "Upper A",
                 "exercises": [{"exercise": "bench",
                                "sets": [{"w": 100, "r": 5, "pr": False}]}]}]
    counter = _trace(c)
    days = calendar_view(c, sessions, date.today().isoformat(), rotation, anchor, 4)
    c.set_trace_callback(None)
    assert counter.selects <= 8, f"{counter.selects} SELECTs for a 10-day calendar"
    assert [d["date"] for d in days] == [
        (date.today() - timedelta(days=i)).isoformat() for i in range(5, -1, -1)]
    for d in days:
        single = log.classify_date(c, rotation, anchor, d["date"])
        assert d["adherence_status"] == single["status"]
        assert d["expected"] == single["expected"]


def test_bodyweight_view_matches_naive(log_module):
    """Sliding-window averages equal the naive rescan, gaps included."""
    from reps.snapshot import bodyweight_view
    log = log_module
    c = log.conn()
    base = date.today() - timedelta(days=30)
    weigh = [(0, 80.0), (0, 80.4), (3, 79.5), (10, 81.0), (11, 81.2), (25, 79.0)]
    for off, kg in weigh:
        c.execute("INSERT INTO bodyweight (date, kg, note) VALUES (?, ?, '')",
                  ((base + timedelta(days=off)).isoformat(), kg))
    c.commit()
    rows = c.execute("SELECT date, kg FROM bodyweight ORDER BY date, id").fetchall()
    got = bodyweight_view(c, 7, 14)
    assert len(got) == len(weigh)
    for out, r in zip(got, rows):
        d = date.fromisoformat(r["date"])
        win = [q["kg"] for q in rows
               if 0 <= (d - date.fromisoformat(q["date"])).days < 7]
        assert out["avg7"] == (round(sum(win) / len(win), 1) if win else None)
        assert out["kg"] == r["kg"]
    assert got[2]["gap_before"] == 3
    assert got[5]["gap_before"] == 14
    assert got[5]["gap"] is False
    counter = _trace(c)
    bodyweight_view(c, 7, 14)
    c.set_trace_callback(None)
    assert counter.selects == 1


def test_weekly_volumes_matches_singles(log_module):
    """weekly_volumes equals per-muscle weekly_volume on every muscle."""
    from reps.program import weekly_volume, weekly_volumes
    from reps.weeks import week_starts
    log = log_module
    c = log.conn()
    seed_lift(c, "bench", "chest")
    seed_lift(c, "squat", "quads,glutes")
    base = date.today() - timedelta(days=21)
    for i in range(6):
        d = (base + timedelta(days=i * 3)).isoformat()
        cur = c.execute("INSERT INTO workouts (date, status, notes) VALUES (?, 'done', '')", (d,))
        c.commit()
        wid = cur.lastrowid
        ex = "bench" if i % 2 == 0 else "squat"
        c.execute("INSERT INTO sets (workout_id, exercise, weight, reps, note, created) "
                  "VALUES (?, ?, 100, 5, '', datetime('now'))", (wid, ex))
        c.commit()
    starts = [date.fromisoformat(s) for s in week_starts(4)]
    batched = weekly_volumes(c, ["chest", "quads", "glutes"], starts)
    for m in ["chest", "quads", "glutes"]:
        assert batched[m] == weekly_volume(c, m, starts)


def test_plan_ledger_and_lifts_exact(log_module):
    """Ledger counts/sessions/last_hit exact; last-set is date-then-id (a
    backfilled set in an old workout with a higher id is NOT last); an
    exercise with only >12-rep sets has best None."""
    log = log_module
    c = log.conn()
    seed_lift(c, "bench", "chest")
    seed_lift(c, "curl", "biceps")
    seed_lift(c, "pump", "chest")
    today = date.today()
    recent = (today - timedelta(days=1)).isoformat()
    old = (today - timedelta(days=5)).isoformat()
    cur = c.execute("INSERT INTO workouts (date, status, notes) VALUES (?, 'done', '')", (recent,))
    c.commit()
    w1 = cur.lastrowid
    c.execute("INSERT INTO sets (workout_id, exercise, weight, reps, note, created) "
              "VALUES (?, 'bench', 100, 5, '', datetime('now'))", (w1,))
    c.execute("INSERT INTO sets (workout_id, exercise, weight, reps, note, created) "
              "VALUES (?, 'pump', 20, 20, '', datetime('now'))", (w1,))
    c.commit()
    cur = c.execute("INSERT INTO workouts (date, status, notes) VALUES (?, 'done', '')", (old,))
    c.commit()
    w0 = cur.lastrowid
    # Backfill into the OLD workout after the recent one: higher set id,
    # older date. Date wins for "last".
    c.execute("INSERT INTO sets (workout_id, exercise, weight, reps, note, created) "
              "VALUES (?, 'bench', 200, 1, '', datetime('now'))", (w0,))
    c.commit()
    plan = log.get_plan()
    ledger = plan["ledger"]
    assert ledger["chest"]["sets"] == 3
    assert ledger["chest"]["sessions"] == 2
    assert ledger["chest"]["last_hit"] == recent
    by_ex = {l["exercise"]: l for l in plan["lifts"]}
    assert by_ex["bench"]["last"] == {"weight": 100, "reps": 5}
    assert by_ex["bench"]["best_e1rm"] == 200.0  # 200x1 single outranks 100x5
    assert by_ex["pump"]["best_e1rm"] is None
    assert by_ex["pump"]["last"] == {"weight": 20, "reps": 20}


def test_scale_smoke_three_years(log_module):
    """~3 years of weekly sessions + ~1000 weigh-ins complete promptly."""
    from reps.snapshot import bodyweight_view, calendar_view
    log = log_module
    c = log.conn()
    seed_lift(c, "bench", "chest")
    log.set_split("Upper A", 1, "bench", 3)
    log.set_rotation(["Upper A", "rest"])
    log.anchor_rotation((date.today() - timedelta(days=1100)).isoformat(), "Upper A")
    base = date.today() - timedelta(days=1099)
    seeded_dates = []
    for w in range(157):
        d = (base + timedelta(days=w * 7)).isoformat()
        seeded_dates.append(d)
        cur = c.execute("INSERT INTO workouts (date, status, notes) VALUES (?, 'done', '')", (d,))
        wid = cur.lastrowid
        for s in range(8):
            c.execute("INSERT INTO sets (workout_id, exercise, weight, reps, note, created) "
                      "VALUES (?, 'bench', 100, 5, '', datetime('now'))", (wid,))
    c.commit()
    for i in range(1000):
        d = (base + timedelta(days=i)).isoformat()
        c.execute("INSERT INTO bodyweight (date, kg, note) VALUES (?, ?, '')", (d, 80 + (i % 5) * 0.2))
    c.commit()
    # One recent session inside the 7-day ledger window (weekly seeds are old).
    recent = (date.today() - timedelta(days=1)).isoformat()
    seeded_dates.append(recent)
    cur = c.execute("INSERT INTO workouts (date, status, notes) VALUES (?, 'done', '')", (recent,))
    c.commit()
    for s in range(8):
        c.execute("INSERT INTO sets (workout_id, exercise, weight, reps, note, created) "
                  "VALUES (?, 'bench', 100, 5, '', datetime('now'))", (cur.lastrowid,))
    c.commit()
    t0 = time.perf_counter()
    bw = bodyweight_view(c, 7, 14)
    sessions = [{"date": d, "status": "done", "slot_label": "Upper A",
                 "exercises": [{"exercise": "bench",
                                "sets": [{"w": 100, "r": 5, "pr": False}] * 8}]}
                for d in seeded_dates]
    cal = calendar_view(c, sessions, date.today().isoformat(), log.get_rotation(c),
                        log.get_anchor(c), 4)
    plan = log.get_plan()
    signals = log.build_signals()
    dt = time.perf_counter() - t0
    assert len(bw) == 1000
    assert len(cal) == 1100  # base (today-1099) through today inclusive
    assert plan["ledger"]["chest"]["sets"] == 8
    assert isinstance(signals, list)
    assert dt < 30, f"3-year views took {dt:.1f}s"


def test_close_all_and_closing_conn(log_module):
    """Registry closes tracked handles; the context manager scopes one."""
    import sqlite3
    import reps.db as db
    c1 = db.conn()
    c2 = db.conn()
    assert db.close_all() >= 2
    try:
        c1.execute("SELECT 1")
        closed = False
    except sqlite3.ProgrammingError:
        closed = True
    assert closed is True
    with db.closing_conn() as c3:
        assert c3.execute("SELECT 1").fetchone()[0] == 1
    try:
        c3.execute("SELECT 1")
        closed = False
    except sqlite3.ProgrammingError:
        closed = True
    assert closed is True


def test_conn_skips_ddl_on_version_match(log_module):
    """Version-match opens skip the DDL pass but keep schema enforcement."""
    import reps.db as db
    c = db.conn()
    tables = {r[0] for r in c.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert "sets" in tables and "schema_version" in tables
    c.close()
    ver = db.SCHEMA_VERSION
    c2 = db.conn()
    c2.execute("UPDATE schema_version SET version = ?", (ver + 99,))
    c2.commit()
    c2.close()
    try:
        db.conn()
        mismatch_refused = False
    except RuntimeError:
        mismatch_refused = True
    assert mismatch_refused is True


def test_call_domain_closes_connections(log_module):
    """The MCP edge leaves no tracked handles behind."""
    from reps.mcp.server import call_domain
    import reps.db as db
    out = call_domain(db.conn)
    assert out["ok"] is True
    assert len(db._OPEN) == 0


def test_signals_respects_deprioritize(log_module):
    """Below-MEV signals downgrade one level with annotation on deprioritize
    (parity with audit check 8); glutes-style intentional gaps read as such."""
    log = log_module
    c = log.conn()
    seed_lift(c, "fly", "chest")
    base = date.today() - timedelta(weeks=8)
    for week in range(8):
        d = (base + timedelta(weeks=week)).isoformat()
        cur = c.execute("INSERT INTO workouts (date, status, notes) VALUES (?, 'done', '')", (d,))
        c.commit()
        c.execute("INSERT INTO sets (workout_id, exercise, weight, reps, note, created) "
                  "VALUES (?, 'fly', 20, 10, '', datetime('now'))", (cur.lastrowid,))
        c.commit()
    before = [s for s in log.build_signals() if s["text"].startswith("chest:")]
    assert before and before[0]["severity"] == "medium"
    assert "deprioritize" not in before[0]["text"]
    log.set_priority("chest", "deprioritize", None)
    after = [s for s in log.build_signals() if s["text"].startswith("chest:")]
    assert after and after[0]["severity"] == "low"
    assert "priority: deprioritize, intentional" in after[0]["text"]
