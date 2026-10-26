"""Checks the program in program/library.yaml against the spec's rules (v2: 45-minute superset plan)."""
import pathlib
import re

import yaml

LIB = yaml.safe_load((pathlib.Path(__file__).resolve().parent.parent / "program" / "library.yaml").read_text())
DAYS = [d[0] for d in LIB["days"]]
UPPER_OK = {"dumbbell", "machine", "cable", "bodyweight", "smith"}
LEGS_OK = UPPER_OK | {"barbell"}
MUSCLES = {"chest", "back", "shoulders", "rear_delts", "traps", "biceps", "triceps", "core",
           "quads", "hamstrings", "glutes", "calves"}


def exercises():
    for block, days in LIB["blocks"].items():
        for day in DAYS:
            for order, ex in enumerate(days[day], 1):
                yield block, day, order, ex


def test_three_blocks_six_days_each():
    assert list(LIB["blocks"]) == ["D", "E", "F"]
    for days in LIB["blocks"].values():
        assert list(days) == DAYS


def test_three_supersets_heavy_lift_first():
    for days in LIB["blocks"].values():
        for day in DAYS:
            types = [e[1] for e in days[day]]
            assert len(types) == 6, day
            assert types[0] == "Heavy" and "Heavy" not in types[1:], day


def test_belt_squat_is_the_heavy_lift_on_both_leg_days():
    for days in LIB["blocks"].values():
        for day in ("L1", "L2"):
            assert days[day][0][0] == "Belt Squat Machine"
            assert days[day][0][1] == "Heavy"


def test_core_work_in_the_superset_slots():
    for days in LIB["blocks"].values():
        core_days = {day for day in DAYS for e in days[day] if e[7] == "core"}
        assert core_days == {"PU1", "PU2", "L1", "L2"}


def test_biceps_on_push_and_pull_days():
    for days in LIB["blocks"].values():
        for day in ("P1", "P2", "PU1", "PU2"):
            assert any(e[7] == "biceps" for e in days[day]), day


def test_set_and_rep_ranges():
    for _, _, _, (name, typ, sets, lo, hi, *_rest) in exercises():
        if typ == "Heavy":
            assert 4 <= sets <= 5 and (lo, hi) == (3, 5), name
        else:
            assert 3 <= sets <= 4 and (lo, hi) == (8, 12), name


def test_increments_follow_region_rules():
    for _, day, _, (name, typ, sets, lo, hi, inc, *_rest) in exercises():
        if day.startswith("L"):
            assert 5 <= inc <= 10, name
        else:
            assert 2.5 <= inc <= 5, name


def test_equipment_rules_and_no_deadlifts():
    for _, day, _, (name, typ, sets, lo, hi, inc, equip, muscle, url) in exercises():
        allowed = LEGS_OK if day.startswith("L") else UPPER_OK
        assert equip in allowed, f"{name}: {equip} not allowed on {day}"
        assert not re.search(r"deadlift|\bRDL\b|good morning", name, re.I), name
        assert muscle in MUSCLES, name


def test_every_exercise_has_a_youtube_video():
    for _, _, _, (name, *_rest, url) in exercises():
        assert re.fullmatch(r"https://www\.youtube\.com/watch\?v=[\w-]{11}", url), name
    assert set(LIB["kettlebell"]) == {"push", "pull", "legs"}
    for kb in LIB["kettlebell"].values():
        assert re.fullmatch(r"https://www\.youtube\.com/watch\?v=[\w-]{11}", kb["url"])


def test_one_video_per_exercise_name():
    seen = {}
    for _, _, _, (name, *_rest, url) in exercises():
        assert seen.setdefault(name, url) == url, name


def test_exercises_rotate_between_blocks():
    names = {k: {e[0] for e in sum(LIB["blocks"][k].values(), [])} for k in "DEF"}
    for x, y in (("D", "E"), ("E", "F"), ("D", "F")):
        # the belt squat is shared on purpose; at most one other repeat
        assert len(names[x] & names[y] - {"Belt Squat Machine"}) <= 1, (x, y)


def test_start_weights_point_at_real_slots():
    for block, starts in LIB["start_lb"].items():
        for key, lb in starts.items():
            day, order = key.split("|")
            assert day in DAYS and 1 <= int(order) <= 6, key
            assert lb > 0
