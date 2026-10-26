---
name: new-block
description: The 6-week block recalculation for the Lifting Plan Tracker. Reads the InBody scans (including body-part readings), body weight, food log and logged lifts, then sets up the next block (extra sets for lagging parts, one-arm/one-leg work for an uneven side, start weights from AMRAP sets) and writes a plain-words Block Review. Use when the scheduled Thursday check fires, or when Marcus asks to recalculate the next block.
---

# Recalculate the next block (end of every 6-week block)

Sheet: **Lifting Plan Tracker** `1fTHQ7q9cnYqHdw5xueuDbO5nDeAp3Fhhd8VpKPH3LeU`.
Repo: `marcusbonde11-art/lifting-plan-tracker` (public — **never** put body numbers in the repo;
they go only in the sheet's Block Review tab).

## 0. Is it time?

`get_values` on `Config!B2:B20`. Week-in-block = `(B3 − B20) mod B6 + 1`.
- Not 6 → stop. Reply "Week N is week K of the block; nothing to do." Don't write anything.
- 6 → carry on. The Saturday 7 am generator builds week 1 of the next block from the Library,
  so everything below must be live before then.

## 1. Gather the data into one JSON file

Use `get_values` (formatted values) and save the raw `values` arrays in
`/tmp/recalc_input.json` with these keys:

| key | range |
|---|---|
| `config` | `Config!B2:B20` as a flat list (one value per row) |
| `tabs` | `{tab name: values}` for every `Wk NN · …` tab of this block (the six from `B20 + block×6`), range `A4:W45` |
| `body_log` | `'Body Log'!A16:T215` |
| `body_targets` | `'Body Log'!B2:B13` as a flat list |
| `daily_weight` | `'Daily Weight'!A4:C` |
| `nutrition` | `Nutrition!A5:E` |

Tab names are in `Config!B4` (current) and `B5` (previous); the others follow the pattern
`Wk NN · Mon d`. List the sheet's tabs with `get_spreadsheet` (fields `sheets.properties.title`).

## 2. Decide

```
python scripts/recalc.py /tmp/recalc_input.json --apply
```
It prints the review rows and the changes, and writes them to `program/adjustments.yaml` (only in
week 6). The rules are in the docstring of `scripts/recalc.py` — that's what "plain words" means in
the review. Then:
```
python -m pytest -q          # must pass: every day still fits 30 minutes
python scripts/build_update.py --block <next block>
```
The second command prints `{"range": "Library!A..:S..", "values": [...]}` for the next block.

## 3. Make it live (before Saturday 7 am ET)

1. `update_values` with that range and values (the next block's 36 Library rows).
2. **Block Review tab**: if there's no tab called `Block Review`, add it (`addSheet`, title
   `Block Review`). Append below the last used row: a bold title row
   `Block <letter> review – <today>`, a header row `Area | What we saw | What changes`, then the
   `review` rows from the JSON, then one blank row. Newest review at the bottom.
3. Spot-check: `get_values` on the first 6 rows you wrote in the Library and confirm sets, rest
   text and start weights match `program/adjustments.yaml`.

## 4. Save and report

- Commit `program/adjustments.yaml` (and nothing personal) on a branch named
  `claude/block-<letter>-recalc-<yyyy-mm-dd>` and push it. Don't open a PR unless asked.
- Reply in plain words: what changed in the next block and why (2–6 bullets, from the review),
  and that the Block Review tab has the details.

## Guardrails

- Never email anyone. Never touch the weekly tabs, Config, Outbox or `_Template`.
- If any range can't be read or the script errors, write nothing to the sheet and say what failed.
- Don't re-run Setup or `build/requests.json` on the live sheet (it holds other tabs too).
