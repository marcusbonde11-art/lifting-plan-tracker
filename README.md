# lifting-plan-tracker

A Google Sheets lifting tracker for a twice-weekly Push / Pull / Legs split, with automatic
progressive overload and two Make.com automations:
- **Saturday:** builds next week's tab.
- **When a day is ticked complete:** emails a summary of that workout.

```
 program/library.yaml ──► scripts/build_sheet.py ──► Make "Lifting – Setup" ──► Google Sheet
                                                                                 │
 Saturday 6 pm ET  Make "Weekly Tab Generator"  ── copies _Template → "Wk NN · Mon d" ┤
 every 30 min      Make "Workout Complete Email" ── Outbox → Gmail → stamps "Email sent" ┘
```

## The week

| Sun | Mon | Tue | Wed | Thu | Fri | Sat |
|---|---|---|---|---|---|---|
| Push 1 | Pull 1 | Legs 1 | Push 2 | Pull 2 | Legs 2 | Rest |

Every session:
1. **Kettlebell warm-up, ~15 min.** A beginner-friendly, male-led follow-along matched to the day
   (linked on each day's 🔔 row; stored in `Config!B17:C19`):
   - Push: Samuel Jordan, *Chest & Triceps with One Kettlebell* (15 min)
   - Pull: DanielPT Fitness, *15 min Pull Upper Body Kettlebell* (slow-paced)
   - Legs: DanielPT Fitness, *15 min Kettlebell Leg & Glute* (all standing)
2. **Main lift.** One heavy compound, 4–5 sets × 3–5 reps. The last set is AMRAP. Rest 3–5 min.
3. **Four accessories.** 3–4 sets × 8–12 reps. Rest 2–3 min for compound or machine moves,
   60–90 s for isolations.

**Equipment rules:**
- Upper body: dumbbells, machines and cables only. The Smith machine is the one barbell exception.
- Legs: barbell allowed, including squats.
- No deadlift variants anywhere.

**Rotation:** exercises stay fixed for 6-week blocks, then rotate (Block A → B → C → A).

**Videos:** every exercise links a short (< 4 min) how-to video.

## What you edit (yellow cells only)

| Cell | Where | Notes |
|---|---|---|
| Weight lifted | every exercise row | Leave blank if you used the suggested weight. A different number becomes your new baseline. |
| AMRAP reps | main-lift row | Reps on the final set. |
| KB start / KB stop | day header row | Kettlebell warm-up times, e.g. `6:05 am`. Duration is calculated and included in the email. |
| Body weight (lb) | day header row, column D | Optional. Included in the email with the change since your last weigh-in. |
| Workout complete ☐ | day header row | Ticking it queues the summary email. |

Other tabs (yellow cells are yours):

| Tab | What you enter | What it calculates |
|---|---|---|
| Body Log | Weekly InBody scan: date, weight, body fat %, SMM. Goal weight and goal date (B7:B8). | Lean body mass, then the daily targets below. |
| Monthly Check-in | Date, waist, link to progress photos, notes. | Waist change vs the previous month. |
| Nutrition | One row per weighed food: date, food, grams, calories, protein. You can also tell Claude in chat what you ate and it will log it ("Logged by" = Claude). | Today's totals vs targets. |

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

Week 1 (and the first week of a new block) has no suggested weight. Log what you lift and it becomes the baseline.

## Make.com scenarios (team "My Team")

| Scenario | Schedule | Does |
|---|---|---|
| Lifting – Weekly Tab Generator (Sat 6pm) | Saturdays 18:00 ET | If `Config!B16` is TRUE: duplicates `_Template` as `Wk NN · Mon d`, stamps the week number and previous tab, protects the tab except the yellow cells, freezes exercises and suggested weights as values, then advances Config. |
| Lifting – Workout Complete Email (every 30 min) | every 30 min, 06:00–23:00 ET | Reads `Outbox` (days ticked complete with no "Email sent" stamp), emails each summary to the address in `Config!B8`, then stamps "Email sent". The email also includes the previous day's nutrition totals and the surplus or deficit vs maintenance. The recipient gets only the email, with no access to the sheet. |
| Lifting – Setup (one-shot) | (deleted after use) | Created the spreadsheet from `build/*.json`; blueprint kept in `make/`. |

The blueprints are in `make/` and are regenerated with `python scripts/build_make.py <spreadsheetId>`.

## Changing the program

1. Edit `program/library.yaml`.
2. Run `python -m pytest`. It checks the spec rules: equipment, no deadlifts, set/rep ranges,
   increments, videos and rotation.
3. Run `python scripts/build_sheet.py`, then re-paste the `Library` tab. You can also re-run Setup
   for a fresh workbook.

## Files

- `program/library.yaml`: all three blocks, rest times, increments and video links.
- `scripts/layout.py`: column and row layout shared by the builders.
- `scripts/build_logs.py`: Body Log, Monthly Check-in and Nutrition tabs.
- `scripts/targets.py`: Python mirror of the calorie and protein target formulas.
- `scripts/build_sheet.py`: Google Sheets API payloads (`build/create.json`, `build/requests.json`).
- `scripts/build_make.py`: Make blueprints.
- `scripts/progression.py`: Python mirror of the sheet's progression formulas (for tests).
- `tests/`: progression and program-rule tests.

## Live setup

- Spreadsheet: [Lifting Plan Tracker](https://docs.google.com/spreadsheets/d/1fTHQ7q9cnYqHdw5xueuDbO5nDeAp3Fhhd8VpKPH3LeU/edit). Week 1 = `Wk 01 · Oct 11` (Sun Oct 11 – Sat Oct 17).
- Make: generator scenario 6590981 (Saturdays 18:00 ET), email scenario 6592194 (every 30 min, 06:00–23:00 ET).
- Verified end to end on 2026-10-11:
  - A test day sent the summary email (KB 13 min, body weight, 3 of 5 targets hit, ⬆ weights).
  - "Email sent" was stamped.
  - A test Week 2 carried forward 185→190, 50→55 and 20→22.5.
  - Test data was then removed.
- v2 (2026-10-11): added the log tabs and per-day KB videos. The nutrition section was verified in a test email (yesterday 1,310 kcal / 137 g, deficit of 2,940 vs maintenance, targets 3,240 kcal / 156 g); the test data was then cleared.
