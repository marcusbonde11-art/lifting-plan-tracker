"""InBody photo → Body Log: unreadable or implausible fields block the write; rows land in A:D + F:T."""
import datetime
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
import build_logs  # noqa: E402
import inbody  # noqa: E402

TODAY = datetime.date(2026, 10, 26)
# Marcus's Oct 26, 2026 printout, field by field
GOOD = {"date": "2026.10.26", "time": "06:48", "weight": "215.9", "bf": "15.9", "smm": "103.6", "vfl": "7",
        "ra_lb": "10.94", "la_lb": "10.74", "tr_lb": "78.7", "rl_lb": "28.68", "ll_lb": "28.82",
        "ra_pct": "120.9", "la_pct": "118.6", "tr_pct": "109.2", "rl_pct": "114.0", "ll_pct": "114.5",
        "bfm": "34.2", "ecw": "0.378", "bmr": "2150"}


def test_clear_scan_passes():
    clean, problems = inbody.check(GOOD, TODAY)
    assert problems == []
    assert clean["vfl"] == 7 and clean["weight"] == 215.9 and clean["bmr"] == 2150


def test_unreadable_field_is_flagged_not_guessed():
    clean, problems = inbody.check({**GOOD, "bf": "?"}, TODAY)
    assert problems == ["Body fat %: not readable in the photo"]
    assert "bf" not in clean


def test_misread_out_of_range_is_flagged():
    _, problems = inbody.check({**GOOD, "smm": "1036", "vfl": "6.5", "date": "2026-11-01"}, TODAY)
    assert len(problems) == 3


def test_unreadable_body_part_blocks_the_whole_write():
    _, problems = inbody.check({**GOOD, "la_pct": "?"}, TODAY)
    assert problems == ["Left arm % of ideal: not readable in the photo"]


def test_segmental_ranges():
    _, problems = inbody.check({**GOOD, "ra_lb": "109.4", "ecw": "3.78"}, TODAY)
    assert len(problems) == 2


def test_cross_checks_catch_in_range_misreads():
    # 43.2 is in range for body fat mass but doesn't match 215.9 lb x 15.9 %
    _, problems = inbody.check({**GOOD, "bfm": "43.2"}, TODAY)
    assert any(p.startswith("Body fat mass") for p in problems)
    _, problems = inbody.check({**GOOD, "bmr": "2750"}, TODAY)
    assert any(p.startswith("BMR") for p in problems)


def test_next_empty_row_and_duplicate_detection():
    clean, _ = inbody.check(GOOD, TODAY)
    assert inbody.plan(clean, ["Mon Oct 12, 2026", ""]) == (build_logs.FIRST + 1, None)
    assert inbody.plan(clean, ["Mon Oct 12, 2026"]) == (build_logs.FIRST + 1, None)
    assert inbody.plan(clean, ["Mon Oct 12, 2026", "Mon Oct 26, 2026"])[1] == build_logs.FIRST + 1


def test_writes_skip_lean_mass_formula_column():
    clean, _ = inbody.check(GOOD, TODAY)
    w = inbody.writes(clean, 17)
    assert [x["range"] for x in w] == ["'Body Log'!A17:D17", "'Body Log'!F17:T17"]
    assert w[1]["values"] == [[7, "6:48 AM", 10.94, 10.74, 78.7, 28.68, 28.82,
                               120.9, 118.6, 109.2, 114.0, 114.5, 34.2, 0.378, 2150]]


def test_body_log_columns():
    assert build_logs.BODY_HEADERS[5:7] == ["Visceral fat level", "Test time"]
    assert len(build_logs.BODY_HEADERS) == 20  # A..T
    assert build_logs.BODY_HEADERS[7] == "Right arm lean (lb)"
    assert build_logs.BODY_HEADERS[-1] == "BMR (kcal)"
