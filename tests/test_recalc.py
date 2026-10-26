"""End-of-block recalculation rules, on a made-up block D (weeks 4-9) with Marcus's real Oct 26 scan."""
import datetime
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
import program  # noqa: E402
import recalc  # noqa: E402
import timing  # noqa: E402
from layout import COLS  # noqa: E402

TODAY = datetime.date(2026, 12, 10)  # Thursday of week 9 = week 6 of block D
OCT26 = ["Mon Oct 26, 2026", "215.9", "15.9", "103.6", "181.6", "7", "6:48 AM",
         "10.94", "10.74", "78.7", "28.68", "28.82", "120.9", "118.6", "109.2", "114.0", "114.5", "34.2", "0.378", "2150"]
DEC07 = ["Mon Dec 7, 2026", "219.0", "15.8", "105.6", "184.4", "7", "6:40 AM",
         "11.30", "10.80", "79.0", "29.40", "29.50", "124.0", "118.5", "109.6", "118.0", "118.4", "34.6", "0.377", "2180"]
CONFIG = ["Sun Oct 11, 2026", "9", "Wk 09 · Dec 6", "Wk 08 · Nov 29", "6", "3", "x", "", "Marcus", "9",
          "10", "", "", "", "FALSE", "", "", "", "4"]
TARGETS = ["Mon Dec 7, 2026", "219", "15.8", "105.6", "184.4", "235", "Tue Jun 1, 2027", "1.55",
           "3330", "310", "3640", "182"]


def row(**kw):
    r = [""] * (COLS.index("name") + 1)
    for k, v in kw.items():
        r[COLS.index(k)] = v
    return r


LIB = program.load()


def week_tab(week, complete_days, amrap_bench):
    rows = []
    for day in ("P1", "PU1", "L1", "P2", "PU2", "L2"):
        rows.append(row(daykey=day, complete="TRUE" if day in complete_days else "FALSE"))
        rows.append(row(key=f"D|{day}|1", name=LIB["blocks"]["D"][day][0][0], type="Heavy",
                        suggested="185", lifted="", amrap=str(amrap_bench), next="190"))
    return rows


def data(sessions_per_week=5, food_days=14, kcal="3700", protein="190", scans=(OCT26, DEC07)):
    days = ["P1", "PU1", "L1", "P2", "PU2", "L2"][:sessions_per_week]
    nutrition = [[(datetime.date(2026, 11, 2) + datetime.timedelta(days=i)).strftime("%a %b %-d, %Y"),
                  "food", "100", kcal, protein] for i in range(food_days)]
    weight = [["", "", "216.0"]] * 20 + [["", "", "219.0"]] * 40
    return {"config": CONFIG, "body_targets": TARGETS, "body_log": list(scans), "nutrition": nutrition,
            "daily_weight": weight,
            "tabs": {f"Wk {w:02d} · x": week_tab(w, days, 7) for w in range(4, 10)}}


def test_block_info_week_six_of_block_d():
    info = recalc.block_info(CONFIG)
    assert (info["block"], info["next_block"], info["week_in_block"]) == ("D", "E", 6)
    assert info["start_date"] == datetime.date(2026, 11, 1)


def test_oct26_scan_trunk_lags_and_sides_are_balanced():
    scan = recalc.parse_scans([OCT26])[0]
    lag, leading, _ = recalc.lagging(scan, None)
    assert lag == {"trunk"} and leading == "arms"
    uneven, _ = recalc.imbalances(scan)
    assert uneven == []  # left arm 1.8% lighter: under the 3% limit


def test_lagging_trunk_gets_a_set_and_every_day_still_fits():
    result = recalc.run(data(), TODAY)
    ch = result["changes"]
    lib = program.load(adjustments={"blocks": {"E": ch}})
    assert ch["sets"], ch
    for key, sets in ch["sets"].items():
        day, order = key.split("|")
        row = lib["blocks"]["E"][day][int(order) - 1]
        assert row[2] == sets
        if sets == 4:
            assert recalc.GROUP[row[7]] == "trunk"
    for day, rows in lib["blocks"]["E"].items():
        assert timing.day_minutes(rows, lib["timing"], program.rest_for(lib, "E", day))[1] <= 30


def test_no_extra_sets_when_attendance_is_low():
    result = recalc.run(data(sessions_per_week=3), TODAY)
    assert result["changes"]["sets"] == {}
    assert any(r[0] == "Volume" for r in result["review"])


def test_no_extra_sets_when_protein_is_short():
    result = recalc.run(data(protein="120"), TODAY)
    assert result["changes"]["sets"] == {}


def test_uneven_arms_switch_to_one_arm_work():
    lopsided = recalc.parse_scans([OCT26])[0]
    lopsided["la_lb"] = 10.0   # left arm 8.6% lighter than right
    uneven, _ = recalc.imbalances(lopsided)
    assert uneven == ["arms"]
    # block F's rope hammer curl / Smith JM press are two-handed -> one-arm versions
    days, ch, notes = recalc.plan_next_block(LIB, "F", set(), None, uneven, add_volume=False)
    assert ch["swap"] and all(recalc.GROUP[days[k.split("|")[0]][int(k.split("|")[1]) - 1][7]] == "arms"
                              for k in ch["swap"])
    assert ch["swap"]["P2|2"] == "Dumbbell Hammer Curl"
    # block E is already dumbbell / one-arm work: nothing to swap, the review says so
    result = recalc.run(data(scans=(OCT26, [*DEC07[:8], "10.00", *DEC07[9:]])), TODAY)
    assert result["changes"]["swap"] == {}
    assert any("already one-arm" in r[1] for r in result["review"])


def test_heavy_start_weight_from_amrap():
    # 185 x 7 -> est. max 228 -> 85% = 193.8 -> 190, the same as last week's suggestion
    result = recalc.run(data(), TODAY)
    assert result["changes"]["start_lb"]["L1|1"] == 190  # belt squat carries into block E


def test_apply_writes_adjustments(tmp_path):
    result = recalc.run(data(), TODAY)
    path = tmp_path / "adjustments.yaml"
    recalc.apply(result, path)
    import yaml
    saved = yaml.safe_load(path.read_text())
    assert saved["blocks"]["E"]["review_date"] == "2026-12-10"
