from app.services.exercise_profiles import classify_heuristic_detailed


def _pushup_pose() -> dict[str, tuple[float, float]]:
    return {
        "left_shoulder": (0.35, 0.5),
        "right_shoulder": (0.65, 0.5),
        "left_elbow": (0.36, 0.60),
        "right_elbow": (0.64, 0.60),
        "left_wrist": (0.37, 0.62),
        "right_wrist": (0.63, 0.62),
        "left_hip": (0.4, 0.58),
        "right_hip": (0.6, 0.58),
        "left_knee": (0.45, 0.70),
        "right_knee": (0.55, 0.70),
    }


def _squat_pose() -> dict[str, tuple[float, float]]:
    return {
        "left_shoulder": (0.5, 0.3),
        "right_shoulder": (0.5, 0.3),
        "left_hip": (0.5, 0.44),
        "right_hip": (0.5, 0.44),
        "left_knee": (0.56, 0.58),
        "right_knee": (0.44, 0.58),
        "left_ankle": (0.5, 0.72),
        "right_ankle": (0.5, 0.72),
    }


def test_pushup_not_classified_as_squat() -> None:
    label, scores, debug = classify_heuristic_detailed(_pushup_pose())
    assert label == "PushUps"
    assert scores["PushUps"] > scores["Squats"]
    assert debug["torso_vertical_span"] is not None
    assert debug["torso_vertical_span"] < 0.16


def test_squat_not_classified_as_pushup() -> None:
    label, scores, _ = classify_heuristic_detailed(_squat_pose())
    assert label == "Squats"
    assert scores["Squats"] > scores["PushUps"]
