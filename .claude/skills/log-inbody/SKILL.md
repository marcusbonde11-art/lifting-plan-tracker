---
name: log-inbody
description: Log an InBody body-composition scan into the Lifting Plan Tracker's Body Log tab from a photo of the printout. Use whenever the user pastes a photo of an InBody scan (or asks to log one).
---

# Log an InBody scan from a photo

Sheet: **Lifting Plan Tracker** `1fTHQ7q9cnYqHdw5xueuDbO5nDeAp3Fhhd8VpKPH3LeU`, tab **Body Log**.
Headers on row 15, scans from row 16:

| A | B | C | D | E | F | G |
|---|---|---|---|---|---|---|
| Date | Weight (lb) | Body fat % | Skeletal muscle mass (lb) | Lean body mass (**formula, never write**) | Visceral fat level | Test time |

The printout is in **lb**. Write values as printed; never convert.

## Steps

1. **Read the five fields off the photo:** test date, test time, weight, percent body fat (PBF),
   skeletal muscle mass (SMM) and visceral fat level. On an InBody sheet the date and time sit
   in the header next to the ID/height/age, e.g. `2026.10.18 07:42`.
   - If a digit is blurry, cut off, glared or could be two different numbers, mark that field `?`.
     **Never guess.** Don't fill a field from earlier scans, the Daily Weight tab, or a calculation
     (e.g. PBF from fat mass ÷ weight). Only use the number printed for that field.
2. **Fetch the existing dates:** `get_values` on `'Body Log'!A16:A215`.
3. **Check and plan:**
   ```
   python scripts/inbody.py --date 2026-10-18 --time "7:42 AM" --weight 219.6 --bf 15.4 \
       --smm 106.0 --vfl 6 --existing "Mon Oct 12, 2026" ...
   ```
   Pass `?` for anything unreadable. Pass the A-column values in order, with blank rows as `""`.
4. **Act on the JSON:**
   - `ok: false`: **write nothing.** Tell the user each field in `problems`, along with what you
     could see. Ask them to confirm the value or send a clearer photo. Once they confirm a value,
     re-run step 3 with it.
   - `duplicate_row` set: a scan for that date is already there. Show that row next to the new
     values and ask before overwriting. Write to `duplicate_row` only on a yes; otherwise stop.
   - Otherwise write right away (no confirmation needed): `update_values` for each entry in
     `writes`, with `valueInputOption: USER_ENTERED`.
5. **Verify:** `get_values` on `'Body Log'!A{row}:G{row}`. Check that the row shows all five
   values and E has the lean mass. Then reply with the row number and the values written.

This skill only logs. It does not summarize, chart, trend or email anything.
