"""End-of-block recalculation: reads the block's data and writes the next block's changes.

Runs in week 6 of each block (see .claude/skills/new-block/SKILL.md). Claude fetches the sheet
ranges into one JSON file; this script does all of the deciding, so the rules are testable.

Input JSON (raw get_values output, formatted values):
  config        Config!B2:B20 (column)
  tabs          {"Wk 04 · Nov 1": rows of A4:W45, ...}   every weekly tab of the block, plus older ones for history
  body_log      'Body Log'!A16:T215
  body_targets  'Body Log'!B2:B13 (column)
  daily_weight  'Daily Weight'!A4:C                       (row i = WEIGHT_START + i days)
  nutrition     Nutrition!A5:E

Usage:
  python scripts/recalc.py input.json            print the review + proposed changes (JSON)
  python scripts/recalc.py input.json --apply    also write them into program/adjustments.yaml

The plain-words rules (also printed in the review):
  1. Strength: every AMRAP set estimates a max = weight x (1 + reps / 30). Heavy lifts that carry
     into the next block start at the higher of last week's suggestion and 85% of the best estimate
     (rounded down to 5 lb). Accessories that carry over start at their last suggestion.
  2. Left vs right: if one arm (or leg) has more than 3% less lean mass than the other, or its
     % of ideal is 5+ points lower, one accessory per day for that pair switches to a one-arm /
     one-leg version. Start each set with the weaker side and match its reps on the stronger side.
  3. Body part vs body part: arms, trunk and legs are compared by % of ideal (and by growth since
     the start of the block when both scans have body-part readings). A part 5+ points below the
     average of the other two (or growing 1+ point slower) is lagging: on each day that trains it,
     one of its 3-set accessories gets a 4th set and the rest between rounds drops to 30 s so the
     day still fits 30 minutes. The best-developed part gives up its 4th set on 1B slots.
  4. Goal and food: extra sets are only added when you averaged 4+ sessions a week and ate enough
     (protein >= 90% of target and calories >= maintenance, when 10+ days are logged). Otherwise
     the review says food or attendance is the limit, not training. Fat rising faster than lean
     mass -> recommend trimming the surplus by 150 kcal (recommendation only).
  5. Exercise choice: blocks keep rotating D -> E -> F; the belt squat stays the heavy lift on both
     leg days.
"""
import datetime
import json
import math
import pathlib
import sys

import yaml

import program
import timing
from build_logs import SEGMENTAL, WEIGHT_START
from layout import COLS, PROGRAM_START

GOAL_BF = 9.0           # 10-year goal: 9% body fat
DEFAULT_GOAL_WEIGHT = 235.0
IMBALANCE_PCT = 3.0     # lean mass, % of the larger side
IMBALANCE_IDEAL = 5.0   # % of ideal points
LAG_IDEAL = 5.0         # % of ideal points below the other parts' average
LAG_GROWTH = 1.0        # percentage points of lean growth below the other parts' average
MIN_SESSIONS = 4.0      # per week, to earn extra volume
SHORT_REST = 30         # seconds between rounds on a day that gets an extra set
GROUP = {"biceps": "arms", "triceps": "arms", "chest": "trunk", "back": "trunk", "shoulders": "trunk",
         "rear_delts": "trunk", "traps": "trunk", "core": "trunk",
         "quads": "legs", "hamstrings": "legs", "glutes": "legs", "calves": "legs"}
