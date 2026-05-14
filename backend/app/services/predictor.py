from statistics import mean


def predict_minutes_to_free(dwell_seconds: int, historical_dwell_seconds: list[int]) -> int:
    if not historical_dwell_seconds:
        baseline = 15 * 60
    else:
        baseline = int(mean(historical_dwell_seconds))

    remaining = max(0, baseline - dwell_seconds)
    return max(1, round(remaining / 60))
