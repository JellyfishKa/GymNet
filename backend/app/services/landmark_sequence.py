"""Буфер кадров pose для формирования окон [13, 99] под CNN-ResBiGRU."""

from __future__ import annotations

from collections import deque

from app.schemas.ingest import LandmarkInput
from app.services.zone_locks import zone_lock

# Порядок точек совпадает с MediaPipe Pose (33 landmarks).
LANDMARK_NAMES = [
    "nose",
    "left_eye_inner",
    "left_eye",
    "left_eye_outer",
    "right_eye_inner",
    "right_eye",
    "right_eye_outer",
    "left_ear",
    "right_ear",
    "mouth_left",
    "mouth_right",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_pinky",
    "right_pinky",
    "left_index",
    "right_index",
    "left_thumb",
    "right_thumb",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
    "left_heel",
    "right_heel",
    "left_foot_index",
    "right_foot_index",
]

WINDOW_SIZE = 13
FEATURE_DIM = 99

_buffers: dict[str, deque[list[float]]] = {}


def landmarks_to_vector(landmarks: list[LandmarkInput]) -> list[float]:
    by_name = {lm.name: lm for lm in landmarks}
    vector: list[float] = []
    for name in LANDMARK_NAMES:
        point = by_name.get(name)
        if point is None:
            vector.extend([0.0, 0.0, 0.0])
        else:
            vector.extend([float(point.x), float(point.y), 0.0])
    if len(vector) != FEATURE_DIM:
        raise ValueError(f"Ожидался вектор длины {FEATURE_DIM}, получено {len(vector)}")
    return vector


def push_landmark_frame(zone_id: str, landmarks: list[LandmarkInput]) -> None:
    if not landmarks:
        return
    frame = landmarks_to_vector(landmarks)
    with zone_lock(zone_id):
        buffer = _buffers.setdefault(zone_id, deque(maxlen=WINDOW_SIZE))
        buffer.append(frame)


def get_window_frames(zone_id: str, min_frames: int = 1) -> list[list[float]] | None:
    """Частичное окно для activity-gate до накопления 13 кадров под ML."""
    if min_frames < 1:
        min_frames = 1
    with zone_lock(zone_id):
        buffer = _buffers.get(zone_id)
        if buffer is None or len(buffer) < min_frames:
            return None
        return [list(item) for item in buffer]


def get_ready_window(zone_id: str) -> list[list[float]] | None:
    return get_window_frames(zone_id, WINDOW_SIZE)


def clear_landmark_buffer(zone_id: str) -> None:
    with zone_lock(zone_id):
        _buffers.pop(zone_id, None)
