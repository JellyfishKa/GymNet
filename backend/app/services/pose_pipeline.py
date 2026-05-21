import os
from dataclasses import dataclass

from app.services.exercise_profiles import (
    Landmarks,
    classify_heuristic,
    form_penalty_for_exercise,
    infer_phase_for_exercise,
)

PRESENCE_KEYPOINTS = ("nose", "left_hip", "right_hip")
DEFAULT_ROI_PRESENCE_RATIO = 0.35


@dataclass(slots=True)
class RoiRect:
    x_min: float
    y_min: float
    x_max: float
    y_max: float


def _roi_presence_ratio() -> float:
    raw = os.environ.get("GYMNET_ROI_PRESENCE_RATIO", str(DEFAULT_ROI_PRESENCE_RATIO))
    try:
        return float(raw)
    except ValueError:
        return DEFAULT_ROI_PRESENCE_RATIO


def _point_in_roi(point: tuple[float, float] | None, roi: RoiRect) -> bool:
    if point is None:
        return False
    x, y = point
    return roi.x_min <= x <= roi.x_max and roi.y_min <= y <= roi.y_max


def detect_presence_raw(landmarks: Landmarks, roi: RoiRect) -> bool:
    """Присутствие: не менее 2 из nose / left_hip / right_hip внутри ROI."""
    inside = sum(1 for name in PRESENCE_KEYPOINTS if _point_in_roi(landmarks.get(name), roi))
    required = max(2, int(len(PRESENCE_KEYPOINTS) * _roi_presence_ratio()))
    return inside >= min(required, len(PRESENCE_KEYPOINTS))


def detect_presence(
    landmarks: list[tuple[float, float]],
    roi: RoiRect,
    threshold: float = 0.25,
) -> bool:
    if not landmarks:
        return False
    inside = 0
    for x, y in landmarks:
        if roi.x_min <= x <= roi.x_max and roi.y_min <= y <= roi.y_max:
            inside += 1
    return inside / len(landmarks) >= threshold


def infer_phase(exercise: str, landmarks: Landmarks, zone_id: str = "default") -> str:
    return infer_phase_for_exercise(exercise, landmarks, zone_id)


def form_penalty(exercise: str, landmarks: Landmarks, phase: str = "Neutral") -> float:
    return form_penalty_for_exercise(exercise, landmarks, phase)
