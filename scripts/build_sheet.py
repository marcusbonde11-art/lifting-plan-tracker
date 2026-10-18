"""Build the Google Sheets API payloads that create the lifting tracker.

Reads program/library.yaml and writes:
  build/create.json    body for POST spreadsheets            (empty tabs)
  build/requests.json  body for POST spreadsheets/{id}:batchUpdate (everything else)

The payload is kept small on purpose (it travels inside a Make.com module):
one day's block of the weekly template is written cell by cell, then copied to
the other five days with copyPaste, and the Library is pasted as TSV.

Usage:  python scripts/build_sheet.py
"""
import json
import pathlib

import yaml

from layout import (
    ATHLETE, COLS, CONFIG_SHEET_ID, DAY_ROWS, LIBRARY_SHEET_ID, OUTBOX_SHEET_ID,
    PROGRAM_START, SAT_ROW, START_SHEET_ID, TEMPLATE_SHEET_ID, TIMEZONE, WIFE_EMAIL,
    col, idx,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent
LIB = yaml.safe_load((ROOT / "program" / "library.yaml").read_text())


# ------------------------------------------------------------------ helpers
def rgb(hex_):
    hex_ = hex_.lstrip("#")
    return {k: round(int(hex_[i:i + 2], 16) / 255, 3) for k, i in zip(("red", "green", "blue"), (0, 2, 4))}


HEADER_BG, DAY_BG, EDIT_BG = rgb("#1F2937"), rgb("#DBEAFE"), rgb("#FFF2CC")
MUTED, WHITE, REST_BG = rgb("#6B7280"), rgb("#FFFFFF"), rgb("#F3F4F6")
NUM = {"type": "NUMBER", "pattern": "0.##"}
TIME = {"type": "TIME", "pattern": "h:mm am/pm"}
DATE = {"type": "DATE", "pattern": "ddd mmm d, yyyy"}


def cell(value=None, *, bold=False, bg=None, fg=None, fmt=None, align=None, wrap=False,
         italic=False, size=None, validation=None):
    c = {}
    if isinstance(value, bool):
        c["userEnteredValue"] = {"boolValue": value}
    elif isinstance(value, (int, float)):
        c["userEnteredValue"] = {"numberValue": value}
    elif isinstance(value, str) and value.startswith("="):
        c["userEnteredValue"] = {"formulaValue": value}
    elif value is not None:
        c["userEnteredValue"] = {"stringValue": value}
    f, tf = {}, {}
    if bold:
        tf["bold"] = True
    if italic:
        tf["italic"] = True
    if fg:
        tf["foregroundColor"] = fg
    if size:
        tf["fontSize"] = size
    if tf:
        f["textFormat"] = tf
    if bg:
        f["backgroundColor"] = bg
    if fmt:
        f["numberFormat"] = fmt
    if align:
        f["horizontalAlignment"] = align
    if wrap:
        f["wrapStrategy"] = "WRAP"
    if f:
        c["userEnteredFormat"] = f
    if validation:
        c["dataValidation"] = validation
    return c


def grid(sheet_id, r1, c1, r2=None, c2=None):
    """0-based, end-exclusive GridRange from 1-based inclusive rows/cols."""
    g = {"sheetId": sheet_id, "startRowIndex": r1 - 1, "startColumnIndex": c1 - 1}
    g["endRowIndex"] = (r2 or r1)
    g["endColumnIndex"] = (c2 or c1)
    return g


def write(sheet_id, r1, rows, c1=1):
    """updateCells request writing a list of rows (lists of cells) at r1/c1."""
    return {"updateCells": {
        "start": {"sheetId": sheet_id, "rowIndex": r1 - 1, "columnIndex": c1 - 1},
        "rows": [{"values": r} for r in rows],
        "fields": "userEnteredValue,userEnteredFormat,dataValidation"}}


def widths(sheet_id, px_by_col, hidden_from=None, total=None):
    reqs = [{"updateDimensionProperties": {
        "range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": i, "endIndex": i + 1},
        "properties": {"pixelSize": px}, "fields": "pixelSize"}} for i, px in enumerate(px_by_col)]
    if hidden_from is not None:
        reqs.append({"updateDimensionProperties": {
            "range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": hidden_from, "endIndex": total},
            "properties": {"hiddenByUser": True}, "fields": "hiddenByUser"}})
    return reqs


