from app.schemas.ingest import LandmarkInput
from app.services.landmark_sequence import (
    FEATURE_DIM,
    WINDOW_SIZE,
    get_ready_window,
    landmarks_to_vector,
    push_landmark_frame,
    clear_landmark_buffer,
)


def test_landmarks_to_vector_shape() -> None:
    landmarks = [LandmarkInput(name="nose", x=0.5, y=0.5)]
    vector = landmarks_to_vector(landmarks)
    assert len(vector) == FEATURE_DIM


def test_landmark_window_buffer() -> None:
    zone_id = "zone_buffer_test"
    clear_landmark_buffer(zone_id)
    frame = [LandmarkInput(name="nose", x=0.4, y=0.4)]
    for _ in range(WINDOW_SIZE):
        push_landmark_frame(zone_id, frame)
    window = get_ready_window(zone_id)
    assert window is not None
    assert len(window) == WINDOW_SIZE
    assert all(len(item) == FEATURE_DIM for item in window)
    clear_landmark_buffer(zone_id)
