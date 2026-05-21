import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from app.schemas.live import LiveUpdateRequest
from app.services.live_update import apply_live_update

router = APIRouter(tags=["live"])
logger = logging.getLogger(__name__)


@router.websocket("/ws/live")
async def websocket_live(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            payload = await websocket.receive_json()
            try:
                incoming = LiveUpdateRequest.model_validate(payload)
            except ValidationError as exc:
                logger.warning("Невалидный WS payload: %s", exc)
                continue

            try:
                result = apply_live_update(incoming)
            except Exception:
                logger.exception("Ошибка live-обновления: zone=%s", payload.get("zone_id"))
                continue

            await websocket.send_json(result)
    except WebSocketDisconnect:
        return
