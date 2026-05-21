from fastapi import APIRouter
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.services.runtime_store import history_store, zone_store
from app.services.session_repo import get_recent_sessions

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("/{zone_id}")
def get_session(zone_id: str) -> dict:
    zone = zone_store.get(zone_id)
    db: Session = SessionLocal()
    try:
        recent_sessions = get_recent_sessions(db, zone_id, limit=10)
    finally:
        db.close()

    sessions_payload = [
        {
            "id": row.id,
            "exercise": row.exercise,
            "dwell_seconds": row.dwell_seconds,
            "exercise_seconds": row.exercise_seconds,
            "rep_count": row.rep_count,
            "form_score": row.form_score,
            "created_at": row.created_at.isoformat(),
        }
        for row in recent_sessions
    ]

    if not zone:
        return {
            "zone_id": zone_id,
            "status": "Free",
            "history": history_store.get(zone_id, []),
            "recent_sessions": sessions_payload,
        }
    return {
        "zone": zone.to_dict(),
        "history": history_store.get(zone_id, []),
        "recent_sessions": sessions_payload,
    }
