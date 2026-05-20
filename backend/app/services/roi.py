from datetime import datetime, timezone

from app.services.state import ZoneState


def update_zone_occupancy(zone: ZoneState, is_present: bool, exercise: str | None = None) -> ZoneState:
    now = datetime.now(timezone.utc)
    zone.updated_at = now

    if is_present:
        if zone.last_entered_at is None:
            zone.last_entered_at = now
        zone.status = "Busy" if zone.dwell_seconds < 180 else "Crowded"
        zone.dwell_seconds = int((now - zone.last_entered_at).total_seconds())
        previous_exercise = zone.current_exercise
        active_exercise = exercise or previous_exercise
        if active_exercise:
            if previous_exercise != active_exercise:
                zone.current_exercise = active_exercise
                zone.exercise_started_at = now
                zone.exercise_seconds = 0
            elif zone.exercise_started_at is None:
                zone.current_exercise = active_exercise
                zone.exercise_started_at = now
                zone.exercise_seconds = 0
            else:
                zone.current_exercise = active_exercise
                zone.exercise_seconds = int((now - zone.exercise_started_at).total_seconds())

            if zone.total_exercise_started_at is None:
                zone.total_exercise_started_at = now
                zone.total_exercise_seconds = 0
            else:
                zone.total_exercise_seconds = int((now - zone.total_exercise_started_at).total_seconds())
        else:
            zone.current_exercise = None
            zone.exercise_started_at = None
            zone.exercise_seconds = 0
            zone.rep_count = 0
    else:
        zone.status = "Free"
        zone.current_exercise = None
        zone.exercise_started_at = None
        zone.exercise_seconds = 0
        zone.total_exercise_started_at = None
        zone.total_exercise_seconds = 0
        zone.last_entered_at = None
        zone.dwell_seconds = 0
        zone.rep_count = 0
        zone.total_rep_count = 0
        zone.form_score = 100.0

    return zone
