"""Body Log (weekly InBody + daily targets), Monthly Check-in and Nutrition tabs."""
from build_sheet import DATE, DAY_BG, EDIT_BG, HEADER_BG, MUTED, NUM, WHITE, cell, grid, widths, write

WDATE = {"type": "DATE", "pattern": "ddd mmm d"}
NUM1 = {"type": "NUMBER", "pattern": "0.0"}


def paint(sheet_id, r1, r2, c1, c2, **fmt):
    """Format a whole block with one repeatCell (keeps the payload small)."""
    return {"repeatCell": {"range": grid(sheet_id, r1, c1, r2, c2), "cell": cell(**fmt),
                           "fields": "userEnteredFormat"}}

BODY_SHEET_ID, MONTHLY_SHEET_ID, NUTRITION_SHEET_ID = 5, 6, 7
LOG_ROWS = 200  # pre-filled formula rows in the logs

# ------------------------------------------------------------------ Body Log
# Rows 2-13: targets block (B7:B9 are inputs). Row 15: headers. Rows 16+: weekly InBody scans.
FIRST = 16
LAST = FIRST + LOG_ROWS - 1
LATEST = (f'IFERROR(INDEX(SORT(FILTER(A{FIRST}:E{LAST},ISNUMBER(A{FIRST}:A{LAST}),'
          f'ISNUMBER(B{FIRST}:B{LAST}),ISNUMBER(C{FIRST}:C{LAST})),1,FALSE),1,{{c}}),"")')

BODY_TARGETS = [  # (label, value, note, format, is_input) – rows 2..13
    ("Latest scan date", "=" + LATEST.format(c=1), "Most recent InBody entry below.", DATE, False),
    ("Weight (lb)", "=" + LATEST.format(c=2), "", NUM, False),
    ("Body fat %", "=" + LATEST.format(c=3), "", NUM, False),
    ("Skeletal muscle mass (lb)", "=" + LATEST.format(c=4), "", NUM, False),
    ("Lean body mass (lb)", "=" + LATEST.format(c=5), "Weight × (1 − body fat %). Targets use this, not total weight.", NUM, False),
    ("Goal weight (lb)", None, "Yours to fill in.", NUM, True),
    ("Goal date", None, "Yours to fill in.", DATE, True),
    ("Activity multiplier", 1.55, "1.55 = lifting 6 days/week. Adjust if needed.", NUM, True),
    ("Maintenance calories", '=IF(B6="","",ROUND((370+21.6*B6/2.20462)*B9,-1))',
     "Katch-McArdle BMR from lean mass × activity.", NUM, False),
    ("Surplus (kcal/day)",
     '=IF(B6="","",IF(AND(ISNUMBER(B7),ISNUMBER(B8)),IF(B7<=B3,0,IF(B8<=TODAY(),500,'
     'ROUND(MIN(500,MAX(150,(B7-B3)/((B8-TODAY())/7)*500)),-1))),300))',
     "Scaled to reach the goal by the goal date (≈500 kcal/day per lb/week), 150–500. "
     "+300 until a goal is set; 0 once the goal is reached.", NUM, False),
    ("Daily calorie target", '=IF(B10="","",B10+B11)', "", NUM, False),
    ("Daily protein target (g)", '=IF(B6="","",ROUND(B6))', "≈1 g per lb of lean body mass.", NUM, False),
]
BODY_HEADERS = ["Date", "Weight (lb)", "Body fat %", "Skeletal muscle mass (lb)", "Lean body mass (lb)"]


