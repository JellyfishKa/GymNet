from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.schemas.live import LiveUpdateRequest
from app.services.roi import update_zone_occupancy
from app.services.runtime_store import history_store, sadla_store, zone_store
from app.services.sadla import SadlaState
from app.services.state import ZoneState

router = APIRouter(tags=["live"])


@router.websocket("/ws/live")
async def websocket_live(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            payload = await websocket.receive_json()
            incoming = LiveUpdateRequest.model_validate(payload)

            zone = zone_store.get(incoming.zone_id) or ZoneState(zone_id=incoming.zone_id)
            previous_dwell = zone.dwell_seconds
            zone = update_zone_occupancy(zone, incoming.is_present, incoming.exercise)

            sadla = sadla_store.get(incoming.zone_id) or SadlaState()
            if incoming.phase:
                sadla.apply_phase(incoming.phase)
            zone.rep_count = sadla.reps
            zone.form_score = max(0.0, zone.form_score - incoming.form_penalty)

            # When user leaves zone, keep dwell in history for later ETA prediction.
            if not incoming.is_present and previous_dwell > 0:
                history_store.setdefault(incoming.zone_id, []).append(previous_dwell)

            zone_store[incoming.zone_id] = zone
            sadla_store[incoming.zone_id] = sadla

            await websocket.send_json(
                {
                    "zone": zone.to_dict(),
                    "sadla_phase": sadla.current_phase,
                    "supported_exercises": [
                        "ResistanceBand",
                        "PushUps",
                        "Squats",
                        "RunInPlace",
                    ],
                }
            )
    except WebSocketDisconnect:
        return
