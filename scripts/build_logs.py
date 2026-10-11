"""Body Log (weekly InBody + daily targets), Monthly Check-in and Nutrition tabs."""
from build_sheet import DATE, EDIT_BG, HEADER_BG, MUTED, NUM, WHITE, cell, grid, widths, write


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
    return [props(BODY_SHEET_ID, "Body Log", start_index, FIRST + LOG_ROWS + 5, 5, 0, green),
            props(MONTHLY_SHEET_ID, "Monthly Check-in", start_index + 1, 70, 5, 3, green),
            props(NUTRITION_SHEET_ID, "Nutrition", start_index + 2, 5 + LOG_ROWS * 3 + 5, 6, 4, green)]


def log_requests():
    return body_requests() + monthly_requests() + nutrition_requests()