def body_requests():
    S = BODY_SHEET_ID
    rows = [[cell("Daily targets – recalculate automatically from your latest InBody scan", bold=True, size=13)]]
    for label, value, note, fmt, inp in BODY_TARGETS:
        rows.append([cell(label, bold=True), cell(value, fmt=fmt, bg=EDIT_BG if inp else None, bold=not inp),
                     cell(note, fg=MUTED, italic=True)])
    rows.append([cell("Weekly InBody scans (newest can go at the bottom)", bold=True, size=13)])
    head = [cell(h, bold=True, bg=HEADER_BG, fg=WHITE, wrap=True, align="CENTER") for h in BODY_HEADERS]
    lbm = (f'=ARRAYFORMULA(IF(ISNUMBER(B{FIRST}:B{LAST})*ISNUMBER(C{FIRST}:C{LAST}),'
           f'ROUND(B{FIRST}:B{LAST}*(1-C{FIRST}:C{LAST}/100),1),""))')
    return [write(S, 1, rows), write(S, FIRST - 1, [head, [cell(), cell(), cell(), cell(), cell(lbm)]]),
            paint(S, FIRST, LAST, 1, 1, bg=EDIT_BG, fmt=DATE), paint(S, FIRST, LAST, 2, 4, bg=EDIT_BG, fmt=NUM),
            paint(S, FIRST, LAST, 5, 5, fmt=NUM), *widths(S, [190, 120, 120, 150, 150]),
            *[{"addProtectedRange": {"protectedRange": {
                "range": {"sheetId": S, "startRowIndex": r1, "endRowIndex": r2, "startColumnIndex": 1, "endColumnIndex": 2},
                "description": "Calculated targets", "warningOnly": True}}} for r1, r2 in ((1, 6), (9, 13))],
            {"addProtectedRange": {"protectedRange": {
                "range": {"sheetId": S, "startRowIndex": FIRST - 1, "endRowIndex": LAST,
                          "startColumnIndex": 4, "endColumnIndex": 5},
                "description": "Calculated lean body mass", "warningOnly": True}}}]


# ------------------------------------------------------------------ Monthly Check-in
def monthly_requests():
    S = MONTHLY_SHEET_ID
    head = [cell(h, bold=True, bg=HEADER_BG, fg=WHITE, wrap=True, align="CENTER")
            for h in ("Date", "Waist (in)", "Change vs last (in)", "Progress photos (link)", "Notes")]
    rows = [[cell("Monthly check-in – progress photos and waist", bold=True, size=13)],
            [cell("Take front/side/back photos in the same light, upload to Google Photos or Drive, paste the album link.",
                  fg=MUTED, italic=True)], head, [cell()],
            [cell(), cell(), cell('=ARRAYFORMULA(IF(ISNUMBER(B5:B63)*ISNUMBER(B4:B62),ROUND(B5:B63-B4:B62,2),""))')]]
    # data starts on row 4; the change formula sits in C5 and spills down (row N vs row N-1)
    return [write(S, 1, rows), paint(S, 4, 63, 1, 1, bg=EDIT_BG, fmt=DATE), paint(S, 4, 63, 2, 2, bg=EDIT_BG, fmt=NUM),
            paint(S, 4, 63, 3, 3, fmt=NUM), paint(S, 4, 63, 4, 5, bg=EDIT_BG, wrap=True),
            *widths(S, [130, 100, 130, 260, 260])]


# ------------------------------------------------------------------ Nutrition
def nutrition_requests():
    S = NUTRITION_SHEET_ID
    head = [cell(h, bold=True, bg=HEADER_BG, fg=WHITE, wrap=True, align="CENTER")
            for h in ("Date", "Food", "Grams (weighed)", "Calories", "Protein (g)", "Logged by")]
    rows = [[cell("Nutrition log – one row per weighed food", bold=True, size=13)],
            [cell("Today's targets", bold=True), cell("='Body Log'!B12", fmt=NUM, bold=True),
             cell("kcal"), cell("='Body Log'!B13", fmt=NUM, bold=True), cell("g protein")],
            [cell("Logged today", bold=True), cell("=SUMIF(A5:A,TODAY(),D5:D)", fmt=NUM, bold=True),
             cell("kcal"), cell("=SUMIF(A5:A,TODAY(),E5:E)", fmt=NUM, bold=True), cell("g protein")],
            head]
    end = 4 + LOG_ROWS * 3
    return [write(S, 1, rows), paint(S, 5, end, 1, 1, bg=EDIT_BG, fmt=DATE), paint(S, 5, end, 2, 2, bg=EDIT_BG),
            paint(S, 5, end, 3, 5, bg=EDIT_BG, fmt=NUM), paint(S, 5, end, 6, 6, bg=EDIT_BG),
            *widths(S, [120, 230, 90, 90, 90, 90]),
            {"addProtectedRange": {"protectedRange": {
                "range": {"sheetId": S, "startRowIndex": 0, "endRowIndex": 4},
                "description": "Totals and headers", "warningOnly": True}}}]


