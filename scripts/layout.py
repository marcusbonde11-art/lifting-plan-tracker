"""Shared layout constants for the weekly tab (used by the builder and tests)."""

PROGRAM_START = (2026, 10, 11)  # first Sunday of week 1
TIMEZONE = "America/New_York"
WIFE_EMAIL = "Maegirl333@gmail.com"
ATHLETE = "Marcus"

START_SHEET_ID = 1
CONFIG_SHEET_ID = 2
LIBRARY_SHEET_ID = 3
OUTBOX_SHEET_ID = 4
TEMPLATE_SHEET_ID = 9
# weekly tabs get sheetId 100000 + week number

# Column order of a weekly tab. A–N are visible, O onward are hidden helpers.
COLS = [
    "label", "exercise", "prescription", "rest", "suggested",   # A B C D E
    "lifted", "amrap", "hit", "next",                           # F G H I
    "kbstart", "kbstop", "kbmin", "complete", "sent",           # J K L M N
    "key", "m", "type", "rephigh", "inc", "video",              # O P Q R S T
    "daykey", "order", "name", "mail", "html", "ready", "ref",  # U V W X Y Z AA
    "kbt0", "kbt1",                                             # AB AC  KB start/stop timestamps
]

EXERCISES_PER_DAY = 6                             # three supersets: 1A 1B 2A 2B 3A 3B
DAY_SPAN = EXERCISES_PER_DAY + 1                  # header row + exercises
FIRST_ROW = 4                                     # first day-header row
DAY_ROWS = [FIRST_ROW + DAY_SPAN * d for d in range(6)]  # 4, 11, 18, 25, 32, 39
LAST_ROW = DAY_ROWS[-1] + EXERCISES_PER_DAY       # 45
SAT_ROW = LAST_ROW + 1                            # 46


def col(name):
    """Column letter for a named column."""
    i = COLS.index(name)
    s = ""
    i += 1
    while i:
        i, rem = divmod(i - 1, 26)
        s = chr(65 + rem) + s
    return s


def idx(name):
    """0-based column index for a named column."""
    return COLS.index(name)


def editable_ranges(sheet_id):
    """GridRanges (0-based, end-exclusive) of the only cells Marcus edits."""
    out = []

    def rng(r1, r2, c1, c2):
        return {"sheetId": sheet_id, "startRowIndex": r1 - 1, "endRowIndex": r2,
                "startColumnIndex": idx(c1), "endColumnIndex": idx(c2) + 1}

    for h in DAY_ROWS:
        out.append(rng(h + 1, h + EXERCISES_PER_DAY, "lifted", "lifted"))  # weight lifted, every exercise
        out.append(rng(h + 1, h + 1, "amrap", "amrap"))     # AMRAP, main lift only
        out.append(rng(h, h, "kbstart", "kbstop"))          # kettlebell start + stop
        out.append(rng(h, h, "complete", "complete"))       # Workout complete checkbox
    return out
