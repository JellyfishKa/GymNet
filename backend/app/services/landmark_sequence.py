"""Буфер кадров pose для формирования окон [13, 99] под CNN-ResBiGRU."""

from __future__ import annotations

from collections import deque

from app.schemas.ingest import LandmarkInput

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
    buffer = _buffers.setdefault(zone_id, deque(maxlen=WINDOW_SIZE))
    buffer.append(frame)


def get_ready_window(zone_id: str) -> list[list[float]] | None:
    buffer = _buffers.get(zone_id)
    if buffer is None or len(buffer) < WINDOW_SIZE:
        return None
    return [list(frame) for frame in buffer]


def clear_landmark_buffer(zone_id: str) -> None:
    _buffers.pop(zone_id, None)
