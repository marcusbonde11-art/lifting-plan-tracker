# lifting-plan-tracker

A Google Sheets lifting tracker for a twice-weekly Push / Pull / Legs split built around
**45-minute sessions** (15 min kettlebell + 30 min of supersets), with automatic progressive
overload, a 6-week recalculation and two Make.com automations:
- **Saturday:** builds next week's tab.
- **When a day is ticked complete:** emails a summary of that workout.

```
 program/library.yaml ──► scripts/build_sheet.py ──► Make "Lifting – Setup" ──► Google Sheet
                                                                                 │
 Saturday 7 am ET  Make "Weekly Tab Generator"  ── copies _Template → "Wk NN · Mon d" ┤
 every 15 min 5–11am Make "Workout Complete Email" ── Outbox → Gmail → stamps "Email sent" ┘
```

## The week

| Sun | Mon | Tue | Wed | Thu | Fri | Sat |
|---|---|---|---|---|---|---|
| Push 1 | Pull 1 | Legs 1 | Push 2 | Pull 2 | Legs 2 | Rest |

Every session is 45 minutes:
1. **Kettlebell warm-up, ~15 min.** A beginner-friendly, male-led follow-along matched to the day
   (linked on each day's 🔔 row; stored in `Config!B17:C19`):
   - Push: Samuel Jordan, *Chest & Triceps with One Kettlebell* (15 min)
   - Pull: DanielPT Fitness, *15 min Pull Upper Body Kettlebell* (slow-paced)
   - Legs: DanielPT Fitness, *15 min Kettlebell Leg & Glute* (all standing)
2. **30 minutes of lifting: three supersets.** Do A, walk straight to B, rest, repeat.

   | Superset | What | Rounds | Minutes |
   |---|---|---|---|
   | 1 | 1A heavy lift (4 × 3–5, last set AMRAP) + 1B partner (4 × 8–12) | 2 ramp-up sets, then 4 × (30 s + 15 s walk + 45 s + 90 s rest) | 14 |
   | 2 | 2A + 2B accessories (3 × 8–12) | 3 × (45 s + 15 s + 45 s + 45 s rest) | 7.5 |
   | 3 | 3A + 3B accessories (3 × 8–12) | same | 7.5 |
   | | walking between supersets | | 1 |
   | | **Total** | | **30** |

   The heavy lift gets ~2.5 min between its own sets (the 1B set fills it). Pairs are chosen so the
   two exercises don't tire the same muscle. Core work sits in the superset slots (1B on pull
   days, 3B on leg days); biceps sit in 1B on push days and 3B on pull days. The **belt squat** is
   the heavy lift on both leg days in every block. `scripts/timing.py` does this math, the tests
   keep every day at or under 30 minutes, and each day's 🔔 row shows it.

**Equipment rules:**
- Upper body: dumbbells, machines and cables only. The Smith machine is the one barbell exception.
- Legs: barbell allowed, including squats.
- No deadlift variants anywhere.

**Rotation:** exercises stay fixed for 6-week blocks, then rotate (Block D → E → F → D; the
45-minute plan started as block D in week 4, Sun Nov 1 2026, `Config!B20`). Blocks A–C (weeks 1–3)
were the old 5-exercise plan; their tabs are untouched.

**Every 6 weeks the plan recalculates** (scheduled Thursday check, `.claude/skills/new-block/`,
`scripts/recalc.py`), using the InBody scans including body parts, the 7-day weight, the food log
and the logged lifts. Changes for the next block go to `program/adjustments.yaml`; the plain-words
reasons go to the sheet's **Block Review** tab:
1. **Strength:** each AMRAP set estimates a max, weight × (1 + reps ÷ 30). Heavy lifts that carry
   over start at the higher of last week's suggestion and 85% of that.
2. **Left vs right:** an arm or leg 3%+ lighter in lean mass (or 5+ points lower % of ideal) gets
   one-arm/one-leg work, weaker side first.
3. **Body part vs body part:** a part 5+ points of ideal below the other two (or growing 1+ point
   slower) gets a 4th set on one accessory per day; rest between rounds drops to 30 s so the day
   still fits 30 minutes. The best-developed part gives up its 4th set on 1B.
4. **Goal and food:** extra sets only with 4+ sessions a week and enough food (protein ≥ 90% of
   target, calories ≥ maintenance). Fat rising faster than lean → suggest −150 kcal.