def lock(sheet_id, description):
    return {"addProtectedRange": {"protectedRange": {
        "range": {"sheetId": sheet_id}, "description": description, "warningOnly": True}}}


# ------------------------------------------------------------------ library
LIB_HEADERS = ["Key", "Block", "Day", "Order", "Exercise", "Region", "Type", "Sets", "Rep low",
               "Rep high", "Rest", "How-to video", "Increment (lb)", "Equipment"]


def library_rows():
    rest = {t: v["rest"] for t, v in LIB["types"].items()}
    out = []
    for block, days in LIB["blocks"].items():
        for day_key, _, _ in LIB["days"]:
            for order, (name, typ, sets, lo, hi, inc, equip, url) in enumerate(days[day_key], 1):
                region = "Legs" if day_key.startswith("L") else "Upper"
                out.append([f"{block}|{day_key}|{order}", block, day_key, order, name, region, typ,
                            sets, lo, hi, rest[typ], url, inc, equip])
    return out


def library_requests():
    tsv = "\n".join("\t".join(str(v) for v in r) for r in [LIB_HEADERS] + library_rows())
    return [
        {"pasteData": {"coordinate": {"sheetId": LIBRARY_SHEET_ID, "rowIndex": 0, "columnIndex": 0},
                       "data": tsv, "type": "PASTE_NORMAL", "delimiter": "\t"}},
        {"repeatCell": {"range": grid(LIBRARY_SHEET_ID, 1, 1, 1, len(LIB_HEADERS)),
                        "cell": cell(bold=True, bg=HEADER_BG, fg=WHITE),
                        "fields": "userEnteredFormat"}},
        *widths(LIBRARY_SHEET_ID, [100, 50, 45, 50, 290, 60, 105, 45, 60, 65, 70, 330, 95, 90]),
        lock(LIBRARY_SHEET_ID, "Library is locked – edit program/library.yaml and rebuild"),
    ]


# ------------------------------------------------------------------ config
KB = LIB["kettlebell"]
CONFIG = [  # (label, value, note, format) – rows 2..16
    ("Program start (first Sunday)", "=DATE(%d,%d,%d)" % PROGRAM_START, "Week 1 starts this Sunday.", DATE),
    ("Current week #", 0, "Set by the Saturday generator.", None),
    ("Current tab", "", "Set by the Saturday generator.", None),
    ("Previous tab", "", "Set by the Saturday generator.", None),
    ("Block length (weeks)", 6, "Exercises rotate to the next block after this many weeks.", None),
    ("Blocks in rotation", 3, "A → B → C → A …", None),
    ("Daily summary email to", WIFE_EMAIL, "Emailed each time a day is ticked complete.", None),
    ("(unused – see rows 17–19)", "", "Kettlebell videos are now per day type below.", None),
    ("Athlete name", ATHLETE, "Used in the email subject.", None),
    ("Template sheet ID", TEMPLATE_SHEET_ID, "Hidden tab the generator copies.", None),
    ("Next week #", "=B3+1", "", None),
    ("Next tab name", '="Wk "&TEXT(B12,"00")&" · "&TEXT(B2+(B12-1)*7,"mmm d")', "", None),
    ("Next sheet ID", "=100000+B12", "", None),
    ("Next week starts", "=B2+(B12-1)*7", "", DATE),
    ("Generate next week now?", "=OR(B3=0,B15-TODAY()<=1)",
     "TRUE from Saturday on (or before week 1). The generator does nothing while FALSE.", None),
    ("Kettlebell warm-up – Push days", KB["push"]["url"], KB["push"]["title"], None),   # row 17
    ("Kettlebell warm-up – Pull days", KB["pull"]["url"], KB["pull"]["title"], None),   # row 18
    ("Kettlebell warm-up – Leg days", KB["legs"]["url"], KB["legs"]["title"], None),    # row 19
]


