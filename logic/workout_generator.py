"""Builds a balanced warm-up / main / cool-down routine and explains each choice."""

GOAL_LABELS = {
    "general_fitness": "General fitness", "mobility": "Mobility", "strength": "Strength",
    "flexibility": "Flexibility", "balance": "Balance", "endurance": "Endurance",
}
LIM_LABELS = {
    "walking": "walking difficulty", "standing": "standing difficulty",
    "upper_body": "upper-body limitation", "lower_body": "lower-body limitation",
    "balance": "balance difficulty", "flexibility": "flexibility limitation",
    "fatigue": "fatigue with activity", "joint_discomfort": "joint discomfort",
    "back_discomfort": "back discomfort",
}


def est_seconds(sets, per_set, rest):
    return sets * per_set + max(0, sets - 1) * rest


def _why(ex, profile, goal_match):
    why = []
    if goal_match:
        why.append("supports your goal: " + GOAL_LABELS.get(profile.get("goal"), "fitness").lower())
    elif ex["role"] == "warmup":
        why.append("gently warms up your body")
    elif ex["role"] == "cooldown":
        why.append("helps you wind down")
    else:
        why.append("balances your routine")
    if ex["position"] == "seated":
        why.append("done seated")
    elif ex["position"] == "wall":
        why.append("done with wall support")
    elif ex["position"] == "floor":
        why.append("done lying down")
    eq = [e for e in ex["equipment"] if e != "none"]
    why.append("uses " + ", ".join(e.replace("_", " ") for e in eq) if eq else "no equipment needed")
    lims = [LIM_LABELS[l] for l in profile.get("limitations", []) if l in LIM_LABELS]
    if lims:
        why.append("not marked to avoid with your " + lims[0] + (" and others" if len(lims) > 1 else ""))
    return "Chosen because it " + why[0] + "; " + "; ".join(why[1:]) + "."


def build_workout(eligible, profile=None, minutes=15, report=None):
    profile = profile or {}
    goal = profile.get("goal", "general_fitness")
    lims = set(profile.get("limitations", []))
    rest = 30 if "fatigue" in lims else 20
    budget = minutes * 60
    notes = []

    def sets_for(ex):
        s = ex["default_sets"]
        return max(1, s - 1) if "fatigue" in lims else s

    def pick(role):
        pool = [e for e in eligible if e["role"] == role]
        pool.sort(key=lambda e: (goal not in e["categories"], e["name"]))
        return pool[0] if pool else None

    chosen, used = [], 0

    def add(ex):
        nonlocal used
        s = sets_for(ex)
        chosen.append({"ex": ex, "sets": s, "rest": rest})
        used += est_seconds(s, ex["duration_seconds"], rest)

    warm, cool = pick("warmup"), pick("cooldown")
    if warm:
        add(warm)
    reserve = est_seconds(sets_for(cool), cool["duration_seconds"], rest) if cool else 0

    mains = [e for e in eligible if e["role"] == "main"]
    on_goal = sorted([e for e in mains if goal in e["categories"]], key=lambda e: (-len(e["target_area"]), e["name"]))
    others = sorted([e for e in mains if goal not in e["categories"]], key=lambda e: e["name"])
    if len(on_goal) < 2 and mains:
        notes.append("Only a few exercises matched your goal with your answers, so we added gentle general options.")
    covered, picked = set(), []
    for pool in (on_goal, others):
        for pass_distinct in (True, False):
            for ex in pool:
                if ex in picked or len(picked) >= 6:
                    continue
                if pass_distinct and covered & set(ex["target_area"]):
                    continue
                s = sets_for(ex)
                if used + reserve + est_seconds(s, ex["duration_seconds"], rest) > budget:
                    continue
                picked.append(ex)
                add(ex)
                covered |= set(ex["target_area"])
        if len(picked) >= 3:
            break
    if cool:
        add(cool)

    if not picked:
        return {"exercises": [], "duration_minutes": minutes, "estimated_minutes": 0,
                "notes": ["We couldn't find enough suitable exercises for your answers and equipment. "
                          "Try adding equipment such as a chair, or speak with a qualified professional."]}

    out = []
    for order, c in enumerate(chosen):
        ex = c["ex"]
        out.append({"slug": ex["id"], "name": ex["name"], "role": ex["role"], "sets": c["sets"],
                    "reps": ex["default_reps"], "duration_seconds": ex["duration_seconds"],
                    "rest_seconds": c["rest"], "why": _why(ex, profile, goal in ex["categories"])})

    if "fatigue" in lims:
        notes.append("You reported fatigue with activity, so each exercise has fewer sets and longer rests.")
    if lims & {"balance", "fatigue"}:
        notes.append("Only beginner-level exercises are included because of your answers.")
    if profile.get("health_status") == "unsure":
        notes.append("You weren't sure about your health status. Consider checking with a professional before starting.")
    if report and sum(report.values()):
        parts = [f"{n} for {k}" for k, n in report.items() if n]
        notes.append("Set aside " + sum(report.values()).__str__() + " exercises (" + ", ".join(parts) + ").")
    notes.append("Move at a comfortable pace. Stop if anything feels wrong; never push through pain.")

    return {"exercises": out, "duration_minutes": minutes,
            "estimated_minutes": max(1, round(used / 60)), "notes": notes}
