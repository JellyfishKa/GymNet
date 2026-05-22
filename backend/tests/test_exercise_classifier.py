from app.services.exercise_classifier import classify_exercise, classify_heuristic, clear_classifier_state


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
        exercise, source, _, _, _, _, _, _ = classify_exercise(zone_id, window=None, landmarks=landmarks)
        labels.append(exercise)
        assert source == "heuristic"
    assert labels[-1] == "Squats"


def test_smooth_does_not_crash_on_first_call() -> None:
    """Smoke test: classify_exercise returns valid exercise on a fresh zone (no prior state)."""
    zone_id = "test_smooth_empty"
    clear_classifier_state(zone_id)
    landmarks = {"left_shoulder": (0.5, 0.3), "left_hip": (0.5, 0.6)}
    result = classify_exercise(zone_id, window=None, landmarks=landmarks)
    assert result[0] in ("PushUps", "Squats", "RunInPlace")


def test_classify_falls_back_when_ml_raises(monkeypatch) -> None:
    """classify_exercise must return heuristic result when ML inference raises."""
    import numpy as np
    from app.services import exercise_classifier
    from app.services.exercise_classifier import clear_classifier_state

    # Make _load_model return a non-None sentinel so ML path is entered
    monkeypatch.setattr(exercise_classifier, "_load_model", lambda: object())
    # Make _predict_ml_probs raise
    def raise_boom(w):
        raise RuntimeError("boom")
    monkeypatch.setattr(exercise_classifier, "_predict_ml_probs", raise_boom)

    clear_classifier_state("test_ml_fallback")
    landmarks = {"left_shoulder": (0.5, 0.3), "left_hip": (0.5, 0.6)}
    window = np.zeros((13, 99), dtype=np.float32)
    result = exercise_classifier.classify_exercise(
        "test_ml_fallback", window=window, landmarks=landmarks
    )
    assert result[0] in ("PushUps", "Squats", "RunInPlace")
    assert result[1] in ("heuristic", "heuristic_override", "smooth")
    assert result[6] is None  # ml_probs should be None on failure
