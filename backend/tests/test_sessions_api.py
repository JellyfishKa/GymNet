"""GET /api/sessions/{zone_id} — JSON с history из deque."""

from collections import deque

from fastapi.testclient import TestClient

from app.db.session import init_db
from app.main import app
from app.services.runtime_store import history_store


def test_sessions_returns_history_as_list():
    init_db()
    history_store["api_test_zone"] = deque([120, 90, 60], maxlen=50)
    client = TestClient(app)
    try:
        response = client.get("/api/sessions/api_test_zone")
        assert response.status_code == 200
        payload = response.json()
        assert payload["history"] == [120, 90, 60]
        assert isinstance(payload["history"], list)
        assert "recent_sessions" in payload
    finally:
        history_store.pop("api_test_zone", None)
