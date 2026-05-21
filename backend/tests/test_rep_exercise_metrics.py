from app.services.online_learning import predict_minutes_to_free_online
from app.services.rep_exercise_metrics import estimate_dwell_at_completion, rep_tempo_seconds


def test_rep_tempo() -> None:
    assert rep_tempo_seconds(60, 10) == 6.0
    assert rep_tempo_seconds(0, 5) is None


def test_slow_tempo_uses_time_not_only_reps() -> None:
    # Много времени, мало повторов — оценка по времени длиннее, чем по быстрому rep_rate.
    estimates = estimate_dwell_at_completion(
        dwell_seconds=120,
        total_exercise_seconds=90,
        total_rep_count=2,
        mean_exercise_seconds=180.0,
        mean_rep_count=10.0,
    )
    assert estimates
    time_based = max(estimates)
    assert time_based >= 120 + (180 - 90)


def test_prediction_rep_exercise_max_of_time_and_reps() -> None:
    minutes = predict_minutes_to_free_online(
        zone_id="z1",
        exercise="PushUps",
        dwell_seconds=60,
        exercise_seconds=60,
        total_exercise_seconds=60,
        total_rep_count=2,
        historical_dwell_seconds=[600],
    )
    assert minutes >= 1
