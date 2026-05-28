import json
import math
from datetime import datetime
from pathlib import Path

_DATA_PATH = Path(__file__).parent / "occupancy_peak_factors.json"
_data: dict = {}


def _load() -> dict:
    global _data
    if not _data:
        _data = json.loads(_DATA_PATH.read_text())
    return _data


def peak_factor(hour: int, day_of_week: int) -> float:
    """Return normalized busyness factor [0,1] for this hour/day."""
    d = _load()
    key = f"{hour}_{day_of_week}"
    return d["peak_factors"].get(key, 0.5)


def mm1_wait_probability(
    *,
    historical_dwell_seconds: list[int],
    hour: int | None = None,
    day_of_week: int | None = None,
    wait_minutes: float = 5.0,
) -> float:
    """
    P(W > wait_minutes) via M/M/1 queue model.
    λ calibrated from data.csv peak factors. μ = 1 / mean_dwell_time.
    Returns probability in [0, 1]; 1.0 when ρ >= 1.
    """
    now = datetime.now()
    h = hour if hour is not None else now.hour
    dow = day_of_week if day_of_week is not None else now.weekday()

    if historical_dwell_seconds:
        mean_dwell = sum(historical_dwell_seconds) / len(historical_dwell_seconds)
    else:
        mean_dwell = 15 * 60
    mu = 1.0 / max(mean_dwell, 60)

    pf = peak_factor(h, dow)
    lam = mu * pf
    rho = lam / mu  # = pf

    if rho >= 1.0:
        return 1.0

    t_seconds = wait_minutes * 60
    prob = rho * math.exp(-mu * (1 - rho) * t_seconds)
    return round(min(max(prob, 0.0), 1.0), 4)
