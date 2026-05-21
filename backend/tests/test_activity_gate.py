import numpy as np

from app.services.activity_gate import (
    detect_idle_standing,
    detect_passing_by,
    is_meaningful_activity,
)
from app.services.landmark_sequence import FEATURE_DIM, LANDMARK_NAMES


def _frame(
    hip_x: float = 0.5,
    hip_y: float = 0.55,
    hip_dy: float = 0.0,
    ankle_dy: float = 0.0,
) -> list[float]:
    vec = [0.0] * FEATURE_DIM
    for name, x_off in (
        ("left_hip", 0),
        ("right_hip", 0.02),
        ("left_ankle", 0),
        ("right_ankle", 0.02),
        ("left_knee", 0),
        ("left_shoulder", 0),
    ):
        idx = LANDMARK_NAMES.index(name) * 3
        vec[idx] = hip_x + x_off
        vec[idx + 1] = hip_y + (ankle_dy if "ankle" in name else hip_dy if "hip" in name else 0.0)
    return vec


def _window_static(n: int = 10) -> list[list[float]]:
    return [_frame() for _ in range(n)]


def _window_passing(n: int = 10) -> list[list[float]]:
    return [_frame(hip_x=0.3 + i * 0.04) for i in range(n)]


def _window_exercise(n: int = 10) -> list[list[float]]:
    frames = []
    for i in range(n):
        dy = 0.04 * np.sin(2 * np.pi * i / 4)
        frames.append(_frame(hip_y=0.55 + dy, hip_dy=dy, ankle_dy=dy))
    return frames


def test_idle_standing_rejected() -> None:
    window = _window_static()
    assert detect_idle_standing(window) is True
    active, reason = is_meaningful_activity(window)
    assert active is False
    assert reason == "idle"


def test_passing_rejected() -> None:
    window = _window_passing()
    assert detect_passing_by(window) is True
    active, reason = is_meaningful_activity(window)
    assert active is False
    assert reason == "passing"


def test_exercise_motion_accepted() -> None:
    window = _window_exercise()
    active, reason = is_meaningful_activity(window)
    assert active is True
    assert reason is None
