import asyncio
import logging
import os

from fastapi import APIRouter, HTTPException, Query

from app.schemas.ingest import PoseIngestRequest, PoseIngestResponse
from app.services.ingest_runner import run_pose_ingest_async
from app.services.pose_ingest import reset_live_tracking

logger = logging.getLogger(__name__)

INGEST_HTTP_TIMEOUT_SEC = float(os.getenv("GYMNET_INGEST_HTTP_TIMEOUT_SEC", "25"))

router = APIRouter(prefix="/live", tags=["live-ingest"])


@router.post("/reset-tracking")
def reset_tracking(zone_id: str = Query(default="treadmill_zone_1")) -> dict[str, str]:
    """Сброс presence/буфера landmarks после выключения камеры."""
    reset_live_tracking(zone_id)
    return {"zone_id": zone_id, "status": "reset"}


@router.post("/ingest", response_model=PoseIngestResponse)
async def ingest_pose(payload: PoseIngestRequest) -> PoseIngestResponse:
    try:
        return await run_pose_ingest_async(payload, timeout_sec=INGEST_HTTP_TIMEOUT_SEC)
    except asyncio.TimeoutError:
        logger.warning("HTTP ingest timeout (%.1fs) zone=%s", INGEST_HTTP_TIMEOUT_SEC, payload.zone_id)
        raise HTTPException(status_code=503, detail="ingest timeout") from None
    except Exception as exc:
        logger.exception("ingest failed for zone %s", payload.zone_id)
        raise HTTPException(status_code=500, detail=f"ingest: {exc}") from exc
