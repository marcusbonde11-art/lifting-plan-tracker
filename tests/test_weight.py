"""Daily Weight tab: starts the Monday of week 1 and is wired into the weekly tab."""
import datetime
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
import build_logs  # noqa: E402
from layout import DAY_ROWS, PROGRAM_START, editable_ranges, idx  # noqa: E402


def test_log_starts_monday_of_week_one():
    start = datetime.date(*build_logs.WEIGHT_START)
    assert start == datetime.date(*PROGRAM_START) + datetime.timedelta(days=1)
    assert start.weekday() == 0


def test_weekly_body_weight_cell_is_read_only():
    rest = idx("rest")
    for r in editable_ranges(1):
        assert not (r["startColumnIndex"] <= rest < r["endColumnIndex"] and r["startRowIndex"] + 1 in DAY_ROWS)


def test_chart_and_email_lookup_present():
    reqs = build_logs.weight_requests()
    assert any("addChart" in r for r in reqs)
    assert "'Daily Weight'!" in build_logs.weight_lookup("A1", 2)
