"""Turn the five fields read off an InBody printout into a checked Body Log write.

Claude reads the photo; this script decides whether the values are safe to write
and where they go. It never writes to the sheet itself: it prints the ranges and
values for the Google Sheets connector (valueInputOption USER_ENTERED).

Usage:
  python scripts/inbody.py --date 2026-10-18 --time "7:42 AM" --weight 218.8 \
      --bf 15.8 --smm 105.4 --vfl 6 --existing "Mon Oct 12, 2026" ""
  Pass "?" for any field that could not be read clearly.
  --existing is 'Body Log'!A16:A215 as formatted values (blank rows as "").

Output (JSON): ok, problems, row, duplicate_row, writes.
"""
import argparse
import datetime
import json

from build_logs import FIRST, LAST

TAB = "Body Log"
UNREADABLE = "?"

# field: (label, unit, low, high, whole number?) – ranges catch misreads such as a dropped decimal point
LIMITS = {
    "weight": ("Weight", "lb", 80, 500, False),
    "bf": ("Body fat %", "%", 2, 70, False),
    "smm": ("Skeletal muscle mass", "lb", 30, 200, False),
    "vfl": ("Visceral fat level", "", 1, 20, True),
}
DATE_FORMATS = ("%Y-%m-%d", "%Y.%m.%d", "%m/%d/%Y", "%a %b %d, %Y")
TIME_FORMATS = ("%I:%M %p", "%H:%M", "%I:%M%p")


def parse_date(text):
    for f in DATE_FORMATS:
        try:
            return datetime.datetime.strptime(text.strip(), f).date()
        except ValueError:
            pass
    return None


def parse_time(text):
    for f in TIME_FORMATS:
        try:
            return datetime.datetime.strptime(text.strip().upper(), f).time()
        except ValueError:
            pass
    return None


def check(fields, today=None):
    """Return (clean values, problems). Any problem means nothing gets written."""
    today = today or datetime.date.today()
    clean, problems = {}, []
    for key in ("date", "time", *LIMITS):
        raw = (fields.get(key) or "").strip()
        label = LIMITS[key][0] if key in LIMITS else "Test " + key
        if raw in ("", UNREADABLE):
            problems.append(f"{label}: not readable in the photo")
            continue
        if key == "date":
            d = parse_date(raw)
            if d is None:
                problems.append(f"{label}: '{raw}' is not a date")
            elif d > today or d < today - datetime.timedelta(days=365):
                problems.append(f"{label}: {d} is in the future or over a year ago")
            else:
                clean[key] = d
        elif key == "time":
            t = parse_time(raw)
            if t is None:
                problems.append(f"{label}: '{raw}' is not a time")
            else:
                clean[key] = t
        else:
            name, unit, low, high, whole = LIMITS[key]
            try:
                v = float(raw)
            except ValueError:
                problems.append(f"{name}: '{raw}' is not a number")
                continue
            if whole and v != int(v):
                problems.append(f"{name}: {raw} should be a whole number")
            elif not low <= v <= high:
                problems.append(f"{name}: {raw} {unit} is outside {low}–{high} {unit}; likely a misread")
            else:
                clean[key] = int(v) if whole else v
    return clean, problems


def plan(clean, existing):
    """Pick the Body Log row: the first empty one, plus any row already holding that date."""
    row = dup = None
    for i, text in enumerate(existing):
        r = FIRST + i
        d = parse_date(text) if text.strip() else None
        if d == clean["date"] and dup is None:
            dup = r
        if not text.strip() and row is None:
            row = r
    if row is None:
        row = FIRST + len(existing)
    if row > LAST:
        raise SystemExit(f"Body Log is full (last formula row is {LAST})")
    return row, dup


def writes(clean, row):
    """A:D and F:G – column E is the lean-mass ARRAYFORMULA and must stay empty."""
    return [{"range": f"'{TAB}'!A{row}:D{row}",
             "values": [[clean["date"].isoformat(), clean["weight"], clean["bf"], clean["smm"]]]},
            {"range": f"'{TAB}'!F{row}:G{row}",
             "values": [[clean["vfl"], clean["time"].strftime("%-I:%M %p")]]}]


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for key in ("date", "time", *LIMITS):
        p.add_argument("--" + key, default="")
    p.add_argument("--existing", nargs="*", default=[])
    a = p.parse_args(argv)
    clean, problems = check(vars(a))
    out = {"ok": not problems, "problems": problems, "row": None, "duplicate_row": None, "writes": []}
    if not problems:
        out["row"], out["duplicate_row"] = plan(clean, a.existing)
        out["writes"] = writes(clean, out["duplicate_row"] or out["row"])
    print(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    main()
