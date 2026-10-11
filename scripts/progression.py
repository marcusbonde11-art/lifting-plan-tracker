"""Python mirror of the progression formulas in the weekly tab (columns H and I).

The sheet is the source of truth; this exists so the rules can be unit-tested.
"""


def target_hit(ex_type, rep_high, amrap, lifted, day_complete):
    """Column H. Returns True / False, or None when there's nothing to judge yet."""
    if ex_type == "Heavy":
        if amrap is None:
            return None
        return amrap >= rep_high
    if not day_complete:
        return None
    return lifted is not None


def next_week(suggested, lifted, hit, increment):
    """Column I. The weight actually lifted (or the suggestion, if blank) is the baseline."""
    used = lifted if lifted is not None else suggested
    if not used:
        return None
    return used + increment if hit else used
