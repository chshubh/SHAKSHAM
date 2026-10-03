"""Transparent rule-based recommendation engine (no black-box AI).

Pipeline: equipment -> limitations -> difficulty. Goal/time matching happens in
workout_generator. Every removal is counted so the user can see why.
"""

DIFF = {"beginner": 1, "intermediate": 2, "advanced": 3}
LIMITATIONS = {"walking", "standing", "upper_body", "lower_body", "balance",
               "flexibility", "fatigue", "joint_discomfort", "back_discomfort"}


def max_difficulty(profile):
    level = DIFF.get(profile.get("difficulty", "beginner"), 1)
    lims = set(profile.get("limitations", []))
    if lims:
        level = min(level, 2)            # any reported limitation: cap at intermediate
    if lims & {"balance", "fatigue"}:
        level = 1                        # balance / fatigue: stay at beginner
    return level


def position_block(ex, lims):
    pos = ex.get("position")
    if pos == "standing" and lims & {"standing", "balance"}:
        return True
    if pos == "wall" and "standing" in lims:
        return True
    if pos == "floor" and lims & {"standing", "lower_body", "balance"}:
        return True
    return False


def recommend_exercises(profile, exercises):
    """Return (eligible_exercises, report). Empty list when the safety gate is closed."""
    report = {"equipment": 0, "limitations": 0, "difficulty": 0}
    if profile.get("safety_block"):
        return [], report

    have = set(profile.get("equipment", [])) | {"none"}
    lims = set(profile.get("limitations", [])) & LIMITATIONS
    cap = max_difficulty(profile)
    eligible = []
    for ex in exercises:
        if not set(ex.get("equipment", [])) <= have:
            report["equipment"] += 1
            continue
        if position_block(ex, lims) or lims & set(ex.get("avoid_if", [])):
            report["limitations"] += 1
            continue
        if DIFF.get(ex.get("difficulty"), 1) > cap:
            report["difficulty"] += 1
            continue
        eligible.append(ex)
    return eligible, report
