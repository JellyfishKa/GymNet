import json
from pathlib import Path

_PATH = Path(__file__).parent / "calories_per_exercise.json"
_rates: dict[str, float] = {}


def _load() -> dict[str, float]:
    global _rates
    if not _rates:
        data = json.loads(_PATH.read_text())
        _rates = {k: v for k, v in data.items() if not k.startswith("_")}
    return _rates


def estimate_calories(exercise: str | None, exercise_seconds: int) -> float | None:
    """Return estimated kcal burned. None if exercise unknown or no time."""
    if not exercise or exercise_seconds <= 0:
        return None
    rates = _load()
    cal_per_hour = rates.get(exercise)
    if cal_per_hour is None:
        return None
    return round(cal_per_hour * exercise_seconds / 3600, 1)
