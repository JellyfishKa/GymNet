import json
import os
from pathlib import Path
from threading import Lock


PROFILE_PATH = Path(
    os.getenv(
        "GYMNET_ONLINE_PROFILE_PATH",
        str(Path(__file__).resolve().parents[3] / "ml" / "experiments" / "online_profile.json"),
    )
)
REP_BASED_EXERCISES = {"PushUps", "Squats", "ResistanceBand"}
_lock = Lock()
_profile: dict[str, dict[str, float]] | None = None


def _load_profile() -> dict[str, dict[str, float]]:
    global _profile
    with _lock:
        if _profile is not None:
            return _profile
        if PROFILE_PATH.exists():
            _profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
        else:
            _profile = {}
        return _profile


def _save_profile(profile: dict[str, dict[str, float]]) -> None:
    PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROFILE_PATH.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")


def _key(zone_id: str, exercise: str) -> str:
    return f"{zone_id}::{exercise}"


def update_online_profile(
    *,
    zone_id: str,
    exercise: str,
    dwell_seconds: int,
    total_exercise_seconds: int,
    total_rep_count: int,
) -> None:
    profile = _load_profile()
    with _lock:
        key = _key(zone_id, exercise)
        row = profile.get(key) or {
            "samples": 0.0,
            "mean_dwell_seconds": 0.0,
            "mean_total_exercise_seconds": 0.0,
            "mean_total_rep_count": 0.0,
        }
        samples = row["samples"] + 1.0
        row["mean_dwell_seconds"] = row["mean_dwell_seconds"] + (dwell_seconds - row["mean_dwell_seconds"]) / samples
        row["mean_total_exercise_seconds"] = row["mean_total_exercise_seconds"] + (
            total_exercise_seconds - row["mean_total_exercise_seconds"]
        ) / samples
        row["mean_total_rep_count"] = row["mean_total_rep_count"] + (
            total_rep_count - row["mean_total_rep_count"]
        ) / samples
        row["samples"] = samples
        profile[key] = row
        _save_profile(profile)


def predict_minutes_to_free_online(
    *,
    zone_id: str,
    exercise: str | None,
    dwell_seconds: int,
    exercise_seconds: int,
    total_rep_count: int,
    historical_dwell_seconds: list[int],
) -> int:
    baseline = 15 * 60
    if historical_dwell_seconds:
        baseline = int(sum(historical_dwell_seconds) / len(historical_dwell_seconds))

    if not exercise:
        remaining = max(0, baseline - dwell_seconds)
        return max(1, round(remaining / 60))

    profile = _load_profile()
    row = profile.get(_key(zone_id, exercise))
    if row:
        baseline = int(0.5 * baseline + 0.5 * row["mean_dwell_seconds"])

        mean_exercise_seconds = row.get("mean_total_exercise_seconds", 0.0)
        if mean_exercise_seconds > 0:
            expected_from_exercise_clock = dwell_seconds + max(0, int(mean_exercise_seconds - exercise_seconds))
            baseline = int(0.6 * baseline + 0.4 * expected_from_exercise_clock)

        mean_reps = row.get("mean_total_rep_count", 0.0)
        if exercise in REP_BASED_EXERCISES and mean_reps > 0 and exercise_seconds > 0 and total_rep_count >= 0:
            rep_rate = total_rep_count / max(exercise_seconds, 1)
            if rep_rate > 0:
                remaining_reps = max(0.0, mean_reps - total_rep_count)
                expected_from_reps = dwell_seconds + int(remaining_reps / rep_rate)
                baseline = int(0.5 * baseline + 0.5 * expected_from_reps)

    remaining = max(0, baseline - dwell_seconds)
    return max(1, round(remaining / 60))
