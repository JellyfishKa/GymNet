import asyncio
import logging
import os

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from app.schemas.ingest import PoseIngestRequest
from app.schemas.live import LiveUpdateRequest
from app.services.live_update import apply_live_update
from app.services.ingest_runner import IngestBusyError, run_pose_ingest_async

router = APIRouter(tags=["live"])
logger = logging.getLogger(__name__)

INGEST_WS_TIMEOUT_SEC = float(os.getenv("GYMNET_INGEST_HTTP_TIMEOUT_SEC", "8"))
INGEST_WS_COALESCE_SEC = float(os.getenv("GYMNET_INGEST_WS_COALESCE_SEC", "0.06"))


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
                result = await asyncio.to_thread(apply_live_update, incoming)
            except Exception:
                logger.exception("Ошибка live-обновления: zone=%s", payload.get("zone_id"))
                continue

            await websocket.send_json(result)
    except WebSocketDisconnect:
        return


@router.websocket("/ws/live/ingest")
async def websocket_live_ingest(websocket: WebSocket) -> None:
    """Камера: обрабатываем только последний кадр из очереди (без 25+ с накопления)."""
    await websocket.accept()
    lock = asyncio.Lock()
    latest_raw: dict | None = None
    pending = asyncio.Event()
    disconnected = asyncio.Event()

    async def reader() -> None:
        nonlocal latest_raw
        try:
            while True:
                raw = await websocket.receive_json()
                if not isinstance(raw, dict):
                    continue
                async with lock:
                    latest_raw = raw
                pending.set()
        except WebSocketDisconnect:
            disconnected.set()
            pending.set()

    async def worker() -> None:
        nonlocal latest_raw
        while not disconnected.is_set():
            await pending.wait()
            await asyncio.sleep(INGEST_WS_COALESCE_SEC)
            async with lock:
                snap = latest_raw
                latest_raw = None
            pending.clear()
            while True:
                await asyncio.sleep(0.02)
                async with lock:
                    if latest_raw is None:
                        break
                    snap = latest_raw
                    latest_raw = None
            if snap is None:
                continue

            try:
                payload = PoseIngestRequest.model_validate(
                    {k: v for k, v in snap.items() if k != "seq"}
                )
            except ValidationError as exc:
                logger.warning("Невалидный WS ingest: %s", exc)
                continue

            try:
                result = await run_pose_ingest_async(payload, timeout_sec=INGEST_WS_TIMEOUT_SEC)
                await websocket.send_json(result.model_dump(mode="json"))
            except IngestBusyError:
                # Не отвечаем клиенту: кадр переобработаем, когда слот освободится.
                async with lock:
                    latest_raw = snap
                pending.set()
                await asyncio.sleep(0.08)
                continue
            except asyncio.TimeoutError:
                logger.warning("WS ingest timeout zone=%s", payload.zone_id)
                try:
                    await websocket.send_json({"error": "timeout"})
                except Exception:
                    return
            except Exception:
                logger.exception("WS ingest error zone=%s", payload.zone_id)
                try:
                    await websocket.send_json({"error": "internal"})
                except Exception:
                    return

    try:
        await asyncio.gather(reader(), worker())
    except WebSocketDisconnect:
        return
