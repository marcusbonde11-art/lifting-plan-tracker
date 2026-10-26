"""Every session fits 15 min kettlebell + 30 min lifting; the heavy lift still gets ~2.5 min rest."""
import pathlib
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
import program  # noqa: E402
import timing  # noqa: E402

LIB = yaml.safe_load((pathlib.Path(__file__).resolve().parent.parent / "program" / "library.yaml").read_text())
T = LIB["timing"]


def all_days(lib=LIB):
    for block, days in lib["blocks"].items():
        for day, exercises in days.items():
            yield f"{block} {day}", exercises


def test_every_day_fits_the_cap_including_adjustments():
    lib = program.load()
    for name, exercises in all_days(lib):
        block, day = name.split()
        _, total = timing.day_minutes(exercises, T, program.rest_for(lib, block, day))
        assert total <= T["cap_min"], (name, total)
        assert total + T["kettlebell_min"] <= 45, name


def test_the_standard_day_math():
    exercises = LIB["blocks"]["D"]["P1"]
    ss, total = timing.day_minutes(exercises, T)
    assert ss == [14.0, 7.5, 7.5]   # 2 ramp-up + 4 x 3:00, then 3 x 2:30 twice
    assert total == 30.0            # + 2 x 0.5 min walking between supersets


def test_heavy_lift_rest_is_about_two_and_a_half_minutes():
    for name, exercises in all_days():
        assert 140 <= timing.heavy_rest_seconds(exercises, T) <= 180, name


def test_an_extra_set_with_shorter_rest_still_fits():
    exercises = [list(e) for e in LIB["blocks"]["D"]["P1"]]
    exercises[2][2] = 4  # 2A gets a 4th set: 3 full rounds + 1 single-exercise round
    assert timing.day_minutes(exercises, T)[1] > T["cap_min"]
    ss, total = timing.day_minutes(exercises, T, [90, 30, 30])
    assert ss == [14.0, 8.0, 6.8] and total <= T["cap_min"]


def test_slots_and_rest_text():
    assert [timing.slot(o) for o in range(1, 7)] == ["1A", "1B", "2A", "2B", "3A", "3B"]
    exercises = LIB["blocks"]["D"]["L1"]
    assert timing.rest_text(1, exercises, T) == "→ 1B now"
    assert timing.rest_text(2, exercises, T) == "rest 90 s → 1A · 4 rounds ≈ 14 min incl. ramp-up"
    assert timing.rest_text(4, exercises, T) == "rest 45 s → 2A · 3 rounds ≈ 7.5 min"