def add_sheets(start_index):
    def props(sid, title, idx, rows, cols, frozen, color):
        return {"addSheet": {"properties": {"sheetId": sid, "title": title, "index": idx,
                                            "gridProperties": {"rowCount": rows, "columnCount": cols,
                                                               "frozenRowCount": frozen},
                                            "tabColorStyle": {"rgbColor": color}}}}
    green = {"red": 0.086, "green": 0.639, "blue": 0.29}
    start_index += 1  # Daily Weight goes first
    return [add_weight_sheet(start_index - 1),
            props(BODY_SHEET_ID, "Body Log", start_index, FIRST + LOG_ROWS + 5, 5, 0, green),
            props(MONTHLY_SHEET_ID, "Monthly Check-in", start_index + 1, 70, 5, 3, green),
            props(NUTRITION_SHEET_ID, "Nutrition", start_index + 2, 5 + LOG_ROWS * 3 + 5, 6, 4, green)]


def log_requests():
    return body_requests() + monthly_requests() + nutrition_requests() + weight_requests()


# ------------------------------------------------------------------ Daily Weight
WEIGHT_SHEET_ID = 8
WEIGHT_START = (2026, 10, 12)  # first logged day (Mon of week 1)
W_FIRST, W_LAST = 4, 4 + 7 * 104  # two years of rows
_W = lambda c: f"{c}{W_FIRST}:{c}"
# Dates run through the end of the current week, so a new week of rows appears each
# Saturday morning when the generator advances Config!B3.
W_DATES = (f'=ARRAYFORMULA(SEQUENCE(Config!$B$2+MAX(1,Config!$B$3)*7-DATE({WEIGHT_START[0]},{WEIGHT_START[1]},'
           f'{WEIGHT_START[2]}),1,DATE({WEIGHT_START[0]},{WEIGHT_START[1]},{WEIGHT_START[2]})))')
W_AVG = (f'=MAP({_W("A")},{_W("B")},LAMBDA(d,w,IF(OR(d="",NOT(ISNUMBER(w))),"",'
         f'ROUND(AVERAGEIFS({_W("B")},{_W("A")},">"&d-7,{_W("A")},"<="&d,{_W("B")},">0"),1))))')
W_CHANGE = (f'=MAP({_W("A")},{_W("C")},LAMBDA(d,a,IF(NOT(ISNUMBER(a)),"",'
            f'LET(p,IFERROR(VLOOKUP(d-7,A{W_FIRST}:C,3,FALSE),""),IF(ISNUMBER(p),ROUND(a-p,1),"")))))')


def weight_lookup(date_expr, column):
    """Formula fragment: a column of the Daily Weight row for a date ("" if none)."""
    return f"IFERROR(VLOOKUP({date_expr},'Daily Weight'!$A${W_FIRST}:$D,{column},FALSE),\"\")"