def config_requests():
    rows = [[cell(h, bold=True, bg=HEADER_BG, fg=WHITE) for h in ("Setting", "Value", "Notes")]]
    rows += [[cell(l, bold=True), cell(v, fmt=f), cell(n, fg=MUTED, italic=True)] for l, v, n, f in CONFIG]
    return [write(CONFIG_SHEET_ID, 1, rows), *widths(CONFIG_SHEET_ID, [210, 330, 430]),
            lock(CONFIG_SHEET_ID, "Config is maintained by the automation")]


# ------------------------------------------------------------------ outbox
def tab_range(c, t="t"):
    return f'INDIRECT("\'"&{t}&"\'!{c}4:{c}40")'


OUTBOX = ('=LET(cur,Config!B4,prev,Config!B5,f,LAMBDA(t,IF(t="",{""},IFERROR(FILTER('
          f'{tab_range(col("mail"))}&"§§"&{tab_range(col("ref"))}&"§§"&{tab_range(col("html"))},'
          f'{tab_range(col("ready"))}=TRUE),{{""}}))),VSTACK(f(cur),f(prev)))')


def outbox_requests():
    # A1 spills one line per pending email: subject §§ cell to stamp §§ html. B1 is the recipient.
    return [write(OUTBOX_SHEET_ID, 1, [[cell(OUTBOX), cell("=Config!B8")]]),
            lock(OUTBOX_SHEET_ID, "Generated – read by Make")]


# ------------------------------------------------------------------ start here
START = [
    ("How this tracker works", True),
    ("• Each week gets its own tab (newest first), built automatically every Saturday at 7 am.", False),
    ("• Only the YELLOW cells are yours: Weight lifted, AMRAP reps (main lift's last set), "
     "▶ Start KB / ⏹ Stop KB (tick to time the kettlebell warm-up) and the Workout complete checkbox.", False),
    ("• Tap an exercise name for its how-to video. The 🔔 row opens the kettlebell warm-up video.", False),
    ("• Main lift: weight goes up next week when the AMRAP set hits 5+ reps.", False),
    ("• Accessories: weight goes up when you tick Workout complete with a weight logged.", False),
    ("• Upper body +2.5–5 lb, legs +5–10 lb. Missed target → same weight next week.", False),
    ("• Typing a different weight than suggested makes YOUR number the new baseline.", False),
    ("• Ticking Workout complete emails a summary of the day (checked every 15 min, 5–11 am).", False),
    ("• Exercises rotate every 6 weeks (Block A → B → C). Saturday is rest.", False),
    ("• Daily Weight: log your weight every morning. A new week of dates appears each Saturday; "
     "the chart shows daily weigh-ins and the 7-day average. Each workout email includes that day's weight.", False),
    ("• Body Log: add your weekly InBody scan (date, weight, body fat %, skeletal muscle mass, visceral fat, time), "
     "or paste a photo of the printout into Claude and it logs the row. "
     "Daily calorie + protein targets update from your latest lean body mass.", False),
    ("• Nutrition: one row per weighed food (date, food, grams, calories, protein). "
     "Yesterday's totals and surplus/deficit go into the next workout email.", False),
    ("• Monthly Check-in: waist measurement + a link to that month's progress photos.", False),
]


def start_requests():
    return [write(START_SHEET_ID, 1, [[cell(t, bold=b, size=14 if b else 11, wrap=True)] for t, b in START]),
            *widths(START_SHEET_ID, [900]), lock(START_SHEET_ID, "Instructions")]


# ------------------------------------------------------------------ weekly template
def lib(c, r):
    """Library column c for the exercise on row r (via the row's match index)."""
    return f'IFERROR(INDEX(Library!${c}:${c},{col("m")}{r}),"")'


