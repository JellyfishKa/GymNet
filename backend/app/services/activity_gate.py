"""Отсекаем «пустое» присутствие: стоят в кадре или проходят мимо."""

from __future__ import annotations

import os
from typing import Sequence

import numpy as np

from app.services.landmark_sequence import FEATURE_DIM, LANDMARK_NAMES, WINDOW_SIZE

# Индексы x,y в плоском векторе кадра [99]
_HIP_L = LANDMARK_NAMES.index("left_hip") * 3
_HIP_R = LANDMARK_NAMES.index("right_hip") * 3
_ANKLE_L = LANDMARK_NAMES.index("left_ankle") * 3
_ANKLE_R = LANDMARK_NAMES.index("right_ankle") * 3
_KNEE_L = LANDMARK_NAMES.index("left_knee") * 3
_SHOULDER_L = LANDMARK_NAMES.index("left_shoulder") * 3

DEFAULT_MIN_HIP_Y_STD = 0.012
DEFAULT_MIN_ANKLE_Y_STD = 0.01
DEFAULT_MAX_HIP_X_RANGE = 0.14
DEFAULT_MIN_FRAMES = 5

_ELBOW_L = LANDMARK_NAMES.index("left_elbow") * 3
_ELBOW_R = LANDMARK_NAMES.index("right_elbow") * 3
_KNEE_R = LANDMARK_NAMES.index("right_knee") * 3


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _series_from_window(window: Sequence[Sequence[float]]) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    hip_x: list[float] = []
    hip_y: list[float] = []
    ankle_y: list[float] = []
    knee_y: list[float] = []

    for frame in window:
        if len(frame) != FEATURE_DIM:
            continue
        lx, ly = float(frame[_HIP_L]), float(frame[_HIP_L + 1])
        rx, ry = float(frame[_HIP_R]), float(frame[_HIP_R + 1])
        hip_x.append((lx + rx) / 2.0)
        hip_y.append((ly + ry) / 2.0)
        al_y = float(frame[_ANKLE_L + 1])
        ar_y = float(frame[_ANKLE_R + 1])
        ankle_y.append((al_y + ar_y) / 2.0)
        knee_y.append(float(frame[_KNEE_L + 1]))

    return (
        np.asarray(hip_x, dtype=np.float32),
        np.asarray(hip_y, dtype=np.float32),
        np.asarray(ankle_y, dtype=np.float32),
        np.asarray(knee_y, dtype=np.float32),
    )


def detect_passing_by(window: Sequence[Sequence[float]]) -> bool:
    """Сильный сдвиг по X за окно — человек проходит через кадр."""
    hip_x, _, _, _ = _series_from_window(window)
    if hip_x.size < 4:
        return False
    x_range = float(np.max(hip_x) - np.min(hip_x))
    return x_range >= _env_float("GYMNET_ACTIVITY_MAX_HIP_X_RANGE", DEFAULT_MAX_HIP_X_RANGE)


def activity_min_frames() -> int:
    return _env_int("GYMNET_ACTIVITY_MIN_FRAMES", DEFAULT_MIN_FRAMES)


def detect_rep_motion(window: Sequence[Sequence[float]]) -> bool:
    """Отжимания/приседания: заметная амплитуда локтей или колен в окне."""
    elbow_y: list[float] = []
    knee_y: list[float] = []
    for frame in window:
        if len(frame) != FEATURE_DIM:
            continue
        elbow_y.append((float(frame[_ELBOW_L + 1]) + float(frame[_ELBOW_R + 1])) / 2.0)
        knee_y.append((float(frame[_KNEE_L + 1]) + float(frame[_KNEE_R + 1])) / 2.0)
    if len(elbow_y) < 4:
        return False
    elbow_std = float(np.std(elbow_y))
    knee_std = float(np.std(knee_y))
    elbow_rng = float(max(elbow_y) - min(elbow_y))
    knee_rng = float(max(knee_y) - min(knee_y))
    return (
        elbow_std >= 0.006
        or knee_std >= 0.006
        or elbow_rng >= 0.018
        or knee_rng >= 0.018
    )


def detect_idle_standing(window: Sequence[Sequence[float]]) -> bool:
    """Вертикальная поза без заметной амплитуды движения."""
    hip_x, hip_y, ankle_y, knee_y = _series_from_window(window)
    if hip_y.size < 4:
        return True

    hip_y_std = float(np.std(hip_y))
    ankle_y_std = float(np.std(ankle_y))
    knee_y_std = float(np.std(knee_y))

    min_hip_std = _env_float("GYMNET_ACTIVITY_MIN_HIP_Y_STD", DEFAULT_MIN_HIP_Y_STD)
    min_ankle_std = _env_float("GYMNET_ACTIVITY_MIN_ANKLE_Y_STD", DEFAULT_MIN_ANKLE_Y_STD)

    if hip_y_std >= min_hip_std or ankle_y_std >= min_ankle_std or knee_y_std >= min_hip_std:
        return False

    # Дополнительно: почти нет смещения по X (стоит на месте, не идёт)
    if hip_x.size >= 4:
        x_range = float(np.max(hip_x) - np.min(hip_x))
        if x_range > _env_float("GYMNET_ACTIVITY_MAX_STAND_X_RANGE", 0.06):
            return False

    return True


def is_meaningful_activity(window: Sequence[Sequence[float]] | None) -> tuple[bool, str | None]:
    """
    True — занимается в зоне; False — стоит/проходит (не засчитываем).
    Возвращает (активен, причина отклонения для UI).
    """
    min_frames = activity_min_frames()
    if window is None or len(window) < min_frames:
        return False, "warming_up"

    if detect_rep_motion(window):
        return True, None

    if detect_passing_by(window):
        return False, "passing"

    if detect_idle_standing(window):
        return False, "idle"

    return True, None
