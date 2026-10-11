import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))

from progression import next_week, target_hit  # noqa: E402


def test_heavy_amrap_at_top_of_range_progresses():
    hit = target_hit("Heavy", 5, amrap=5, lifted=185, day_complete=True)
    assert hit is True
    assert next_week(185, 185, hit, 5) == 190


def test_heavy_amrap_below_range_repeats():
    hit = target_hit("Heavy", 5, amrap=4, lifted=185, day_complete=True)
    assert hit is False
    assert next_week(185, 185, hit, 5) == 185


def test_heavy_without_amrap_is_undecided_and_repeats():
    hit = target_hit("Heavy", 5, amrap=None, lifted=None, day_complete=False)
    assert hit is None
    assert next_week(185, None, hit, 5) == 185


def test_legs_heavy_uses_leg_increment():
    hit = target_hit("Heavy", 5, amrap=7, lifted=225, day_complete=True)
    assert next_week(225, 225, hit, 10) == 235


def test_accessory_progresses_when_day_complete_with_weight():
    hit = target_hit("Isolation", 12, amrap=None, lifted=25, day_complete=True)
    assert hit is True
    assert next_week(25, 25, hit, 2.5) == 27.5


def test_accessory_without_logged_weight_repeats():
    hit = target_hit("Compound-acc", 12, amrap=None, lifted=None, day_complete=True)
    assert hit is False
    assert next_week(60, None, hit, 5) == 60


def test_accessory_not_complete_repeats():
    hit = target_hit("Compound-acc", 12, amrap=None, lifted=60, day_complete=False)
    assert hit is None
    assert next_week(60, 60, hit, 5) == 60


def test_manual_override_becomes_new_baseline():
    # suggested 100, he lifted 110 and hit target -> 110 + 5, not 100 + 5
    hit = target_hit("Heavy", 5, amrap=6, lifted=110, day_complete=True)
    assert next_week(100, 110, hit, 5) == 115
    # suggested 100, he dropped to 90 and missed -> stays at his 90
    hit = target_hit("Heavy", 5, amrap=3, lifted=90, day_complete=True)
    assert next_week(100, 90, hit, 5) == 90


def test_first_week_with_nothing_known_is_blank():
    assert next_week(None, None, None, 5) is None