def weight_requests():
    S = WEIGHT_SHEET_ID
    head = [cell(h, bold=True, bg=HEADER_BG, fg=WHITE, wrap=True, align="CENTER")
            for h in ("Date", "Weight (lb)", "7-day average", "Avg vs a week ago")]
    rows = [[cell("Daily weight", bold=True, size=13)],
            [cell("Weigh in each morning: after the bathroom, before food or water. Today's row is highlighted.",
                  fg=MUTED, italic=True)],
            head, [cell(W_DATES), cell(), cell(W_AVG), cell(W_CHANGE)]]
    signed = {"type": "NUMBER", "pattern": "+0.0;-0.0;0.0"}
    chart = {"addChart": {"chart": {
        "spec": {"title": "Body weight – daily weigh-ins and 7-day average",
                 "basicChart": {
                     "chartType": "LINE", "legendPosition": "BOTTOM_LEGEND", "headerCount": 1,
                     "interpolateNulls": True,
                     "axis": [{"position": "BOTTOM_AXIS", "title": "Date"},
                              {"position": "LEFT_AXIS", "title": "lb", "viewWindowOptions": {"viewWindowMode": "PRETTY"}}],
                     "domains": [{"domain": {"sourceRange": {"sources": [grid(S, 3, 1, W_LAST, 1)]}}}],
                     "series": [
                         {"series": {"sourceRange": {"sources": [grid(S, 3, 2, W_LAST, 2)]}},
                          "targetAxis": "LEFT_AXIS", "color": {"red": 0.58, "green": 0.64, "blue": 0.72},
                          "lineStyle": {"width": 1}, "pointStyle": {"shape": "CIRCLE", "size": 4}},
                         {"series": {"sourceRange": {"sources": [grid(S, 3, 3, W_LAST, 3)]}},
                          "targetAxis": "LEFT_AXIS", "color": {"red": 0.145, "green": 0.388, "blue": 0.922},
                          "lineStyle": {"width": 3}}]}},
        "position": {"overlayPosition": {"anchorCell": {"sheetId": S, "rowIndex": 0, "columnIndex": 5},
                                         "widthPixels": 640, "heightPixels": 360}}}}}
    today = {"addConditionalFormatRule": {"index": 0, "rule": {
        "ranges": [grid(S, W_FIRST, 1, W_LAST, 4)],
        "booleanRule": {"condition": {"type": "CUSTOM_FORMULA", "values": [{"userEnteredValue": f"=$A{W_FIRST}=TODAY()"}]},
                        "format": {"textFormat": {"bold": True}, "backgroundColor": DAY_BG}}}}}
    valid = {"setDataValidation": {"range": grid(S, W_FIRST, 2, W_LAST, 2), "rule": {
        "condition": {"type": "NUMBER_BETWEEN", "values": [{"userEnteredValue": "50"}, {"userEnteredValue": "700"}]},
        "inputMessage": "Your weight this morning (lb). Goes into the workout email.", "strict": True}}}
    return [write(S, 1, rows), paint(S, W_FIRST, W_LAST, 1, 1, fmt=WDATE),
            paint(S, W_FIRST, W_LAST, 2, 2, bg=EDIT_BG, fmt=NUM1, align="CENTER"),
            paint(S, W_FIRST, W_LAST, 3, 3, fmt=NUM1, align="CENTER"),
            paint(S, W_FIRST, W_LAST, 4, 4, fmt=signed, align="CENTER"),
            valid, today, chart, *widths(S, [125, 95, 95, 110]),
            {"addProtectedRange": {"protectedRange": {
                "range": {"sheetId": S}, "description": "Only the yellow weight column is yours to edit",
                "warningOnly": True, "unprotectedRanges": [grid(S, W_FIRST, 2, W_LAST, 2)]}}}]


def add_weight_sheet(index):
    return {"addSheet": {"properties": {
        "sheetId": WEIGHT_SHEET_ID, "title": "Daily Weight", "index": index,
        "gridProperties": {"rowCount": W_LAST + 5, "columnCount": 16, "frozenRowCount": 3},
        "tabColorStyle": {"rgbColor": {"red": 0.145, "green": 0.388, "blue": 0.922}}}}}
