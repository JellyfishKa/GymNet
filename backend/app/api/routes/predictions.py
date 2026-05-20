from fastapi import APIRouter
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.services.predictor import predict_minutes_to_free_adaptive
from app.services.runtime_store import history_store, zone_store
from app.services.session_repo import get_recent_dwell_history

router = APIRouter(prefix="/predictions", tags=["predictions"])


@router.get("/{zone_id}")
def get_prediction(zone_id: str) -> dict:
    zone = zone_store.get(zone_id)
    dwell = zone.dwell_seconds if zone else 0
    exercise = zone.current_exercise if zone else None
    exercise_seconds = zone.exercise_seconds if zone else 0
    total_rep_count = zone.total_rep_count if zone else 0
    history = history_store.get(zone_id, [])
    if not history:
        db: Session = SessionLocal()
        try:
            history = get_recent_dwell_history(db, zone_id, limit=20)
        finally:
            db.close()
    minutes = predict_minutes_to_free_adaptive(
        zone_id=zone_id,
        exercise=exercise,
        dwell_seconds=dwell,
        exercise_seconds=exercise_seconds,
        total_rep_count=total_rep_count,
        historical_dwell_seconds=history,
    )
    return {"zone_id": zone_id, "minutes_to_free": minutes, "mode": "online_adaptive"}
