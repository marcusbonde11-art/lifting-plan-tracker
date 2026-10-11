# Paused: resume checklist

Paused on 2026-10-11 at the user's request ("pause until usage reset").

## Live state
- **Sheet:** "Lifting Plan Tracker", ID `1fTHQ7q9cnYqHdw5xueuDbO5nDeAp3Fhhd8VpKPH3LeU`
  - Built: Start Here, Config, Library, hidden Outbox and hidden _Template.
  - **Wk 01 · Oct 18** has been generated and checked: exercises, prescriptions, rest times, videos and dates are all correct.
- **Make (team "My Team", org on the Core plan):**
  - `Lifting – Setup (one-shot)`, id 6590912. Active, on-demand only. Currently holds a test-data write.
  - `Lifting – Weekly Tab Generator (Sat 6pm)`, id 6590981. Active, but still **on-demand**. Its schedule isn't set yet.
  - `Lifting – Workout Complete Email`: **not created yet**. The blueprint is in `make/daily_email.blueprint.json`.

## ⚠️ Test data currently in the live sheet (clean up first)
- `Config!B8` was temporarily set to `marcusbonde11@gmail.com`. Restore it to `Maegirl333@gmail.com`.
- In `Wk 01 · Oct 18`, clear these test cells:
  - F5:G5 (185, 5)
  - F6:F7 (50, 20)
  - J4:K4 (6:00–6:13 AM)
  - M4 (TRUE)
  - F11:G11 (150, 4)

## Remaining steps
1. **New request: body-weight field emailed to Maegirl333.**
   - Add one yellow "Body weight (lb)" cell per day. Put it on the day header row, next to KB start/stop and Workout complete. A spare column could hold it, or add a column O and shift the hidden helpers right by one.
   - Include it in the daily summary email ("Body weight: 195 lb"), and show the change from the last logged weight if one exists.
   - Update the following, then re-run setup for the template only (a `_Template` row-4 header write plus the copy to the other days) and patch Wk 01:
     - `scripts/layout.py` (COLS, `editable_ranges`)
     - `scripts/build_sheet.py` (`header_cells`: cell + email HTML)
     - the README
     - tests
2. Finish the end-to-end test:
   - Create the email scenario and run it once. Check the test email arrives at marcusbonde11@gmail.com and that "Email sent" gets stamped.
   - Set `Config!B16` to TRUE and run the generator to build a test Wk 02. Check the carried-forward weights:
     - Smith bench: 185 → 190 (AMRAP 5)
     - Shoulder press: 50 → 55
     - Cable fly: 20 → 22.5
     - Iso row: 150 → 150 (AMRAP 4)
   - Then delete sheet 100002, restore the `B16` formula `=OR(B3=0,B15-TODAY()<=1)`, and restore `Config!B3:B5` to `1 / Wk 01 · Oct 18 / (blank)`.
3. Clean up the test data (above).
4. Schedule the scenarios:
   - Generator: weekly, Saturday 18:00 America/New_York. Check the Make org timezone (id 301) first.
   - Email: every 30 min, 06:00–23:00.
5. Optional: deactivate or delete the Setup scenario.
6. Commit the final blueprints to `make/`.