def exercise_cells(r, h, order):
    k = lambda n: f"{col(n)}{r}"
    used = f'IF({k("lifted")}<>"",{k("lifted")},{k("suggested")})'
    c = {n: cell() for n in COLS}
    c["label"] = cell(f'=IF({k("name")}="","",IF({k("type")}="Heavy","MAIN","Acc "&({k("order")}-1)))',
                      fg=MUTED, align="CENTER")
    c["exercise"] = cell(f'=IF({k("name")}="","",HYPERLINK({k("video")},{k("name")}))', wrap=True)
    c["prescription"] = cell(f'=IF({k("name")}="","",{lib("H", r)}&" × "&{lib("I", r)}&"–"&{lib("J", r)}'
                             f'&IF({k("type")}="Heavy"," (last set AMRAP)",""))', align="CENTER", wrap=True)
    c["rest"] = cell("=" + lib("K", r), align="CENTER")
    c["suggested"] = cell(f'=IF(OR({k("key")}="",$Q$1=""),"",IFERROR(INDEX(INDIRECT("\'"&$Q$1&"\'!I4:I40"),'
                          f'MATCH({k("key")},INDIRECT("\'"&$Q$1&"\'!O4:O40"),0)),""))',
                          fmt=NUM, align="CENTER", bold=True)
    c["lifted"] = cell(bg=EDIT_BG, fmt=NUM, align="CENTER", validation={
        "condition": {"type": "NUMBER_BETWEEN", "values": [{"userEnteredValue": "0"}, {"userEnteredValue": "2000"}]},
        "inputMessage": "Weight you lifted (lb). Blank = suggested weight repeats.", "strict": True})
    c["amrap"] = (cell(bg=EDIT_BG, align="CENTER", validation={
        "condition": {"type": "NUMBER_BETWEEN", "values": [{"userEnteredValue": "0"}, {"userEnteredValue": "50"}]},
        "inputMessage": "Reps on your last (AMRAP) set.", "strict": True})
        if order == 1 else cell("—", fg=MUTED, align="CENTER"))
    c["hit"] = cell(f'=IF({k("name")}="","",IF({k("type")}="Heavy",IF({k("amrap")}="","",'
                    f'IF({k("amrap")}>={k("rephigh")},"✅ Yes","❌ No")),'
                    f'IF({col("complete")}{h}=TRUE,IF({k("lifted")}<>"","✅ Yes","❌ No"),"")))', align="CENTER")
    c["next"] = cell(f'=IF({k("name")}="","",IF(N({used})=0,"",IF(REGEXMATCH({k("hit")},"Yes"),'
                     f'{used}+{k("inc")},{used})))', fmt=NUM, align="CENTER", bold=True)
    # hidden helpers
    c["key"] = cell(f'=IF($R$1="","",$R$1&"|"&{col("daykey")}{h}&"|"&{k("order")})')
    c["m"] = cell(f'=IFERROR(MATCH({k("key")},Library!$A:$A,0),"")')
    c["type"] = cell("=" + lib("G", r))
    c["rephigh"] = cell("=" + lib("J", r))
    c["inc"] = cell("=" + lib("M", r))
    c["video"] = cell("=" + lib("L", r))
    c["order"] = cell(order)
    c["name"] = cell("=" + lib("E", r))
    td = "<td align='center' style='border-top:1px solid #e5e7eb'>"
    c["mail"] = cell(
        f'=IF({k("name")}="","","<tr><td style=\'border-top:1px solid #e5e7eb\'>"&SUBSTITUTE({k("name")},"&","&amp;")&"</td>'
        f'{td}"&{k("prescription")}&"</td>{td}"&IF(N({used})=0,"—",{used}&" lb")&"</td>'
        f'{td}"&IF({k("type")}="Heavy",IF({k("amrap")}="","—",{k("amrap")}&" reps"),"")&"</td>'
        f'{td}"&IF({k("hit")}="","—",{k("hit")})&"</td>'
        f'{td}"&IF({k("next")}="","—",{k("next")}&" lb"&IF(N({k("next")})>N({used})," ⬆",""))&"</td></tr>")')
    return [c[n] for n in COLS]


# Config rows 17/18/19 hold the push/pull/legs warm-up video (B) and its title (C).
KB_FORMULA = ('=LET(t,LEFT({u},2),r,IF(t="PU",18,IF(LEFT(t,1)="P",17,19)),'
              'HYPERLINK(INDEX(Config!$B:$B,r),"🔔 Kettlebell warm-up, 15 min: "&INDEX(Config!$C:$C,r)))')


