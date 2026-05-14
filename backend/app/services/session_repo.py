from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.models import ZoneSession


def save_zone_session(
    db: Session,
    *,
    zone_id: str,
    exercise: str,
    dwell_seconds: int,
    rep_count: int,
    form_score: float,
) -> ZoneSession:
    row = ZoneSession(
        zone_id=zone_id,
        exercise=exercise,
        dwell_seconds=dwell_seconds,
        rep_count=rep_count,
        form_score=form_score,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_recent_dwell_history(db: Session, zone_id: str, limit: int = 20) -> list[int]:
    query = (
        select(ZoneSession.dwell_seconds)
        .where(ZoneSession.zone_id == zone_id)
        .order_by(desc(ZoneSession.created_at))
        .limit(limit)
    )
    rows = db.execute(query).all()
    return [row[0] for row in rows]