**Videos:** every exercise links a short (< 4 min) how-to video.

## What you edit (yellow cells only)

| Cell | Where | Notes |
|---|---|---|
| Weight lifted | every exercise row | Leave blank if you used the suggested weight. A different number becomes your new baseline. |
| AMRAP reps | heavy-lift row (1A) | Reps on the final set. |
| ▶ Start KB / ⏹ Stop KB | day header row | Tick boxes. Tick Start when the warm-up begins and Stop when it ends; the time is stamped automatically (hidden columns AB/AC, self-referencing `NOW()` with iterative calculation on). KB min shows ⏱ start time while running, then the minutes. Untick to reset. Times and duration go in the email. |
| Workout complete ☐ | day header row | Ticking it queues the summary email. |

Other tabs (yellow cells are yours):

| Tab | What you enter | What it calculates |
|---|---|---|
| Daily Weight | Your weight each morning. Dates start Mon Oct 12 and run to the end of the current week; the next week's dates appear when the Saturday generator runs. | 7-day average, change vs a week ago, and a line chart (daily weigh-ins as dots, 7-day average as a bold line). That day's weight, average and change go into each workout email; the weekly tab's ⚖️ cell shows it read-only. |
| Body Log | Weekly InBody scan: date, weight, body fat %, SMM, visceral fat level, test time (A:G), plus body-part readings (H:T): lean lb for right arm, left arm, trunk, right leg, left leg; the same five as % of ideal; body fat mass; ECW/TBW; BMR. Or paste a photo of the printout into Claude and it logs the row (see below). Goal weight and goal date (B7:B8). | Lean body mass, then the daily targets below. |
| Monthly Check-in | Date, waist, link to progress photos, notes. | Waist change vs the previous month. |
| Nutrition | One row per weighed food: date, food, grams, calories, protein. You can also tell Claude in chat what you ate and it will log it ("Logged by" = Claude). | Today's totals vs targets. |

**Logging an InBody scan from a photo:** paste a photo of the printout into a Claude Code chat on this repo.
Claude follows `.claude/skills/log-inbody/SKILL.md`:
- It reads the date, time, weight, body fat %, SMM, visceral fat level and the body-part readings.
- `scripts/inbody.py` checks each value against a plausible range, cross-checks body fat mass against
  weight × body fat % and BMR against lean mass, and picks the row (the next empty one from row 16).
- It writes A:D and F:T. Column E is the lean-mass formula and is never written.
- If any field is blurry, cut off or out of range, nothing is written. Claude names the field and asks you to confirm it or send a clearer photo.
- If a scan with the same date already exists, Claude asks before overwriting it.

**Daily targets** (Body Log, recalculated from the latest scan):
- Protein = 1 g per lb of lean body mass.
- Maintenance = Katch-McArdle `(370 + 21.6 × LBM kg) × 1.55`.
- Surplus:
  - +300 kcal until a goal is set.
  - Once a goal is set, it is scaled to reach the goal weight by the goal date at about 500 kcal per lb/week, clamped to 150–500.
  - 0 once the goal weight is reached.
- Calorie target = maintenance + surplus.

`scripts/targets.py` mirrors these formulas for the tests.

Everything else is formula-driven and protected. Because Marcus owns the sheet, Google can't hard-lock
it for him, so the protection is set to warn before any edit outside the yellow cells.

## Progressive overload

| Situation | Next week |
|---|---|
| Main lift: AMRAP set reaches the top of the range (≥ 5 reps) | + increment |
| Accessory: day ticked complete with a weight logged | + increment |
| Target missed or day not completed | same weight |
| You typed a weight different from the suggestion | your weight is the new baseline |

Increments come from the Library tab:
- Upper body: +5 lb on compound / Smith / machine lifts, +2.5 lb on isolations.
- Legs: +10 lb on barbell squats, hack squat and leg press; +5 lb on other leg accessories.

In the first week of a block, the suggestion comes from the Library's *Start lb* column (set by the
recalculation, and for block D from weeks 1–3). Blank means log what you lift and it becomes the baseline.

## Make.com scenarios (team "My Team")

