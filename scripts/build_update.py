"""batchUpdate bodies that move the LIVE sheet to the current program, without re-running Setup.

The live workbook also holds other tabs (Today, Backlog, Business …), so Setup must never be
re-run on it. This writes targeted updates instead, one file per area:

  build/update_library.json   Library tab (resize, clear, paste, format)
  build/update_template.json  hidden _Template tab (clear, rebuild the 6 days)
  build/update_misc.json      Start Here text, Config row 20, Outbox formula
  build/update_bodylog.json   Body Log body-part columns H:T (headers, yellow formats, widths)

Apply each file's "requests" with the Google Sheets connector (spreadsheets.batchUpdate).
Usage:  python scripts/build_update.py
        python scripts/build_update.py --block E   just block E's Library rows, as
                                                   {"range", "values"} for update_values
"""
import json
import pathlib
import sys

import build_logs
import build_sheet as b
from layout import CONFIG_SHEET_ID, OUTBOX_SHEET_ID, START_SHEET_ID, TEMPLATE_SHEET_ID

ROOT = pathlib.Path(__file__).resolve().parent.parent


def without_locks(reqs):
    """The live tabs already carry their protections; don't stack duplicates."""
    return [r for r in reqs if "addProtectedRange" not in r]


def clear(sheet_id):
    return {"updateCells": {"range": {"sheetId": sheet_id}, "fields": "userEnteredValue,userEnteredFormat,dataValidation"}}


def resize(sheet_id, rows, cols):
    return {"updateSheetProperties": {"properties": {"sheetId": sheet_id,
                                                     "gridProperties": {"rowCount": rows, "columnCount": cols}},
                                      "fields": "gridProperties.rowCount,gridProperties.columnCount"}}


def library():
    return [resize(b.LIBRARY_SHEET_ID, len(b.library_rows()) + 5, len(b.LIB_HEADERS)), clear(b.LIBRARY_SHEET_ID),
            *without_locks(b.library_requests())]


def template():
    # _Template is 599 x 29 live; clearing it first removes the old 5-exercise days.
    return [clear(TEMPLATE_SHEET_ID), *b.template_requests()]


def misc():
    start_rows = [[b.cell(t, bold=bold, size=14 if bold else 11, wrap=True)] for t, bold in b.START]
    return [resize(START_SHEET_ID, len(start_rows) + 3, 1), clear(START_SHEET_ID),
            b.write(START_SHEET_ID, 1, start_rows),
            b.write(CONFIG_SHEET_ID, len(b.CONFIG) + 1,
                    [[b.cell(b.CONFIG[-1][0], bold=True), b.cell(b.CONFIG[-1][1]),
                      b.cell(b.CONFIG[-1][2], fg=b.MUTED, italic=True)]]),
            *without_locks(b.outbox_requests())]


def bodylog():
    return [resize(build_logs.BODY_SHEET_ID, build_logs.FIRST + build_logs.LOG_ROWS + 5, len(build_logs.BODY_HEADERS)),
            *build_logs.segmental_requests()]


def library_block_values(block):
    """Block `block`'s rows of the Library tab (row 1 is the header), as a values write."""
    rows = b.library_rows()
    idx = [i for i, r in enumerate(rows) if r[1] == block]
    first, last = idx[0] + 2, idx[-1] + 2
    return {"range": f"Library!A{first}:S{last}", "values": [rows[i] for i in idx]}


def main():
    if "--block" in sys.argv:
        print(json.dumps(library_block_values(sys.argv[sys.argv.index("--block") + 1]), ensure_ascii=False))
        return
    out = ROOT / "build"
    for name, reqs in (("library", library()), ("template", template()), ("misc", misc()), ("bodylog", bodylog())):
        text = json.dumps({"requests": reqs}, ensure_ascii=False, separators=(",", ":"))
        (out / f"update_{name}.json").write_text(text)
        print(f"wrote build/update_{name}.json ({len(text.encode()) // 1024} KB, {len(reqs)} requests)")


if __name__ == "__main__":
    main()