PAIRS = {"arms": ("ra", "la", "Right arm", "Left arm"), "legs": ("rl", "ll", "Right leg", "Left leg")}
# Bilateral exercise -> one-arm / one-leg version already in the library (has its own video).
UNILATERAL = {
    "Machine Preacher Curl": "Incline Dumbbell Curl",
    "Rope Cable Hammer Curl": "Dumbbell Hammer Curl",
    "Overhead Rope Triceps Extension": "Seated Dumbbell Overhead Triceps Extension",
    "Cable Triceps Pushdown": "Cross-Body Cable Triceps Extension",
    "Smith Machine JM Press": "Dumbbell Skull Crusher",
    "Leg Extension": "Single-Leg Leg Extension",
    "Paused Leg Extension": "Single-Leg Leg Extension",
    "Leg Press (High & Wide Feet)": "Single-Leg Leg Press",
    "Hack Squat Machine": "Dumbbell Bulgarian Split Squat",
    "Seated Leg Curl": "Standing Single-Leg Curl Machine",
    "Lying Leg Curl": "Standing Single-Leg Curl Machine",
    "Kneeling Leg Curl Machine": "Standing Single-Leg Curl Machine",
    "Standing Calf Raise Machine": "Single-Leg Dumbbell Calf Raise",
    "Seated Calf Raise": "Single-Leg Dumbbell Calf Raise",
    "Leg Press Calf Raise": "Single-Leg Dumbbell Calf Raise",
    "Smith Machine Calf Raise": "Single-Leg Dumbbell Calf Raise",
}
C = {n: i for i, n in enumerate(COLS)}


# ------------------------------------------------------------------ parsing
def num(v):
    try:
        x = float(str(v).replace(",", "").strip())
    except ValueError:
        return None
    return None if math.isnan(x) else x


