from fastapi.testclient import TestClient

from app.main import app


def test_live_ingest() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/live/ingest",
        json={
            "zone_id": "treadmill_zone_1",
            "treadmill_zone": True,
            "roi": {"x_min": 0.2, "y_min": 0.2, "x_max": 0.8, "y_max": 0.9},
            "landmarks": [
                {"name": "left_shoulder", "x": 0.4, "y": 0.4},
                {"name": "right_shoulder", "x": 0.6, "y": 0.4},
                {"name": "left_hip", "x": 0.45, "y": 0.6},
                {"name": "right_hip", "x": 0.55, "y": 0.6},
            ],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["exercise"] == "RunInPlace"
    assert payload["is_present"] is True
