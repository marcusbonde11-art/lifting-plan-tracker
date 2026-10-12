"""Generate the Make.com scenario blueprints into make/.

Usage:  python scripts/build_make.py <spreadsheetId>
        python scripts/build_make.py            (setup blueprint only)

Blueprints:
  make/setup.blueprint.json           one-shot: creates the spreadsheet
  make/weekly_generator.blueprint.json Saturday 7 am ET: builds next week's tab
  make/daily_email.blueprint.json     every 30 min, 6 am–11 pm ET: emails completed days
"""
import json
import pathlib
import sys

from layout import COLS, DAY_ROWS, SAT_ROW, TEMPLATE_SHEET_ID, editable_ranges, idx

ROOT = pathlib.Path(__file__).resolve().parent.parent
GOOGLE = 11391947  # "Marcus's Google connection" (Sheets)
GMAIL = 11391672   # "Marcus's Gmail connection"


def sheets_call(mid, url, method="GET", qs=None, body=None, note="", filt=None, x=0):
    m = {"id": mid, "module": "google-sheets:makeAPICall", "version": 2,
         "parameters": {"__IMTCONN__": GOOGLE},
         "mapper": {"url": url, "method": method},
         "metadata": {"designer": {"x": x, "y": 0}, "note": note}}
    if qs:
        m["mapper"]["qs"] = [{"key": k, "value": v} for k, v in qs]
    if body is not None:
        m["mapper"]["headers"] = [{"key": "Content-Type", "value": "application/json"}]
        m["mapper"]["body"] = body if isinstance(body, str) else json.dumps(body, ensure_ascii=False,
                                                                           separators=(",", ":"))
    if filt:
        m["filter"] = filt
    return m


def blueprint(name, flow):
    return {"name": name, "flow": flow,
            "metadata": {"version": 1, "instant": False,
                         "scenario": {"roundtrips": 1, "maxErrors": 3, "autoCommit": True,
                                      "autoCommitTriggerLast": True, "sequential": True,
                                      "confidential": False, "dataloss": False, "dlq": False,
                                      "freshVariables": False}}}


# ------------------------------------------------------------------ setup
def setup():
    create = (ROOT / "build" / "create.json").read_text()
    requests = (ROOT / "build" / "requests.json").read_text()
    return blueprint("Lifting – Setup (one-shot)", [
        sheets_call(1, "spreadsheets", "POST", body=create, note="Create the workbook with empty tabs"),
        sheets_call(2, "spreadsheets/{{1.body.spreadsheetId}}:batchUpdate", "POST", body=requests,
                    note="Fill Start Here, Config, Library, Outbox and the weekly _Template", x=300),
    ])


