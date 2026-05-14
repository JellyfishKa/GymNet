from fastapi import APIRouter

from app.services.predictor import predict_minutes_to_free
from app.services.runtime_store import history_store, zone_store

router = APIRouter(prefix="/predictions", tags=["predictions"])


@router.get("/{zone_id}")
def get_prediction(zone_id: str) -> dict:
    zone = zone_store.get(zone_id)
    dwell = zone.dwell_seconds if zone else 0
    history = history_store.get(zone_id, [])
    minutes = predict_minutes_to_free(dwell, history)
    return {"zone_id": zone_id, "minutes_to_free": minutes}
