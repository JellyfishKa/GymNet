from statistics import mean

from app.services.online_learning import predict_minutes_to_free_online


def predict_minutes_to_free(dwell_seconds: int, historical_dwell_seconds: list[int]) -> int:
    if not historical_dwell_seconds:
        baseline = 15 * 60
    else:
        baseline = int(mean(historical_dwell_seconds))

    remaining = max(0, baseline - dwell_seconds)
    return max(1, round(remaining / 60))


def predict_minutes_to_free_adaptive(
    *,
    zone_id: str,
    exercise: str | None,
    dwell_seconds: int,
    exercise_seconds: int,
    total_exercise_seconds: int,
    total_rep_count: int,
    historical_dwell_seconds: list[int],
) -> int:
    return predict_minutes_to_free_online(
        zone_id=zone_id,
        exercise=exercise,
        dwell_seconds=dwell_seconds,
        exercise_seconds=exercise_seconds,
        total_exercise_seconds=total_exercise_seconds,
        total_rep_count=total_rep_count,
        historical_dwell_seconds=historical_dwell_seconds,
    )
