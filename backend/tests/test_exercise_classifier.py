from app.services.exercise_classifier import classify_exercise, classify_heuristic


def test_heuristic_pushups() -> None:
    landmarks = {
        "left_shoulder": (0.35, 0.5),
        "right_shoulder": (0.65, 0.5),
        "left_elbow": (0.36, 0.60),
        "right_elbow": (0.64, 0.60),
        "left_wrist": (0.37, 0.62),
        "right_wrist": (0.63, 0.62),
        "left_hip": (0.4, 0.58),
        "right_hip": (0.6, 0.58),
    }
    assert classify_heuristic(landmarks) == "PushUps"


def test_heuristic_squats() -> None:
    landmarks = {
        "left_shoulder": (0.5, 0.3),
        "right_shoulder": (0.5, 0.3),
        "left_hip": (0.5, 0.44),
        "right_hip": (0.5, 0.44),
        "left_knee": (0.56, 0.58),
        "right_knee": (0.44, 0.58),
        "left_ankle": (0.5, 0.72),
        "right_ankle": (0.5, 0.72),
    }
    assert classify_heuristic(landmarks) == "Squats"


def test_smoothing_majority_vote() -> None:
    zone_id = "smooth_test_zone"
    landmarks = {
        "left_shoulder": (0.5, 0.3),
        "left_hip": (0.5, 0.4),
        "left_knee": (0.56, 0.58),
        "left_ankle": (0.5, 0.72),
    }
    labels = []
    for _ in range(6):
        exercise, source, _, _, _, _ = classify_exercise(zone_id, window=None, landmarks=landmarks)
        labels.append(exercise)
        assert source == "heuristic"
    assert labels[-1] == "Squats"
