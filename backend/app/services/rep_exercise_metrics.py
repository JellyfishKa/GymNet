"""Метрики силовых упражнений: повторы + время (разный темп)."""

from __future__ import annotations

REP_BASED_EXERCISES = frozenset({"PushUps", "Squats"})


def is_rep_based(exercise: str | None) -> bool:
    return exercise in REP_BASED_EXERCISES


def rep_tempo_seconds(exercise_seconds: int, rep_count: int) -> float | None:
    if rep_count <= 0 or exercise_seconds <= 0:
        return None
    return round(exercise_seconds / rep_count, 1)


def estimate_dwell_at_completion(
    *,
    dwell_seconds: int,
    total_exercise_seconds: int,
    total_rep_count: int,
    mean_exercise_seconds: float,
    mean_rep_count: float,
) -> list[int]:
    """
    Оценки момента освобождения зоны (сек от входа).
    Для медленного темпа берём max(по времени, по повторам), не min.
    """
    estimates: list[int] = []

    if mean_exercise_seconds > 0:
        remaining_time = max(0, int(mean_exercise_seconds) - total_exercise_seconds)
        estimates.append(dwell_seconds + remaining_time)

    if mean_rep_count > 0:
        remaining_reps = max(0.0, mean_rep_count - total_rep_count)
        if total_rep_count > 0 and total_exercise_seconds > 0:
            rep_rate = total_rep_count / total_exercise_seconds
            if rep_rate > 0:
                estimates.append(dwell_seconds + int(remaining_reps / rep_rate))
        elif total_exercise_seconds > 0 and mean_exercise_seconds > 0:
            # Повторы ещё не детектятся — опираемся на профиль длительности.
            progress = min(1.0, total_exercise_seconds / mean_exercise_seconds)
            estimates.append(dwell_seconds + int(mean_exercise_seconds * (1.0 - progress)))

    return estimates
