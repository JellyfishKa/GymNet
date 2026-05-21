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
    label, scores, debug, _ = classify_heuristic_detailed(_pushup_pose())
    assert label == "PushUps"
    assert scores["PushUps"] > scores["Squats"]
    assert debug["torso_vertical_span"] is not None
    assert debug["torso_vertical_span"] < 0.16


def test_squat_not_classified_as_pushup() -> None:
    label, scores, _, _ = classify_heuristic_detailed(_squat_pose())
    assert label == "Squats"
    assert scores["Squats"] > scores["PushUps"]


def _run_pose() -> dict[str, tuple[float, float]]:
    return {
        "left_shoulder": (0.48, 0.28),
        "right_shoulder": (0.52, 0.28),
        "left_hip": (0.48, 0.42),
        "right_hip": (0.52, 0.42),
        "left_knee": (0.50, 0.56),
        "right_knee": (0.50, 0.56),
        "left_ankle": (0.48, 0.68),
        "right_ankle": (0.52, 0.78),
        "left_elbow": (0.47, 0.36),
        "right_elbow": (0.53, 0.36),
    }


def _run_window() -> list[list[float]]:
    from app.services.landmark_sequence import FEATURE_DIM, LANDMARK_NAMES

    frames: list[list[float]] = []
    for step in (-0.04, 0.04, -0.05, 0.05, -0.04, 0.04, -0.03, 0.03, -0.04, 0.04, -0.05, 0.05, -0.04):
        lm = _run_pose()
        lm = dict(lm)
        lm["left_ankle"] = (lm["left_ankle"][0], lm["left_ankle"][1] + step)
        lm["right_ankle"] = (lm["right_ankle"][0], lm["right_ankle"][1] - step)
        vec = [0.0] * FEATURE_DIM
        for i, name in enumerate(LANDMARK_NAMES):
            p = lm.get(name)
            if p:
                vec[i * 3] = p[0]
                vec[i * 3 + 1] = p[1]
        frames.append(vec)
    return frames


def test_run_not_classified_as_pushup_or_squat() -> None:
    label, scores, _, _ = classify_heuristic_detailed(_run_pose(), _run_window())
    assert label == "RunInPlace"
    assert scores["RunInPlace"] > scores["PushUps"]
    assert scores["RunInPlace"] > scores["Squats"]
