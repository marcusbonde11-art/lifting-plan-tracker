# Lifting Plan Tracker

- When the user pastes a photo of an InBody scan, follow `.claude/skills/log-inbody/SKILL.md`.
  It writes the scan, including the body-part readings, to the Body Log tab and flags unreadable
  fields instead of guessing.
- At the end of each 6-week block (or when asked to recalculate the plan), follow
  `.claude/skills/new-block/SKILL.md`.
- The live sheet also holds other tabs: never re-run Setup on it. Use `scripts/build_update.py`.
- The repo is public: body numbers go in the sheet, never in the repo.
- Tests: `python -m pytest`.
