from app.services.exercise_profiles import (
    classify_heuristic_detailed,
    detect_body_orientation,
    infer_squat_phase,
    torso_horizontal_span,
    torso_vertical_span,
)


def _frontal_squat() -> dict[str, tuple[float, float]]:
    return {
        "nose": (0.5, 0.28),
        "left_shoulder": (0.42, 0.3),
        "right_shoulder": (0.58, 0.3),
        "left_hip": (0.44, 0.44),
        "right_hip": (0.56, 0.44),
        "left_knee": (0.46, 0.58),
        "right_knee": (0.54, 0.58),
        "left_ankle": (0.46, 0.72),
        "right_ankle": (0.54, 0.72),
    }


def _left_profile_squat() -> dict[str, tuple[float, float]]:
    return {
        "nose": (0.42, 0.28),
        "left_shoulder": (0.44, 0.3),
        "right_shoulder": (0.48, 0.31),
        "left_hip": (0.44, 0.42),
        "right_hip": (0.47, 0.43),
        "left_knee": (0.46, 0.58),
        "right_knee": (0.47, 0.59),
        "left_ankle": (0.46, 0.72),
        "right_ankle": (0.47, 0.73),
    }


def _left_profile_pushup_bottom() -> dict[str, tuple[float, float]]:
    return {
        "nose": (0.40, 0.48),
        "left_shoulder": (0.42, 0.5),
        "right_shoulder": (0.46, 0.51),
        "left_elbow": (0.43, 0.58),
        "right_elbow": (0.45, 0.58),
        "left_wrist": (0.44, 0.60),
        "right_wrist": (0.45, 0.60),
        "left_hip": (0.42, 0.52),
        "right_hip": (0.45, 0.52),
    }


def test_detect_profile_vs_frontal() -> None:
    assert detect_body_orientation(_frontal_squat()) == "frontal"
    assert detect_body_orientation(_left_profile_squat()) in ("left_profile", "right_profile")


def test_profile_squat_standing_lockout() -> None:
    lm = {
        "nose": (0.42, 0.28),
        "left_shoulder": (0.44, 0.3),
        "right_shoulder": (0.48, 0.31),
        "left_hip": (0.44, 0.40),
        "right_hip": (0.47, 0.41),
        "left_knee": (0.46, 0.66),
        "right_knee": (0.47, 0.67),
        "left_ankle": (0.46, 0.88),
        "right_ankle": (0.47, 0.89),
    }
    assert torso_vertical_span(lm) >= 0.1
    assert infer_squat_phase(lm, "profile_squat") == "Standing"


def test_profile_pushup_classified_not_as_squat() -> None:
    label, scores, _, orientation = classify_heuristic_detailed(_left_profile_pushup_bottom())
    assert orientation != "frontal"
    assert label == "PushUps"
    assert scores["PushUps"] > scores["Squats"]
    assert torso_horizontal_span(_left_profile_pushup_bottom()) < 0.17
