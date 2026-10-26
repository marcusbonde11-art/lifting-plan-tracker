---
name: log-inbody
description: Log an InBody body-composition scan into the Lifting Plan Tracker's Body Log tab from a photo of the printout, including the body-part (segmental) readings. Use whenever the user pastes a photo of an InBody scan (or asks to log one).
---

# Log an InBody scan from a photo

Sheet: **Lifting Plan Tracker** `1fTHQ7q9cnYqHdw5xueuDbO5nDeAp3Fhhd8VpKPH3LeU`, tab **Body Log**.
Headers on row 15, scans from row 16:

| A | B | C | D | E | F | G |
|---|---|---|---|---|---|---|
| Date | Weight (lb) | Body fat % | Skeletal muscle mass (lb) | Lean body mass (**formula, never write**) | Visceral fat level | Test time |

| H–L | M–Q | R | S | T |
|---|---|---|---|---|
| Lean (lb): right arm, left arm, trunk, right leg, left leg | % of ideal, same order | Body fat mass (lb) | ECW/TBW | BMR (kcal) |

The printout is in **lb**. Write values as printed; never convert.

## Steps

1. **Read every field off the photo:**
   - Header: test date and time, e.g. `10.26.2026 06:48`.
   - Body Composition Analysis: **Body Fat Mass** (lb).
   - Muscle-Fat Analysis: **Weight**, **SMM**.
   - Obesity Analysis: **Percent Body Fat**.
   - **Segmental Lean Body Analysis** (left side, middle of the sheet). Each body part has two numbers:
     the top one is lb, the bottom one is %. Right arm, left arm, trunk, right leg, left leg.
     Don't confuse this with **Segmental Fat Analysis** on the right side (fat lb in brackets and
     %), which is not logged.
   - ECW/TBW Analysis: the ratio (e.g. `0.378`).
   - Right column: **Visceral Fat Level** and **Basal Metabolic Rate** (kcal).
   - If a digit is blurry, cut off, glared or could be two different numbers, mark that field `?`.
     **Never guess.** Don't fill a field from earlier scans, the Body Composition History strip,
     the Daily Weight tab or a calculation. Only use the number printed for that field.
2. **Fetch the existing dates:** `get_values` on `'Body Log'!A16:A215`.
3. **Check and plan:**
   ```
   python scripts/inbody.py --date 2026-10-26 --time "6:48 AM" --weight 215.9 --bf 15.9 \
       --smm 103.6 --vfl 7 \
       --ra_lb 10.94 --la_lb 10.74 --tr_lb 78.7 --rl_lb 28.68 --ll_lb 28.82 \
       --ra_pct 120.9 --la_pct 118.6 --tr_pct 109.2 --rl_pct 114.0 --ll_pct 114.5 \
       --bfm 34.2 --ecw 0.378 --bmr 2150 --existing "Mon Oct 12, 2026" ...
   ```
   Pass `?` for anything unreadable. Pass the A-column values in order, with blank rows as `""`.
   Besides range checks, the script checks body fat mass against weight × body fat % and BMR
   against lean mass, so a misread digit that's still in range gets caught.
4. **Act on the JSON:**
   - `ok: false`: **write nothing.** Tell the user each field in `problems`, along with what you
     could see. Ask them to confirm the value or send a clearer photo. Once they confirm a value,
     re-run step 3 with it.
   - `duplicate_row` set: a scan for that date is already there. Show that row next to the new
     values and ask before overwriting. Write to `duplicate_row` only on a yes; otherwise stop.
   - Otherwise write right away (no confirmation needed): `update_values` for each entry in
     `writes`, with `valueInputOption: USER_ENTERED`.
5. **Verify:** `get_values` on `'Body Log'!A{row}:T{row}`. Check that every value is there and E has
   the lean mass. Then reply with the row number and the values written.

This skill only logs. The 6-week block recalculation (`.claude/skills/new-block/`) reads these
columns; this skill does not summarize, chart, trend or email anything.
