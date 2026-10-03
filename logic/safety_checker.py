"""Conservative safety gate. This is NOT a medical diagnostic system."""

RED_FLAGS = {
    "chest_pain": "chest pain during activity",
    "fainting": "fainting or near-fainting",
    "severe_breathlessness": "severe unexplained shortness of breath",
    "severe_acute_pain": "severe or sudden pain",
    "recent_serious_injury": "a recent serious injury",
    "professional_exercise_restriction": "a professional advising you not to exercise right now",
}
RED_FLAG_KEYS = set(RED_FLAGS)


def safety_check(assessment):
    flags = [k for k in RED_FLAGS if assessment.get(k) is True]
    if flags:
        return {
            "safe_to_generate": False,
            "flags": flags,
            "labels": [RED_FLAGS[f] for f in flags],
            "message": (
                "Based on your answers, Shaksham cannot safely generate a normal workout. "
                "Please speak with a doctor, physiotherapist or other qualified professional "
                "before exercising. If you have chest pain, fainting, or severe breathlessness "
                "right now, seek urgent medical help."
            ),
        }
    return {
        "safe_to_generate": True,
        "flags": [],
        "labels": [],
        "message": "No safety block was triggered by the screening answers.",
    }
