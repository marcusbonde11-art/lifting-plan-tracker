"""Checks the program in program/library.yaml against the spec's rules."""
import pathlib
import re

import yaml

LIB = yaml.safe_load((pathlib.Path(__file__).resolve().parent.parent / "program" / "library.yaml").read_text())
DAYS = [d[0] for d in LIB["days"]]
UPPER_OK = {"dumbbell", "machine", "cable", "bodyweight", "smith"}
LEGS_OK = UPPER_OK | {"barbell"}


def exercises():
    for block, days in LIB["blocks"].items():
        for day in DAYS:
            for order, ex in enumerate(days[day], 1):
                yield block, day, order, ex


def test_three_blocks_six_days_each():
    assert list(LIB["blocks"]) == ["A", "B", "C"]
    for days in LIB["blocks"].values():
        assert list(days) == DAYS


def test_one_heavy_then_four_accessories():
    for days in LIB["blocks"].values():
        for day in DAYS:
            types = [e[1] for e in days[day]]
            assert types[0] == "Heavy"
            assert len(types) == 5 and "Heavy" not in types[1:]


def test_set_and_rep_ranges():
    for _, _, _, (name, typ, sets, lo, hi, inc, equip, url) in exercises():
        if typ == "Heavy":
            assert 4 <= sets <= 5 and (lo, hi) == (3, 5), name
        else:
            assert 3 <= sets <= 4 and (lo, hi) == (8, 12), name


def test_increments_follow_region_rules():
    for _, day, _, (name, typ, sets, lo, hi, inc, equip, url) in exercises():
        if day.startswith("L"):
            assert 5 <= inc <= 10, name
        else:
            assert 2.5 <= inc <= 5, name


def test_equipment_rules_and_no_deadlifts():
    for _, day, _, (name, typ, sets, lo, hi, inc, equip, url) in exercises():
        allowed = LEGS_OK if day.startswith("L") else UPPER_OK
        assert equip in allowed, f"{name}: {equip} not allowed on {day}"
        assert not re.search(r"deadlift|\bRDL\b|good morning", name, re.I), name


def test_every_exercise_has_a_youtube_video():
    for _, _, _, (name, *_rest, url) in exercises():
        assert re.fullmatch(r"https://www\.youtube\.com/watch\?v=[\w-]{11}", url), name
    assert set(LIB["kettlebell"]) == {"push", "pull", "legs"}
    for kb in LIB["kettlebell"].values():
        assert re.fullmatch(r"https://www\.youtube\.com/watch\?v=[\w-]{11}", kb["url"])


def test_exercises_rotate_between_blocks():
    a, b, c = ({e[0] for e in sum(LIB["blocks"][k].values(), [])} for k in "ABC")
    assert len(a & b) <= 2 and len(b & c) <= 2 and len(a & c) <= 2
