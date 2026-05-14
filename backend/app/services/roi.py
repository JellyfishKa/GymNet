from datetime import datetime, timezone

from app.services.state import ZoneState


def update_zone_occupancy(zone: ZoneState, is_present: bool, exercise: str | None = None) -> ZoneState:
    now = datetime.now(timezone.utc)
    zone.updated_at = now

    if is_present:
        if zone.last_entered_at is None:
            zone.last_entered_at = now
        zone.current_exercise = exercise or zone.current_exercise
        zone.status = "Busy" if zone.dwell_seconds < 180 else "Crowded"
        zone.dwell_seconds = int((now - zone.last_entered_at).total_seconds())
    else:
        zone.status = "Free"
        zone.current_exercise = None
        zone.last_entered_at = None
        zone.dwell_seconds = 0
        zone.rep_count = 0
        zone.form_score = 100.0

    return zone
