"""The effective program: program/library.yaml plus the end-of-block changes in
program/adjustments.yaml (written by scripts/recalc.py, never by hand).

adjustments.yaml looks like:
  blocks:
    E:
      review_date: 2026-12-10
      swap:  {"L1|4": "Single-Leg Leg Extension"}   # day|order -> exercise from the library
      sets:  {"P1|3": 4}                             # day|order -> sets
      rest:  {"P1": [90, 30, 30]}                    # rest after each round, supersets 1-3
      start_lb: {"L1|1": 255}                        # week-1 suggested weights (replaces library.yaml's)
"""
import copy
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
LIBRARY = ROOT / "program" / "library.yaml"
ADJUSTMENTS = ROOT / "program" / "adjustments.yaml"


def exercises_by_name(lib):
    """Every exercise row in the library, by name (the swap pool)."""
    return {row[0]: row for days in lib["blocks"].values() for rows in days.values() for row in rows}


def load(base=None, adjustments=None):
    lib = copy.deepcopy(base if base is not None else yaml.safe_load(LIBRARY.read_text()))
    if adjustments is None:
        adjustments = yaml.safe_load(ADJUSTMENTS.read_text()) if ADJUSTMENTS.exists() else {}
    pool = exercises_by_name(lib)
    lib.setdefault("rest", {})
    lib.setdefault("start_lb", {})
    for block, adj in ((adjustments or {}).get("blocks") or {}).items():
        days = lib["blocks"][block]
        for key, name in (adj.get("swap") or {}).items():
            day, order = key.split("|")
            old, new = days[day][int(order) - 1], pool[name]
            # keep the slot's type, sets and reps; take name, increment, equipment, muscle, video
            days[day][int(order) - 1] = [new[0], *old[1:5], *new[5:]]
        for key, sets in (adj.get("sets") or {}).items():
            day, order = key.split("|")
            days[day][int(order) - 1][2] = sets
        lib["rest"][block] = dict(adj.get("rest") or {})
        if "start_lb" in adj:
            lib["start_lb"][block] = dict(adj["start_lb"])
    return lib


def rest_for(lib, block, day):
    return lib.get("rest", {}).get(block, {}).get(day) or lib["timing"]["rest_after_round"]
