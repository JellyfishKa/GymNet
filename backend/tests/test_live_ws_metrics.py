from fastapi.testclient import TestClient

from app.main import app


def test_websocket_counts_reps_only_for_rep_exercises() -> None:
    client = TestClient(app)
    with client.websocket_connect("/ws/live") as ws:
        base_payload = {
            "zone_id": "zone_rep_test",
            "is_present": True,
            "exercise": "PushUps",
            "form_penalty": 0.0,
        }
        phases = ["TransitionDown", "Bottom", "TransitionUp", "Standing"]

        last = None
        for phase in phases:
            ws.send_json({**base_payload, "phase": phase})
            last = ws.receive_json()

        assert last is not None
        assert last["zone"]["current_exercise"] == "PushUps"
        assert last["zone"]["rep_count"] == 1
        assert last["zone"]["total_rep_count"] == 1
        assert "exercise_seconds" in last["zone"]
        assert "total_exercise_seconds" in last["zone"]
        assert last["minutes_to_free"] >= 1

        ws.send_json(
            {
                "zone_id": "zone_rep_test",
                "is_present": True,
                "exercise": "RunInPlace",
                "phase": "Standing",
                "form_penalty": 0.0,
            }
        )
        switched = ws.receive_json()
        assert switched["zone"]["current_exercise"] == "RunInPlace"
        assert switched["zone"]["rep_count"] == 0
        assert switched["zone"]["total_rep_count"] == 1
