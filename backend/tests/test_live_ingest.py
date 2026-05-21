import math

from fastapi.testclient import TestClient

from app.main import app
from app.services.zone_presence import reset_zone_presence


def _ingest_body(frame_idx: int) -> dict:
    dy = 0.04 * math.sin(2 * math.pi * frame_idx / 4)
    hip_y = 0.55 + dy
    return {
        "zone_id": "test_zone_presence",
        "roi": {"x_min": 0.2, "y_min": 0.2, "x_max": 0.8, "y_max": 0.9},
        "landmarks": [
            {"name": "nose", "x": 0.5, "y": 0.35},
            {"name": "left_hip", "x": 0.45, "y": hip_y},
            {"name": "right_hip", "x": 0.55, "y": hip_y + 0.01},
            {"name": "left_ankle", "x": 0.45, "y": 0.82 + dy},
            {"name": "right_ankle", "x": 0.55, "y": 0.82 + dy},
            {"name": "left_knee", "x": 0.45, "y": 0.65 + dy * 0.5},
            {"name": "left_shoulder", "x": 0.4, "y": 0.4},
            {"name": "left_elbow", "x": 0.35, "y": 0.55 + dy},
            {"name": "left_wrist", "x": 0.32, "y": 0.7 + dy},
        ],
    }


def test_live_ingest_presence_and_zone_snapshot() -> None:
    reset_zone_presence("test_zone_presence")
    client = TestClient(app)

    last_payload = None
    for frame in range(16):
        response = client.post("/api/live/ingest", json=_ingest_body(frame))
        assert response.status_code == 200
        last_payload = response.json()

    assert last_payload is not None
    assert last_payload["is_present"] is True
    assert last_payload["in_roi"] is True
    assert last_payload["zone"] is not None
    assert last_payload["zone"]["zone_id"] == "test_zone_presence"
    assert last_payload["exercise"] in ("PushUps", "Squats", "RunInPlace")
    assert "ResistanceBand" not in (last_payload.get("supported_exercises") or [])


def test_idle_in_roi_not_counted() -> None:
    reset_zone_presence("test_zone_idle")
    client = TestClient(app)
    static = {
        "zone_id": "test_zone_idle",
        "roi": {"x_min": 0.2, "y_min": 0.2, "x_max": 0.8, "y_max": 0.9},
        "landmarks": [
            {"name": "nose", "x": 0.5, "y": 0.35},
            {"name": "left_hip", "x": 0.45, "y": 0.55},
            {"name": "right_hip", "x": 0.55, "y": 0.55},
            {"name": "left_ankle", "x": 0.45, "y": 0.82},
            {"name": "right_ankle", "x": 0.55, "y": 0.82},
            {"name": "left_knee", "x": 0.45, "y": 0.65},
        ],
    }
    last = None
    for _ in range(14):
        response = client.post("/api/live/ingest", json=static)
        assert response.status_code == 200
        last = response.json()

    assert last is not None
    assert last["in_roi"] is True
    assert last["is_present"] is False
    assert last["activity_rejected"] == "idle"