def nutrition_html(date):
    """Email paragraph: yesterday's logged calories/protein vs maintenance and targets."""
    rng = lambda c: f"Nutrition!${c}$5:${c}"
    return (f'LET(d,{date}-1,n,COUNTIF({rng("A")},d),k,SUMIF({rng("A")},d,{rng("D")}),'
            f'p,SUMIF({rng("A")},d,{rng("E")}),m,\'Body Log\'!$B$10,tk,\'Body Log\'!$B$12,tp,\'Body Log\'!$B$13,'
            '"<p>🍽️ Nutrition yesterday ("&TEXT(d,"ddd mmm d")&"): "&IF(n=0,"no food logged",'
            '"<b>"&TEXT(k,"#,##0")&" kcal</b> · <b>"&ROUND(p)&" g protein</b>"'
            '&IF(ISNUMBER(m)," — "&IF(k>=m,"<b>surplus</b> of +"&TEXT(k-m,"#,##0"),'
            '"<b>deficit</b> of "&TEXT(m-k,"#,##0"))&" kcal vs maintenance ("&TEXT(m,"#,##0")&")","")'
            '&IF(ISNUMBER(tk),"<br>Daily targets: "&TEXT(tk,"#,##0")&" kcal · "&tp&" g protein",""))&"</p>")')


def header_cells(h, day_key, label):
    k = lambda n: f"{col(n)}{h}"
    first, last = h + 1, h + 5
    date = "($S$1+(ROW()-4)/6)"
    c = {n: cell(bg=DAY_BG) for n in COLS[:idx("sent") + 1]}
    c.update({n: cell() for n in COLS[idx("sent") + 1:]})
    c["label"] = cell(f'=IF($S$1="",UPPER({k("order")}),UPPER(TEXT({date},"ddd mmm d"))&" · "&UPPER({k("order")}))',
                      bold=True, bg=DAY_BG)
    c["exercise"] = cell(KB_FORMULA.format(u=k("daykey")), bg=DAY_BG, italic=True, wrap=True)
    # Body weight: shown from the Daily Weight tab (logged there, not here)
    from build_logs import weight_lookup  # late import: build_logs imports this module
    c["prescription"] = cell("⚖️ Body weight", bg=DAY_BG, align="RIGHT", italic=True)
    c["rest"] = cell(f'=IFERROR(1/(1/{weight_lookup(date, 2)}),"")', bg=DAY_BG, fmt=NUM, align="CENTER", bold=True)
    # KB timer: tick ▶ Start / ⏹ Stop; the hidden AB/AC cells stamp NOW() once and keep it
    # (self-referencing formulas, which need iterative calculation switched on).
    tick = {"condition": {"type": "BOOLEAN"}, "strict": True}
    c["kbstart"] = cell(False, bg=EDIT_BG, align="CENTER", validation=tick)
    c["kbstop"] = cell(False, bg=EDIT_BG, align="CENTER", validation=tick)
    for flag, ts in (("kbstart", "kbt0"), ("kbstop", "kbt1")):
        c[ts] = cell(f'=IF({k(flag)}=TRUE,IF(ISNUMBER({k(ts)}),{k(ts)},NOW()),"")')
    t0, t1 = k("kbt0"), k("kbt1")
    c["kbmin"] = cell(f'=IF(AND(ISNUMBER({t0}),ISNUMBER({t1})),ROUND(MAX(0,{t1}-{t0})*1440)&" min",'
                      f'IF(ISNUMBER({t0}),"⏱ "&TEXT({t0},"h:mm"),""))', bg=DAY_BG, align="CENTER", bold=True)
    c["complete"] = cell(False, bg=EDIT_BG, align="CENTER", validation={"condition": {"type": "BOOLEAN"}, "strict": True})
    c["sent"] = cell(bg=DAY_BG, fg=MUTED, size=8)
    c["daykey"] = cell(day_key)
    c["order"] = cell(label)
    c["mail"] = cell(f'=Config!$B$10&" finished "&{k("order")}&" – "&TEXT({date},"ddd mmm d")&" 💪"')
    kb = (f'IF(AND(ISNUMBER({t0}),ISNUMBER({t1})),"<b>"&ROUND(MAX(0,{t1}-{t0})*1440)&" min</b> ("'
          f'&TEXT({t0},"h:mm am/pm")&"–"&TEXT({t1},"h:mm am/pm")&")","not logged")')
    bw_html = (f'LET(w,{weight_lookup(date, 2)},a,{weight_lookup(date, 3)},c,{weight_lookup(date, 4)},'
               'IF(ISNUMBER(w),"<b>"&TEXT(w,"0.0")&" lb</b>"&IF(ISNUMBER(a)," · 7-day average "&TEXT(a,"0.0")&" lb"'
               '&IF(ISNUMBER(c)," ("&TEXT(c,"+0.0;-0.0;0.0")&" lb vs a week ago)",""),""),"not logged today"))')
    hits = f'COUNTIF({col("hit")}{first}:{col("hit")}{last},"✅*")'
    total = f'COUNTIF({col("name")}{first}:{col("name")}{last},"?*")'
    c["html"] = cell(
        f'="<div style=\'font-family:Arial,Helvetica,sans-serif;color:#1f2937;max-width:680px\'>'
        f'<h2 style=\'margin:0 0 4px\'>"&{k("mail")}&"</h2>'
        f'<p style=\'margin:0 0 14px;color:#6b7280\'>Week "&$P$1&" · Block "&$R$1&" (week "&$T$1&" of "&Config!$B$6&")</p>'
        f'<p>🔔 Kettlebell warm-up: "&{kb}&"</p>'
        f'<p>⚖️ Body weight: "&{bw_html}&"</p>'
        f'"&{nutrition_html(date)}&"'
        f'<p><b>"&{hits}&" of "&{total}&"</b> exercises hit their rep targets.</p>'
        f'<table cellpadding=\'6\' style=\'border-collapse:collapse;font-size:14px\'>'
        f'<tr style=\'background:#f3f4f6\'><th align=\'left\'>Exercise</th><th>Sets × reps</th><th>Weight</th>'
        f'<th>AMRAP</th><th>Target hit?</th><th>Next week</th></tr>"'
        f'&TEXTJOIN("",TRUE,{col("mail")}{first}:{col("mail")}{last})&"</table>'
        f'<p style=\'color:#9ca3af;font-size:12px\'>⬆ = weight goes up next week. Sent automatically by the lifting tracker.</p></div>"')
    c["ready"] = cell(f'=AND({k("complete")}=TRUE,{k("sent")}="",$O$1<>"")')
    c["ref"] = cell(f'="\'"&$O$1&"\'!{col("sent")}"&ROW()')
    return [c[n] for n in COLS]


