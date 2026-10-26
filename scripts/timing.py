"""Time math for a session: three supersets (1A/1B, 2A/2B, 3A/3B) inside the lifting cap.

A round = A set + walk + B set + rest. When one exercise of a pair has an extra set, that last
round is just the one set + rest. Superset 1 also gets the heavy lift's ramp-up sets.
The numbers live in program/library.yaml (timing:), so the sheet and the tests agree. `rest`
is the rest after each round for supersets 1-3; the end-of-block recalculation can shorten it
on a day that gets an extra set (scripts/recalc.py), so pass the day's value when there is one.
"""


def set_seconds(ex_type, t):
    return t["heavy_set"] if ex_type == "Heavy" else t["set"]


def superset_minutes(a, b, ss, t, rest=None):
    """Minutes for one superset. a/b are library rows; ss is 1, 2 or 3."""
    r = (rest or t["rest_after_round"])[ss - 1]
    both = min(a[2], b[2])
    longer = a if a[2] >= b[2] else b
    seconds = both * (set_seconds(a[1], t) + t["move"] + set_seconds(b[1], t) + r)
    seconds += (max(a[2], b[2]) - both) * (set_seconds(longer[1], t) + r)
    minutes = seconds / 60
    if a[1] == "Heavy":
        minutes += t["ramp_up_min"]
    return round(minutes, 1)


def day_minutes(exercises, t, rest=None):
    """(per-superset minutes, total lifting minutes) for a day's six exercises."""
    ss = [superset_minutes(exercises[2 * i], exercises[2 * i + 1], i + 1, t, rest) for i in range(3)]
    total = sum(ss) + t["between_supersets_min"] * (len(ss) - 1)
    return ss, round(total, 1)


def heavy_rest_seconds(exercises, t, rest=None):
    """How long the heavy lift's muscles rest between their own sets (the 1B set fills it)."""
    return t["move"] + set_seconds(exercises[1][1], t) + (rest or t["rest_after_round"])[0]


def slot(order):
    """1 -> '1A', 2 -> '1B', ... 6 -> '3B'."""
    return f"{(order + 1) // 2}{'AB'[(order - 1) % 2]}"


def rest_text(order, exercises, t, rest=None):
    """What the Rest column says for exercise `order` (1-based) of a day."""
    ss = (order + 1) // 2
    if order % 2:  # A exercise
        return f"→ {slot(order + 1)} now"
    a, b = exercises[order - 2], exercises[order - 1]
    mins = superset_minutes(a, b, ss, t, rest)
    rounds = max(a[2], b[2])
    ramp = " incl. ramp-up" if a[1] == "Heavy" else ""
    return f"rest {(rest or t['rest_after_round'])[ss - 1]} s → {slot(order - 1)} · {rounds} rounds ≈ {mins:g} min{ramp}"
