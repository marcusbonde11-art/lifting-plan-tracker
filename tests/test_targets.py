import pathlib
import sys
from datetime import date

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))

from targets import lean_mass, maintenance, surplus, targets  # noqa: E402

TODAY = date(2026, 10, 12)


def test_protein_follows_lean_mass_not_total_weight():
    a = targets(200, 20)   # 160 lb lean
    b = targets(200, 10)   # 180 lb lean, same body weight
    assert a["protein_g"] == 160 and b["protein_g"] == 180


def test_maintenance_from_lean_mass():
    assert maintenance(160) == round((370 + 21.6 * 160 / 2.20462) * 1.55, -1)


def test_default_surplus_without_goal():
    assert surplus(190) == 300


def test_surplus_scales_to_goal_and_is_capped():
    assert surplus(190, 200, date(2027, 2, 15), TODAY) == 280   # 10 lb in ~18 weeks
    assert surplus(190, 220, date(2026, 11, 12), TODAY) == 500  # aggressive goal → capped
    assert surplus(190, 191, date(2027, 10, 12), TODAY) == 150  # tiny goal → floor
    assert surplus(205, 200, date(2027, 2, 15), TODAY) == 0     # goal reached


def test_targets_recalculate_with_new_scan():
    before = targets(190, 18, 200, date(2027, 2, 15), TODAY)
    after = targets(192, 17, 200, date(2027, 2, 15), TODAY)
    assert after["lbm"] == lean_mass(192, 17) and after["protein_g"] > before["protein_g"]