HEADS = {"label": "Day / #", "exercise": "Exercise (tap for video)", "prescription": "Sets × reps",
         "rest": "Rest", "suggested": "Suggested lb", "lifted": "Weight lifted", "amrap": "AMRAP reps",
         "hit": "Target hit?", "next": "Next week lb", "kbstart": "▶ Start KB", "kbstop": "⏹ Stop KB",
         "kbmin": "KB min", "complete": "Workout complete", "sent": "Email sent"}
WIDTHS = [130, 230, 120, 70, 85, 85, 70, 85, 85, 70, 70, 75, 85, 115]


def template_requests():
    T = TEMPLATE_SHEET_ID
    title = cell('=IF(P1="","Template – do not edit","Week "&P1&" · Block "&R1&" (week "&T1&" of "&Config!$B$6&") · "'
                 '&TEXT(S1,"ddd mmm d")&" – "&TEXT(S1+6,"ddd mmm d"))', bold=True, size=14)
    # Row 1: O1 tab name, P1 week #, Q1 previous tab (all written by Make), R1 block, S1 start date, T1 week-in-block
    meta = [cell('=IF(P1="","",MID("ABC",MOD(INT((P1-1)/Config!$B$6),Config!$B$7)+1,1))'),
            cell('=IF(P1="","",Config!$B$2+(P1-1)*7)', fmt={"type": "DATE", "pattern": "yyyy-mm-dd"}),
            cell('=IF(P1="","",MOD(P1-1,Config!$B$6)+1)')]
    day_key, _, label = LIB["days"][0]
    h = DAY_ROWS[0]
    block = [header_cells(h, day_key, label)] + [exercise_cells(h + o, h, o) for o in range(1, 6)]
    reqs = [
        write(T, 1, [[title]]),
        write(T, 1, [meta], c1=idx("rephigh") + 1),
        write(T, 2, [[cell("✏️ Fill in only the yellow cells. Tap an exercise for its how-to video.", fg=MUTED, italic=True)]]),
        write(T, 3, [[cell(HEADS[n], bold=True, bg=HEADER_BG, fg=WHITE, align="CENTER", wrap=True) for n in HEADS]]),
        write(T, h, block),
    ]
    # copy day 1's block to days 2–6 (relative references shift by 6 rows each time)
    for d in range(1, 6):
        reqs.append({"copyPaste": {"source": grid(T, h, 1, h + 5, len(COLS)),
                                   "destination": grid(T, DAY_ROWS[d], 1, DAY_ROWS[d] + 5, len(COLS)),
                                   "pasteType": "PASTE_NORMAL"}})
    for d in range(1, 6):
        dk, _, lbl = LIB["days"][d]
        reqs.append(write(T, DAY_ROWS[d], [[cell(dk), cell(lbl)]], c1=idx("daykey") + 1))
    sat = [cell('=IF($S$1="","SATURDAY · REST",UPPER(TEXT($S$1+6,"ddd mmm d"))&" · REST DAY")', bold=True, bg=REST_BG),
           cell("Rest day. Next week's tab appears at 7 am today. Still log your weight on the Daily Weight tab.", italic=True, fg=MUTED, bg=REST_BG)]
    sat += [cell(bg=REST_BG) for _ in range(idx("sent") - 1)]
    reqs.append(write(T, SAT_ROW, [sat]))
    reqs += widths(T, WIDTHS, hidden_from=len(WIDTHS), total=len(COLS))
    return reqs


