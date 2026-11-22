from datetime import date, timedelta

import pytest

from conftest import close_session
from reps.blocks import correct_block, close_block, list_blocks, preview_start, start_block
from reps.errors import RepsError
from reps.mcp.server import call_tool
from reps.sessions import start_workout, update_workout


def day(ago):
    return (date.today() - timedelta(days=ago)).isoformat()


def test_block_close_coverage_and_workout_corrections(tmp_db):
    with pytest.raises(RepsError, match="no block covers"):
        start_workout("")
    block = start_block(day(5), [])
    wid = start_workout("", day(3))["workout_id"]
    with pytest.raises(RepsError, match="open workout"):
        close_block(day(3), "Keep the basics.")
    import reps
    close_session(reps)
    with pytest.raises(RepsError, match="coach note"):
        close_block(day(3), " ")
    with pytest.raises(RepsError, match="outside every block"):
        close_block(day(4), "Keep the basics.")
    assert list_blocks()[0]["end_date"] is None
    closed = close_block(day(3), "Keep the basics.")
    assert closed["coach_note"] == "Keep the basics."
    with pytest.raises(RepsError, match="no block covers"):
        update_workout(wid, "date", day(2))
    assert update_workout(wid, "notes", "corrected")["updated_workout"] == wid
    with pytest.raises(RepsError, match="outside every block"):
        correct_block(block["id"], start_date=day(2), end_date=day(1))
    assert correct_block(block["id"], coach_note="New summary.")["coach_note"] == "New summary."


def test_preview_keeps_net_program_changes(tmp_db):
    import reps
    from reps.history import list_changes

    for exercise in ("bench", "smith"):
        reps.set_exercise_mapping(exercise, "chest")
    reps.set_split("Upper A", 1, "bench", 3)
    c = reps.conn()
    c.execute("UPDATE state_change SET date = ? WHERE domain = 'program'", (day(5),))
    c.commit()
    start_block(day(5), [])
    close_block(day(3), "Baseline established.")
    reps.set_split("Upper A", 1, "smith", 3)
    reps.set_split("Upper A", 1, "bench", 3)
    assert preview_start(day(0))["changes"] == []
    reps.set_split("Upper A", 1, "smith", 4)
    draft = preview_start(day(0))
    assert draft["changes"][0]["details"] == ["bench 3 sets -> smith 4 sets"]
    choice = draft["changes"][0]["change_id"]
    assert len(draft["changes"][0]["source_ids"]) == 3
    block = start_block(day(0), [choice])
    reps.set_split("Upper A", 1, "bench", 3)
    assert list_blocks()[-1]["changes"] == block["changes"]
    assert list_changes("program")[-1]["id"] != choice
    with pytest.raises(RepsError, match="overlap"):
        correct_block(block["id"], start_date=day(3))


def test_block_separates_local_best_from_global_pr(tmp_db):
    import reps
    from reps.blocks import lift_comparisons

    def log(ago, load):
        workout = start_workout("", day(ago))
        reps.log_set("bench", load, 6, "", "chest")
        close_session(reps)
        return workout["workout_id"]

    start_block(day(10), [])
    log(10, 100)
    log(8, 99)
    log(6, 98)
    close_block(day(5), "Three comparable sessions.")
    current = start_block(day(3), [])
    baseline = log(3, 90)
    assert reps.session_prs(baseline)["block_bests"] == []
    second = log(2, 95)
    assert reps.session_prs(second)["block_bests"] == [{"exercise": "bench", "e1rm": 114.0}]
    third = log(0, 102)
    report = reps.session_prs(third)
    assert report["prs"][0]["is_pr"]
    assert report["block_bests"] == []
    comparison = lift_comparisons(reps.conn())[current["id"]]["bench"]
    assert (comparison["baseline"], comparison["best"]) == (108.0, 122.4)
    assert comparison["sessions"] == 3 and not comparison["stalling"]


def test_block_tool_lifecycle(tmp_db):
    import asyncio

    async def run():
        assert not (await call_tool("session_start", {}))["ok"]
        draft = await call_tool("block_preview_start", {"start_date": day(0)})
        assert draft["ok"] and draft["data"]["changes"] == []
        started = await call_tool("block_start", {"start_date": day(0), "confirmed_change_ids": []})
        assert started["ok"]
        closed = await call_tool("block_close", {"end_date": day(0), "coach_note": "Completed."})
        assert closed["ok"] and closed["data"]["end_date"] == day(0)
        assert (await call_tool("block_list", {}))["data"][0]["coach_note"] == "Completed."

    asyncio.run(run())


def test_bodyweight_uses_boundary_medians_and_latest_daily_measurement():
    from reps.blocks import bodyweight_summary

    start = date(2026, 9, 22)
    end = date(2026, 11, 20)
    rows = [
        {"date": "2026-09-22", "kg": 79.8},
        {"date": "2026-09-23", "kg": 77.0},
        {"date": "2026-09-23", "kg": 78.9},
        {"date": "2026-09-29", "kg": 78.6},
        {"date": "2026-09-30", "kg": 82.0},
        {"date": "2026-11-12", "kg": 82.0},
        {"date": "2026-11-13", "kg": 83.0},
        {"date": "2026-11-16", "kg": 83.2},
        {"date": "2026-11-20", "kg": 83.0},
    ]
    weight = bodyweight_summary(rows, start, end, 8)
    assert weight["start"] == {"since": "2026-09-22", "until": "2026-09-29", "samples": 3, "kg": 78.9}
    assert weight["end"] == {"since": "2026-11-13", "until": "2026-11-20", "samples": 3, "kg": 83.0}


def test_short_blocks_do_not_reuse_weigh_ins():
    from reps.blocks import bodyweight_summary

    start = date(2026, 9, 22)
    end = date(2026, 9, 26)
    rows = [{"date": (start + timedelta(days=i)).isoformat(), "kg": 78.0 + i} for i in range(5)]
    weight = bodyweight_summary(rows, start, end, 8)
    assert weight["start"] == {"since": "2026-09-22", "until": "2026-09-24", "samples": 3, "kg": 79.0}
    assert weight["end"] == {"since": "2026-09-25", "until": "2026-09-26", "samples": 2, "kg": None}
    assert bodyweight_summary(rows, start, start, 8)["end"] == {
        "since": None, "until": None, "samples": 0, "kg": None,
    }