# ------------------------------------------------------------------ weekly generator
def generator(sid):
    v = lambda row: "{{1.body.values[1][%d]}}" % (row - 1)  # Config!B<row>, 1-based arrays, B2 is [1]
    week, name, sheet_id, cur_tab, flag = v(12), v(13), v(14), v(4), v(16)
    unprotected = json.dumps(editable_ranges("@@SID@@"), separators=(",", ":")).replace('"@@SID@@"', sheet_id)
    build = ('{"requests":['
             f'{{"duplicateSheet":{{"sourceSheetId":{TEMPLATE_SHEET_ID},"insertSheetIndex":0,'
             f'"newSheetId":{sheet_id},"newSheetName":"{name}"}}}},'
             f'{{"updateSheetProperties":{{"properties":{{"sheetId":{sheet_id},"hidden":false}},"fields":"hidden"}}}},'
             f'{{"updateCells":{{"start":{{"sheetId":{sheet_id},"rowIndex":0,"columnIndex":{idx("key")}}},'
             f'"rows":[{{"values":[{{"userEnteredValue":{{"stringValue":"{name}"}}}},'
             f'{{"userEnteredValue":{{"numberValue":{week}}}}},'
             f'{{"userEnteredValue":{{"stringValue":"{cur_tab}"}}}}]}}],"fields":"userEnteredValue"}}}},'
             f'{{"addProtectedRange":{{"protectedRange":{{"range":{{"sheetId":{sheet_id}}},'
             f'"description":"Only the yellow cells are yours to edit","warningOnly":true,'
             f'"unprotectedRanges":{unprotected}}}}}}}'
             ']}')

    def freeze(c1, c2):
        g = (f'{{"sheetId":{sheet_id},"startRowIndex":3,"endRowIndex":{SAT_ROW},'
             f'"startColumnIndex":{idx(c1)},"endColumnIndex":{idx(c2) + 1}}}')
        return f'{{"copyPaste":{{"source":{g},"destination":{g},"pasteType":"PASTE_VALUES"}}}}'

    # Snapshot exercises, prescriptions, rest and suggested weights (C:E) plus the hidden
    # lookup columns (O:W) as values, so later Library edits never rewrite past weeks.
    # The body-weight cell on each day-header row (D) is a live lookup into Daily Weight,
    # so restore it from the template after the freeze.
    def restore_weight(h):
        g = lambda sid: (f'{{"sheetId":{sid},"startRowIndex":{h - 1},"endRowIndex":{h},'
                         f'"startColumnIndex":{idx("rest")},"endColumnIndex":{idx("rest") + 1}}}')
        return f'{{"copyPaste":{{"source":{g(TEMPLATE_SHEET_ID)},"destination":{g(sheet_id)},"pasteType":"PASTE_NORMAL"}}}}'
    snapshot = ('{"requests":[' + ",".join([freeze("prescription", "suggested"), freeze("key", "name")]
                                           + [restore_weight(h) for h in DAY_ROWS]) + "]}")
    only_when_due = {"name": "Only when next week is due (Saturday) and not built yet",
                     "conditions": [[{"a": flag, "o": "text:equal", "b": "true"}]]}
    return blueprint("Lifting – Weekly Tab Generator (Sat 7am)", [
        sheets_call(1, f"spreadsheets/{sid}/values/Config!B2:B16", qs=[("majorDimension", "COLUMNS"),
                                                                      ("valueRenderOption", "UNFORMATTED_VALUE")],
                    note="Config: current/next week, next tab name, generate flag"),
        sheets_call(2, f"spreadsheets/{sid}:batchUpdate", "POST", body=build, filt=only_when_due, x=300,
                    note="Copy _Template → new week tab, stamp week #/previous tab, lock all but yellow cells"),
        sheets_call(3, f"spreadsheets/{sid}:batchUpdate", "POST", body=snapshot, x=600,
                    note="Freeze the week's exercises and suggested weights as values; keep the body-weight lookups live"),
        sheets_call(4, f"spreadsheets/{sid}/values/Config!B3:B5", "PUT",
                    qs=[("valueInputOption", "USER_ENTERED")],
                    body='{"values":[[' + week + '],["' + name + '"],["' + cur_tab + '"]]}', x=900,
                    note="Advance Config: current week, current tab, previous tab"),
    ])


# ------------------------------------------------------------------ daily email
def daily_email(sid):
    part = lambda n: '{{get(split(2.value; "§§"); %d)}}' % n
    return blueprint("Lifting – Workout Complete Email (every 30 min)", [
        sheets_call(1, f"spreadsheets/{sid}/values/Outbox!A1:B13", qs=[("majorDimension", "COLUMNS")],
                    note="Pending summaries (days ticked complete, not yet emailed) + recipient"),
        {"id": 2, "module": "builtin:BasicFeeder", "version": 1, "parameters": {},
         "mapper": {"array": "{{1.body.values[1]}}"},
         "metadata": {"designer": {"x": 300, "y": 0}}},
        {"id": 3, "module": "google-email:sendAnEmail", "version": 4,
         "parameters": {"__IMTCONN__": GMAIL},
         "filter": {"name": "Only real pending emails",
                    "conditions": [[{"a": "{{2.value}}", "o": "text:contain", "b": "§§"}]]},
         "mapper": {"to": ["{{1.body.values[2][1]}}"], "subject": part(1), "bodyType": "rawHtml",
                    "content": part(3)},
         "metadata": {"designer": {"x": 600, "y": 0}}},
        sheets_call(4, f"spreadsheets/{sid}/values/{part(2)}", "PUT",
                    qs=[("valueInputOption", "USER_ENTERED")],
                    body='{"values":[["Sent {{formatDate(now; "ddd h:mm A"; "America/New_York")}}"]]}',
                    x=900, note="Stamp 'Email sent' so the day is never emailed twice"),
    ])


def main():
    out = ROOT / "make"
    out.mkdir(exist_ok=True)
    targets = [("setup.blueprint.json", setup())]
    if len(sys.argv) > 1:
        sid = sys.argv[1]
        targets += [("weekly_generator.blueprint.json", generator(sid)),
                    ("daily_email.blueprint.json", daily_email(sid))]
    for fname, bp in targets:
        (out / fname).write_text(json.dumps(bp, ensure_ascii=False, indent=1))
        print("wrote make/" + fname)


if __name__ == "__main__":
    main()
