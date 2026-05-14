from fastapi import APIRouter
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.services.predictor import predict_minutes_to_free
from app.services.runtime_store import history_store, zone_store
from app.services.session_repo import get_recent_dwell_history

router = APIRouter(prefix="/predictions", tags=["predictions"])


@router.get("/{zone_id}")
def get_prediction(zone_id: str) -> dict:
    zone = zone_store.get(zone_id)
    dwell = zone.dwell_seconds if zone else 0
    history = history_store.get(zone_id, [])
    if not history:
        db: Session = SessionLocal()
        try:
            history = get_recent_dwell_history(db, zone_id, limit=20)
        finally:
            db.close()
    minutes = predict_minutes_to_free(dwell, history)
    return {"zone_id": zone_id, "minutes_to_free": minutes}