# ------------------------------------------------------------------ assemble
def create_body():
    def props(sid, title, index, hidden=False, cols=26, rows=100, frozen=0, frozen_cols=0, color=None):
        p = {"sheetId": sid, "title": title, "index": index, "hidden": hidden,
             "gridProperties": {"rowCount": rows, "columnCount": cols, "frozenRowCount": frozen,
                                "frozenColumnCount": frozen_cols}}
        if color:
            p["tabColorStyle"] = {"rgbColor": rgb(color)}
        return {"properties": p}

    # Iterative calculation lets the KB timer formulas keep their first NOW() stamp.
    return {"properties": {"title": "Lifting Plan Tracker", "timeZone": TIMEZONE, "locale": "en_US",
                           "iterativeCalculationSettings": {"maxIterations": 1, "convergenceThreshold": 0.05}},
            "sheets": [props(START_SHEET_ID, "Start Here", 0, cols=1, rows=20, color="#F59E0B"),
                       props(CONFIG_SHEET_ID, "Config", 1, cols=3, rows=20, frozen=1, color="#6B7280"),
                       props(LIBRARY_SHEET_ID, "Library", 2, cols=14, rows=len(library_rows()) + 5, frozen=1,
                             color="#6B7280"),
                       props(OUTBOX_SHEET_ID, "Outbox", 3, hidden=True, cols=2, rows=30),
                       props(TEMPLATE_SHEET_ID, "_Template", 4, hidden=True, cols=len(COLS), rows=SAT_ROW,
                             frozen=3, frozen_cols=0, color="#2563EB")]}


def batch_body():
    import build_logs  # imported late: build_logs reuses helpers from this module
    return {"requests": start_requests() + config_requests() + library_requests()
            + outbox_requests() + template_requests()
            + build_logs.add_sheets(5) + build_logs.log_requests()}


def main():
    out = ROOT / "build"
    out.mkdir(exist_ok=True)
    for name, body in (("create.json", create_body()), ("requests.json", batch_body())):
        text = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
        (out / name).write_text(text)
        print(f"wrote build/{name} ({len(text.encode()) // 1024} KB)")


if __name__ == "__main__":
    main()
