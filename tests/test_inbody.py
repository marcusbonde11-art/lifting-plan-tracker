"""InBody photo → Body Log: unreadable or implausible fields block the write; rows land in A:D + F:G."""
import datetime
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
import build_logs  # noqa: E402
import inbody  # noqa: E402

TODAY = datetime.date(2026, 10, 18)
GOOD = {"date": "2026-10-18", "time": "7:42 AM", "weight": "219.6", "bf": "15.4", "smm": "106.0", "vfl": "6"}


def test_clear_scan_passes():
    clean, problems = inbody.check(GOOD, TODAY)
    assert problems == []
    assert clean["vfl"] == 6 and clean["weight"] == 219.6


def test_unreadable_field_is_flagged_not_guessed():
    clean, problems = inbody.check({**GOOD, "bf": "?"}, TODAY)
    assert problems == ["Body fat %: not readable in the photo"]
    assert "bf" not in clean


def test_misread_out_of_range_is_flagged():
    _, problems = inbody.check({**GOOD, "smm": "1060", "vfl": "6.5", "date": "2026-11-01"}, TODAY)
    assert len(problems) == 3


def test_next_empty_row_and_duplicate_detection():
    clean, _ = inbody.check(GOOD, TODAY)
    assert inbody.plan(clean, ["Mon Oct 12, 2026", ""]) == (build_logs.FIRST + 1, None)
    assert inbody.plan(clean, ["Mon Oct 12, 2026"]) == (build_logs.FIRST + 1, None)
    assert inbody.plan(clean, ["Mon Oct 12, 2026", "Sun Oct 18, 2026"])[1] == build_logs.FIRST + 1


def test_writes_skip_lean_mass_formula_column():
    clean, _ = inbody.check(GOOD, TODAY)
    w = inbody.writes(clean, 17)
    assert [x["range"] for x in w] == ["'Body Log'!A17:D17", "'Body Log'!F17:G17"]
    assert w[1]["values"] == [[6, "7:42 AM"]]


def test_body_log_has_seven_columns():
    assert build_logs.BODY_HEADERS[5:] == ["Visceral fat level", "Test time"]
