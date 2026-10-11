"""Python mirror of the Body Log target formulas (for tests)."""
from datetime import date


def lean_mass(weight_lb, body_fat_pct):
    return round(weight_lb * (1 - body_fat_pct / 100), 1)


def maintenance(lbm_lb, activity=1.55):
    """Katch-McArdle BMR (370 + 21.6 × LBM kg) × activity, rounded to 10 kcal."""
    return round((370 + 21.6 * lbm_lb / 2.20462) * activity, -1)


def surplus(weight_lb, goal_lb=None, goal_date=None, today=None):
    if goal_lb is None or goal_date is None:
        return 300
    if goal_lb <= weight_lb:
        return 0
    today = today or date.today()
    if goal_date <= today:
        return 500
    weeks = (goal_date - today).days / 7
    return round(min(500, max(150, (goal_lb - weight_lb) / weeks * 500)), -1)


def targets(weight_lb, body_fat_pct, goal_lb=None, goal_date=None, today=None, activity=1.55):
    lbm = lean_mass(weight_lb, body_fat_pct)
    kcal = maintenance(lbm, activity) + surplus(weight_lb, goal_lb, goal_date, today)
    return {"lbm": lbm, "calories": kcal, "protein_g": round(lbm)}