| Scenario | Schedule | Does |
|---|---|---|
| Lifting – Weekly Tab Generator (Sat 7am) | Saturdays 07:00 ET | If `Config!B16` is TRUE: duplicates `_Template` as `Wk NN · Mon d`, stamps the week number and previous tab, protects the tab except the yellow cells, freezes exercises and suggested weights as values, then advances Config. |
| Lifting – Workout Complete Email (every 15 min, 5–11 am) | every 15 min, 05:00–11:00 ET (a day ticked after 11 am is emailed at 5 am the next morning) | Reads `Outbox` (days ticked complete with no "Email sent" stamp), emails each summary to the address in `Config!B8`, then stamps "Email sent". The email also includes the previous day's nutrition totals and the surplus or deficit vs maintenance. The recipient gets only the email, with no access to the sheet. |
| Lifting – Setup (one-shot) | (deleted after use) | Created the spreadsheet from `build/*.json`; blueprint kept in `make/`. |

Claude scheduled task **Lifting – end-of-block recalculation**: Thursdays 08:43 ET. Does nothing
unless it's week 6 of a block.

The blueprints are in `make/` and are regenerated with `python scripts/build_make.py <spreadsheetId>`.

## Changing the program

1. Edit `program/library.yaml`.
2. Run `python -m pytest`. It checks the spec rules: supersets, belt squat, equipment, no deadlifts,
   set/rep ranges, increments, videos, rotation and the 30-minute cap.
3. Run `python scripts/build_update.py` and apply `build/update_library.json` (and
   `update_template.json` if the layout changed) to the live sheet. **Never re-run Setup on the
   live sheet:** it also holds other tabs (Today, Backlog, Business …).

## Files

- `program/library.yaml`: blocks D/E/F, time math settings, increments, start weights and video links.
- `program/adjustments.yaml`: next-block changes written by the recalculation (created at the first one).
- `scripts/program.py`: library + adjustments = the effective program.
- `scripts/timing.py`: superset and day minutes.
- `scripts/recalc.py`: the end-of-block rules; `.claude/skills/new-block/` is the procedure.
- `scripts/build_update.py`: targeted updates for the live sheet.
- `scripts/layout.py`: column and row layout shared by the builders.
- `scripts/build_logs.py`: Body Log, Monthly Check-in and Nutrition tabs.
- `scripts/inbody.py`: checks values read from an InBody photo and plans the Body Log write.
- `.claude/skills/log-inbody/`: the photo-to-Body-Log procedure Claude follows.
- `scripts/targets.py`: Python mirror of the calorie and protein target formulas.
- `scripts/build_sheet.py`: Google Sheets API payloads (`build/create.json`, `build/requests.json`).
- `scripts/build_make.py`: Make blueprints.
- `scripts/progression.py`: Python mirror of the sheet's progression formulas (for tests).
- `tests/`: progression, program-rule, timing, InBody and recalculation tests.

## Live setup

- Spreadsheet: [Lifting Plan Tracker](https://docs.google.com/spreadsheets/d/1fTHQ7q9cnYqHdw5xueuDbO5nDeAp3Fhhd8VpKPH3LeU/edit). Week 1 = `Wk 01 · Oct 11` (Sun Oct 11 – Sat Oct 17).
- Make: generator scenario 6590981 (Saturdays 07:00 ET), email scenario 6592194 (every 15 min, 05:00–11:00 ET).
- Verified end to end on 2026-10-11:
  - A test day sent the summary email (KB 13 min, body weight, 3 of 5 targets hit, ⬆ weights).
  - "Email sent" was stamped.
  - A test Week 2 carried forward 185→190, 50→55 and 20→22.5.
  - Test data was then removed.
- v2 (2026-10-11): added the log tabs and per-day KB videos. The nutrition section was verified in a test email (yesterday 1,310 kcal / 137 g, deficit of 2,940 vs maintenance, targets 3,240 kcal / 156 g); the test data was then cleared.
- v3 (2026-10-26, row 50): 45-minute superset plan (blocks D/E/F from week 4), InBody body-part
  columns (Oct 26 scan backfilled in row 17), Block Review tab and the 6-week recalculation.
  Verified on a throwaway test tab: week 4 showed the right exercises, labels, time math and
  start weights; a logged Push 1 gave the right targets, "next week" weights and email HTML
  (6 rows, "5 of 6"); a test week 5 carried 145→150 etc. The test tabs were deleted; no email was sent.
