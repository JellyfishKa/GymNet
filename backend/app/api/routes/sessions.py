from fastapi import APIRouter

from app.services.runtime_store import history_store, zone_store

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("/{zone_id}")
def get_session(zone_id: str) -> dict:
    zone = zone_store.get(zone_id)
    if not zone:
        return {"zone_id": zone_id, "status": "Free", "history": history_store.get(zone_id, [])}
    return {"zone": zone.to_dict(), "history": history_store.get(zone_id, [])}
