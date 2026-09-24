# SSOT owner: test datasets. Consumers: pytest golden tests, generated TS fixtures.
# Every scenario builds a seeded state through real domain functions only.

"""Named seeded states. Both pytest golden tests and TS fixtures derive from these."""

from datetime import date, timedelta


def _day(ago):
    return (date.today() - timedelta(days=ago)).isoformat()


def _session(log, ago, exercise, weight, reps, verdict="baseline", note=""):
    from conftest import close_session
    log.start_workout(f"scenario {ago}d ago")
    log.log_set(exercise, weight, reps, "", {"bench": "chest", "row": "back",
                                             "squat": "quads"}.get(exercise, "chest"))
    c = log.conn()
    c.execute("UPDATE workouts SET date = ? WHERE status = 'open'", (_day(ago),))
    c.commit()
    log.set_progression(exercise, verdict, weight + 2.5, reps, "flat", note)
    wid = log.open_workout(log.conn())["id"]
    close_session(log, note or f"scenario {ago}d ago")
    c.execute("UPDATE workouts SET date = ? WHERE id = ?", (_day(ago), wid))
    c.commit()
    return wid


def seed_minimal(log):
    """One lift, one done session, split plus rotation."""
    log.set_exercise_mapping("bench", "chest")
    log.set_split("Upper A", 1, "bench", 3)
    log.set_rotation(["Upper A", "rest"])
    _session(log, 1, "bench", 100, 5)
    return {"name": "minimal"}


def seed_rich(log):
    """Two lifts over weeks: progression, goal, priority, flag, rule, bodyweight, anchor."""
    log.set_exercise_mapping("bench", "chest")
    log.set_exercise_mapping("row", "back")
    log.set_exercise_mapping("incline", "chest")
    log.set_split("Upper A", 1, "bench", 3)
    log.set_split("Upper A", 2, "incline", 4)
    log.set_split("Upper B", 1, "row", 3)
    log.set_rotation(["Upper A", "Upper B", "rest"])
    for ago, ex, w in [(20, "bench", 95), (17, "row", 80), (13, "bench", 97.5),
                       (10, "row", 82.5), (6, "bench", 100), (3, "row", 85)]:
        _session(log, ago, ex, w, 5, "hit" if ago < 10 else "baseline")
    log.anchor_rotation(_day(20), "Upper A")
    log.record_bodyweight(84.0, "")
    log.add_goal("bench", 130, (date.today() + timedelta(days=60)).isoformat(), "", 116.7)
    log.set_priority("chest", "priority")
    log.add_flag("bench", "watch depth")
    log.add_rule("train before work", "schedule", None)
    log.set_movement_note("bench", "touch low")
    log.add_rule("autoreg standing permission", "autoreg", None)
    log.apply_autoreg("Upper A", 1, "bench", 2, "two misses")
    return {"name": "rich"}


def seed_break(log):
    """Last session long ago: the break path (no PR attempts)."""
    log.set_exercise_mapping("bench", "chest")
    log.set_split("Upper A", 1, "bench", 3)
    log.set_rotation(["Upper A", "rest"])
    _session(log, 10, "bench", 100, 5)
    log.mark_rest(_day(2), "sore legs")
    return {"name": "break"}


def seed_deload(log):
    """Active lift deload plus a deload-noted session."""
    log.set_exercise_mapping("bench", "chest")
    log.set_split("Upper A", 1, "bench", 3)
    log.set_rotation(["Upper A", "rest"])
    _session(log, 6, "bench", 100, 5)
    log.set_deload("lift", "bench")
    c = log.conn()
    c.execute("UPDATE deload_state SET set_on = ? WHERE cleared_on IS NULL", (_day(1),))
    c.commit()
    log.start_workout("deload week")
    log.log_set("bench", 60, 5, "", "chest")
    c.execute("UPDATE workouts SET date = ? WHERE status = 'open'", (_day(1),))
    c.commit()
    log.set_progression("bench", "hold", 100, 5, "flat", "deload")
    wid = log.open_workout(log.conn())["id"]
    log.end_workout("deload session")
    c.execute("UPDATE workouts SET date = ? WHERE id = ?", (_day(1), wid))
    c.commit()
    return {"name": "deload"}


def seed_goal_off_track(log):
    """Goal with consecutive shortfalls: off-track trajectory."""
    log.set_exercise_mapping("bench", "chest")
    log.set_split("Upper A", 1, "bench", 3)
    log.set_rotation(["Upper A", "rest"])
    _session(log, 12, "bench", 100, 5)
    gid = log.add_goal("bench", 150, (date.today() + timedelta(days=8)).isoformat(), "", 116.7)["goal_id"]
    c = log.conn()
    c.execute("UPDATE goals SET created = ? WHERE id = ?",
              ((date.today() - timedelta(days=13)).isoformat() + "T12:00:00", gid))
    c.commit()
    _session(log, 8, "bench", 100, 5, "miss")
    _session(log, 4, "bench", 100, 5, "miss")
    return {"name": "goal_off_track"}


SCENARIOS = {
    "minimal": seed_minimal,
    "rich": seed_rich,
    "break": seed_break,
    "deload": seed_deload,
    "goal_off_track": seed_goal_off_track,
}
