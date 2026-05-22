from app.services.exercise_profiles import (
    classify_heuristic,
    classify_heuristic_detailed,
    elbow_angle,
    infer_pushup_phase,
    infer_squat_phase,
    knee_angle,
    form_penalty_for_exercise,
    pushup_profile,
    squat_profile,
)


def _pushup_landmarks(
    *,
    shoulder_y: float = 0.5,
    elbow_y: float,
    wrist_y: float,
) -> dict[str, tuple[float, float]]:
    return {
        "left_shoulder": (0.35, shoulder_y),
        "right_shoulder": (0.65, shoulder_y),
        "left_elbow": (0.36, elbow_y),
        "right_elbow": (0.64, elbow_y),
        "left_wrist": (0.37, wrist_y),
        "right_wrist": (0.63, wrist_y),
        "left_hip": (0.4, shoulder_y + 0.08),
        "right_hip": (0.6, shoulder_y + 0.08),
    }


def _squat_landmarks(
    *,
    hip_y: float = 0.44,
    knee_y: float,
    ankle_y: float,
    knee_x: float = 0.56,
) -> dict[str, tuple[float, float]]:
    return {
        "left_shoulder": (0.5, 0.3),
        "right_shoulder": (0.5, 0.3),
        "left_hip": (0.5, hip_y),
        "right_hip": (0.5, hip_y),
        "left_knee": (knee_x, knee_y),
        "right_knee": (1.0 - knee_x, knee_y),
        "left_ankle": (0.5, ankle_y),
        "right_ankle": (0.5, ankle_y),
    }


def test_pushup_full_extension_is_standing() -> None:
    lm = _pushup_landmarks(elbow_y=0.52, wrist_y=0.64)
    assert infer_pushup_phase(lm, "z1") == "Standing"


def test_pushup_bottom_phase() -> None:
    lm = _pushup_landmarks(elbow_y=0.60, wrist_y=0.62)
    assert infer_pushup_phase(lm, "z2") == "Bottom"


def test_squat_full_extension_is_standing() -> None:
    lm = _squat_landmarks(hip_y=0.40, knee_y=0.68, ankle_y=0.90, knee_x=0.5)
    angle = knee_angle(lm)
    assert angle is not None
    assert angle >= squat_profile().standing_min_angle
    assert infer_squat_phase(lm, "z3") == "Standing"


def test_squat_bottom_phase() -> None:
    lm = _squat_landmarks(knee_y=0.62, ankle_y=0.66, knee_x=0.60)
    angle = knee_angle(lm)
    assert angle is not None
    assert angle <= squat_profile().bottom_max_angle
    assert infer_squat_phase(lm, "z4") == "Bottom"


def test_incomplete_lockout_penalty() -> None:
    lm = _squat_landmarks(hip_y=0.40, knee_y=0.64, ankle_y=0.84, knee_x=0.54)
    angle = knee_angle(lm)
    assert angle is not None
    assert angle < squat_profile().standing_min_angle
    penalty = form_penalty_for_exercise("Squats", lm, "Standing")
    assert penalty >= 6.0


def test_classify_prefers_squat_with_vertical_torso_and_deep_knee() -> None:
    lm = _squat_landmarks(knee_y=0.62, ankle_y=0.66, knee_x=0.60)
    assert classify_heuristic(lm) == "Squats"


def test_pushup_rep_sequence_reaches_standing() -> None:
    zone = "rep_seq"
    phases = []
    sequence = [
        (0.52, 0.64),
        (0.60, 0.62),
        (0.56, 0.63),
        (0.52, 0.64),
    ]
    for elbow_y, wrist_y in sequence:
        lm = _pushup_landmarks(elbow_y=elbow_y, wrist_y=wrist_y)
        phases.append(infer_pushup_phase(lm, zone))
    assert "Bottom" in phases
    assert phases[-1] == "Standing"


def test_temporal_angles_empty_vals_no_crash() -> None:
    """_temporal_joint_angles must not crash when angle lists are empty."""
    # Minimal landmarks — no elbows/knees so angle lists will be empty
    landmarks = {
        "left_shoulder": (0.5, 0.3),
        "right_shoulder": (0.5, 0.3),
        "left_hip": (0.5, 0.6),
        "right_hip": (0.5, 0.6),
    }
    # Should not crash
    label, scores, debug, orientation = classify_heuristic_detailed(landmarks, window=None)
    assert label in ("PushUps", "Squats", "RunInPlace")