def date(v):
    for f in ("%a %b %d, %Y", "%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.datetime.strptime(str(v).strip(), f).date()
        except ValueError:
            pass
    return None


def cellv(row, name):
    i = C[name]
    return row[i] if i < len(row) else ""


def parse_tabs(tabs):
    """(sessions {week: completed}, lifts [dict]) from weekly tabs' A4:W rows."""
    sessions, lifts = {}, []
    for title, rows in tabs.items():
        week = int(title.split()[1])
        sessions.setdefault(week, 0)
        for row in rows:
            if cellv(row, "daykey") and str(cellv(row, "complete")).upper() == "TRUE":
                sessions[week] += 1
            key, name = cellv(row, "key"), cellv(row, "name")
            if not key or not name:
                continue
            used = num(cellv(row, "lifted")) or num(cellv(row, "suggested"))
            lifts.append({"week": week, "key": key, "name": name, "type": cellv(row, "type"),
                          "used": used, "amrap": num(cellv(row, "amrap")), "next": num(cellv(row, "next"))})
    return sessions, lifts


def parse_scans(rows):
    keys = ["date", "weight", "bf", "smm", "lbm", "vfl", "time"] + [k for k, _, _ in SEGMENTAL]
    scans = []
    for row in rows:
        d = date(row[0]) if row else None
        if not d:
            continue
        s = {"date": d}
        for k, v in zip(keys[1:], row[1:]):
            s[k] = num(v)
        scans.append(s)
    return sorted(scans, key=lambda s: s["date"])


def has_segments(scan):
    return scan is not None and all(scan.get(f"{k}_pct") is not None for k in ("ra", "la", "tr", "rl", "ll"))


# ------------------------------------------------------------------ rules
def e1rm(weight, reps):
    return weight * (1 + reps / 30)


def floor5(x):
    return math.floor(x / 5) * 5


def strength(lifts):
    """Best estimated max per heavy exercise, and the latest 'next week' weight per exercise."""
    best, last = {}, {}
    for lift in sorted(lifts, key=lambda x: x["week"]):
        if lift["type"] == "Heavy" and lift["used"] and lift["amrap"]:
            best[lift["name"]] = max(best.get(lift["name"], 0), e1rm(lift["used"], lift["amrap"]))
        if lift["next"]:
            last[lift["name"]] = lift["next"]
    return best, last


def start_weights(next_days, best, last):
    out = {}
    for day, rows in next_days.items():
        for order, row in enumerate(rows, 1):
            name = row[0]
            w = last.get(name)
            if row[1] == "Heavy" and name in best:
                w = max(w or 0, floor5(0.85 * best[name]))
            if w:
                out[f"{day}|{order}"] = round(w, 1)
    return out


def parts(scan):
    """% of ideal and lean lb per part (arms and legs averaged)."""
    return {"arms": ((scan["ra_pct"] + scan["la_pct"]) / 2, scan["ra_lb"] + scan["la_lb"]),
            "trunk": (scan["tr_pct"], scan["tr_lb"]),
            "legs": ((scan["rl_pct"] + scan["ll_pct"]) / 2, scan["rl_lb"] + scan["ll_lb"])}


def lagging(latest, baseline):
    """(lagging parts, leading part, notes)."""
    now = parts(latest)
    notes, lag = [], set()
    for p, (pct, _) in now.items():
        others = [v[0] for q, v in now.items() if q != p]
        gap = sum(others) / 2 - pct
        if gap >= LAG_IDEAL:
            lag.add(p)
            notes.append(f"{p.title()} is at {pct:.1f}% of ideal, {gap:.1f} points below the other two.")
    if has_segments(baseline) and (latest["date"] - baseline["date"]).days >= 21:
        before = parts(baseline)
        growth = {p: (now[p][1] / before[p][1] - 1) * 100 for p in now}
        for p, g in growth.items():
            others = [v for q, v in growth.items() if q != p]
            if sum(others) / 2 - g >= LAG_GROWTH:
                lag.add(p)
                notes.append(f"{p.title()} lean mass grew {g:+.1f}% this block vs {sum(others) / 2:+.1f}% for the others.")
    leading = max(now, key=lambda p: now[p][0])
    if leading in lag:
        leading = None
    return lag, leading, notes


def imbalances(latest):
    out, notes = [], []
    for pair, (r, l, rn, ln) in PAIRS.items():
        a, b = latest[f"{r}_lb"], latest[f"{l}_lb"]
        gap_lb = abs(a - b) / max(a, b) * 100
        gap_ideal = abs(latest[f"{r}_pct"] - latest[f"{l}_pct"])
        weaker = rn if a < b else ln
        if gap_lb > IMBALANCE_PCT or gap_ideal >= IMBALANCE_IDEAL:
            out.append(pair)
            notes.append(f"{weaker} is {gap_lb:.1f}% lighter in lean mass ({gap_ideal:.1f} points of ideal): "
                         f"one-{pair[:-1]} work next block, weaker side first.")
        else:
            notes.append(f"{rn} vs {ln}: {gap_lb:.1f}% apart in lean mass — balanced (limit {IMBALANCE_PCT:g}%).")
    return out, notes


def plan_next_block(lib, next_block, lag, leading, uneven, add_volume):
    """swap / sets / rest changes for the next block that keep every day inside the cap."""
    t = lib["timing"]
    pool = program.exercises_by_name(lib)
    days = {d: [list(r) for r in rows] for d, rows in lib["blocks"][next_block].items()}
    swap, sets, rest, notes = {}, {}, {}, []
    for day, rows in days.items():
        names = {r[0] for r in rows}
        for pair in uneven:
            for order, row in enumerate(rows, 1):
                target = UNILATERAL.get(row[0])
                if order > 1 and target and GROUP[row[7]] == pair and target not in names:
                    swap[f"{day}|{order}"] = target
                    new = pool[target]
                    rows[order - 1] = [new[0], *row[1:5], *new[5:]]
                    notes.append(f"{day}: {row[0]} → {target} (one-{pair[:-1]}).")
                    break
        if not add_volume:
            continue
        for part in sorted(lag):
            cands = [o for o, r in enumerate(rows, 1)
                     if o >= 3 and GROUP[r[7]] == part and r[2] == 3]
            cands.sort(key=lambda o: rows[o - 1][1] != "Compound-acc")
            if not cands:
                continue
            o = cands[0]
            trial = [list(r) for r in rows]
            trial[o - 1][2] = 4
            short = [t["rest_after_round"][0], SHORT_REST, SHORT_REST]
            if timing.day_minutes(trial, t, short)[1] <= t["cap_min"]:
                rows[o - 1][2] = 4
                sets[f"{day}|{o}"] = 4
                rest[day] = short
                notes.append(f"{day}: {rows[o - 1][0]} 3 → 4 sets for {part}; rest between rounds 45 → 30 s.")
                break
        if lag and leading and GROUP[rows[1][7]] == leading and rows[1][2] == 4:
            rows[1][2] = 3
            sets[f"{day}|2"] = 3
            notes.append(f"{day}: {rows[1][0]} 4 → 3 sets ({leading} is your best-developed part).")
    return days, {"swap": swap, "sets": sets, "rest": rest}, notes


# ------------------------------------------------------------------ the run
def block_info(config):
    cur, length, start = int(num(config[1])), int(num(config[4])), int(num(config[18]))
    idx = (cur - start) // length
    first = start + idx * length
    return {"week": cur, "week_in_block": cur - first + 1, "length": length,
            "block": "DEF"[idx % 3], "next_block": "DEF"[(idx + 1) % 3], "weeks": list(range(first, first + length)),
            "start_date": datetime.date(*PROGRAM_START) + datetime.timedelta(days=(first - 1) * 7)}


def avg_weight(rows, day):
    """7-day average on the Daily Weight row for `day` (or the nearest earlier one)."""
    i = (day - datetime.date(*WEIGHT_START)).days
    for j in range(min(i, len(rows) - 1), -1, -1):
        v = num(rows[j][2]) if len(rows[j]) > 2 else None
        if v:
            return v
    return None


def run(data, today=None):
    today = today or datetime.date.today()
    lib = program.load()
    info = block_info(data["config"])
    sessions, lifts = parse_tabs(data["tabs"])
    scans = parse_scans(data["body_log"])
    targets = [num(v) for v in data["body_targets"]]
    # Body Log B2..B13: [date, weight, bf, smm, lbm, goal wt, goal date, activity, maint, surplus, kcal, protein]
    maintenance, kcal_target, protein_target = targets[8], targets[10], targets[11]
    goal_weight = targets[5] or DEFAULT_GOAL_WEIGHT
    goal_date = date(data["body_targets"][6]) if len(data["body_targets"]) > 6 else None
    review, notes = [], {}

    # attendance
    done = [sessions.get(w, 0) for w in info["weeks"] if w <= info["week"]]
    per_week = sum(done) / max(1, len(done))
    review.append(["Attendance", f"{sum(done)} sessions in {len(done)} weeks ({per_week:.1f} a week).",
                   "Extra sets need 4+ a week." if per_week < MIN_SESSIONS else "Enough to add volume."])

    # food
    start, food_days = info["start_date"], {}
    for row in data["nutrition"]:
        d = date(row[0]) if row else None
        if d and start <= d <= today:
            day = food_days.setdefault(d, [0, 0])
            day[0] += num(row[3] if len(row) > 3 else "") or 0
            day[1] += num(row[4] if len(row) > 4 else "") or 0
    food_ok = True
    if len(food_days) >= 10:
        kcal = sum(v[0] for v in food_days.values()) / len(food_days)
        prot = sum(v[1] for v in food_days.values()) / len(food_days)
        food_ok = prot >= 0.9 * (protein_target or 0) and kcal >= (maintenance or 0)
        review.append(["Food", f"{len(food_days)} days logged: {kcal:,.0f} kcal and {prot:.0f} g protein a day "
                       f"(targets {kcal_target or 0:,.0f} kcal / {protein_target or 0:.0f} g; maintenance {maintenance or 0:,.0f}).",
                       "On track." if food_ok else "Food is the limit right now, not training: no extra sets this block."])
    else:
        review.append(["Food", f"Only {len(food_days)} days logged this block.", "Not enough to judge; doesn't block extra sets."])

    # body + goal
    latest = scans[-1] if scans else None
    before = [s for s in scans if s["date"] <= start + datetime.timedelta(days=3)]
    baseline = before[-1] if before else (scans[0] if scans else None)
    if latest and baseline and latest is not baseline and latest.get("bfm") and baseline.get("bfm"):
        d_fat = latest["bfm"] - baseline["bfm"]
        d_lean = (latest["weight"] - latest["bfm"]) - (baseline["weight"] - baseline["bfm"])
        trim = d_fat > d_lean and d_fat > 1
        review.append(["Body", f"Since {baseline['date']:%b %d}: lean {d_lean:+.1f} lb, fat {d_fat:+.1f} lb, "
                       f"body fat {latest['bf']:.1f}% (goal {GOAL_BF:g}%).",
                       "Fat is outpacing lean: consider trimming the surplus by 150 kcal (Body Log B9/B11)." if trim
                       else "Gaining in the right proportion."])
    w_start, w_now = avg_weight(data["daily_weight"], start), avg_weight(data["daily_weight"], today)
    if w_now:
        line = f"7-day average {w_now:.1f} lb" + (f" ({w_now - w_start:+.1f} lb this block)" if w_start else "")
        pace = ""
        if goal_date and goal_date > today:
            need = (goal_weight - w_now) / ((goal_date - today).days / 7)
            pace = f"Need {need:+.2f} lb/week to reach {goal_weight:g} lb by {goal_date:%b %d, %Y}."
        review.append(["Goal", line + f"; goal {goal_weight:g} lb at {GOAL_BF:g}% body fat.", pace])

    # body parts
    lag, leading, uneven = set(), None, []
    if has_segments(latest):
        lag, leading, lag_notes = lagging(latest, baseline if has_segments(baseline) else None)
        uneven, side_notes = imbalances(latest)
        for n in side_notes:
            review.append(["Left vs right", n, ""])
        for n in lag_notes or ["No part lags the others by 5+ points of ideal."]:
            review.append(["Body parts", n, ""])
    else:
        review.append(["Body parts", "Latest scan has no body-part readings.", "No body-part changes."])

    add_volume = per_week >= MIN_SESSIONS and food_ok
    days, changes, plan_notes = plan_next_block(lib, info["next_block"], lag, leading, uneven, add_volume)
    if lag and not add_volume:
        review.append(["Volume", f"{', '.join(sorted(lag)).title()} lagging, but no extra sets this block.",
                       "Attendance or food first."])
    for pair in uneven:
        if not any(f"one-{pair[:-1]}" in n for n in plan_notes):
            review.append(["Next block", f"Block {info['next_block']}'s {pair} work is already one-{pair[:-1]} "
                           "or dumbbell: start each set with the weaker side.", ""])
    for n in plan_notes:
        review.append(["Next block", n, ""])

    # strength
    history = [l for l in lifts if l["week"] <= info["week"]]
    best, last = strength(history)
    for name, v in sorted(best.items()):
        review.append(["Strength", f"{name}: estimated max {v:.0f} lb.", ""])
    changes["start_lb"] = start_weights(days, best, last)
    changes["review_date"] = today.isoformat()
    return {"info": {**info, "start_date": info["start_date"].isoformat()}, "review": review,
            "changes": changes, "next_block": info["next_block"]}


def apply(result, path=program.ADJUSTMENTS):
    current = (yaml.safe_load(path.read_text()) if path.exists() else None) or {}
    current.setdefault("blocks", {})[result["next_block"]] = result["changes"]
    path.write_text("# Written by scripts/recalc.py at the end of each block. Don't edit by hand.\n"
                    + yaml.safe_dump(current, sort_keys=False, allow_unicode=True))


def main(argv):
    data = json.loads(pathlib.Path(argv[0]).read_text())
    result = run(data)
    if "--apply" in argv:
        if result["info"]["week_in_block"] != result["info"]["length"]:
            raise SystemExit(f"Week {result['info']['week']} is week {result['info']['week_in_block']} of the block; "
                             "the recalculation only applies in the last week.")
        apply(result)
    print(json.dumps(result, indent=2, default=str, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1:])
