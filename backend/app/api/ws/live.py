from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.schemas.live import LiveUpdateRequest
from app.services.landmark_sequence import clear_landmark_buffer, get_ready_window
from app.services.online_learning import update_online_profile
from app.services.predictor import predict_minutes_to_free_adaptive
from app.services.roi import update_zone_occupancy
from app.services.runtime_store import history_store, sadla_store, zone_store
from app.services.sadla import SadlaState
from app.services.session_repo import save_zone_session
from app.services.state import ZoneState
from app.services.training_data_sink import (
    append_completed_session_sample,
    append_live_training_window,
)

router = APIRouter(tags=["live"])
REP_BASED_EXERCISES = {"PushUps", "Squats", "ResistanceBand"}


@router.websocket("/ws/live")
async def websocket_live(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            payload = await websocket.receive_json()
            incoming = LiveUpdateRequest.model_validate(payload)

            zone = zone_store.get(incoming.zone_id) or ZoneState(zone_id=incoming.zone_id)
            previous_dwell = zone.dwell_seconds
            previous_exercise = zone.current_exercise
            previous_total_rep_count = zone.total_rep_count
            previous_total_exercise_seconds = zone.total_exercise_seconds
            previous_form_score = zone.form_score
            zone = update_zone_occupancy(zone, incoming.is_present, incoming.exercise)

            sadla = sadla_store.get(incoming.zone_id) or SadlaState()
            if zone.current_exercise != previous_exercise and zone.current_exercise in REP_BASED_EXERCISES:
                sadla = SadlaState()

            is_rep_exercise = zone.current_exercise in REP_BASED_EXERCISES
            previous_current_rep = zone.rep_count
            if incoming.phase and is_rep_exercise:
                sadla.apply_phase(incoming.phase)
            zone.rep_count = sadla.reps if is_rep_exercise else 0
            rep_delta = max(0, zone.rep_count - previous_current_rep) if is_rep_exercise else 0
            zone.total_rep_count = previous_total_rep_count + rep_delta
            zone.form_score = max(0.0, zone.form_score - incoming.form_penalty)

            # Когда пользователь покидает зону, сохраняем длительность
            # для последующего прогноза времени освобождения.
            if not incoming.is_present and previous_dwell > 0:
                history_store.setdefault(incoming.zone_id, []).append(previous_dwell)
                db: Session = SessionLocal()
                try:
                    save_zone_session(
                        db,
                        zone_id=incoming.zone_id,
                        exercise=previous_exercise or "Неизвестно",
                        dwell_seconds=previous_dwell,
                        rep_count=previous_total_rep_count,
                        form_score=previous_form_score,
                    )
                finally:
                    db.close()
                if previous_exercise:
                    window = get_ready_window(incoming.zone_id)
                    if window is not None:
                        append_live_training_window(
                            zone_id=incoming.zone_id,
                            exercise=previous_exercise,
                            window=window,
                            force=True,
                        )
                    clear_landmark_buffer(incoming.zone_id)
                    update_online_profile(
                        zone_id=incoming.zone_id,
                        exercise=previous_exercise,
                        dwell_seconds=previous_dwell,
                        total_exercise_seconds=previous_total_exercise_seconds,
                        total_rep_count=previous_total_rep_count,
                    )
                    append_completed_session_sample(
                        zone_id=incoming.zone_id,
                        exercise=previous_exercise,
                        dwell_seconds=previous_dwell,
                        total_exercise_seconds=previous_total_exercise_seconds,
                        total_rep_count=previous_total_rep_count,
                        form_score=previous_form_score,
                    )

            zone_store[incoming.zone_id] = zone
            if incoming.is_present and is_rep_exercise:
                sadla_store[incoming.zone_id] = sadla
            else:
                sadla_store.pop(incoming.zone_id, None)

            history = history_store.get(incoming.zone_id, [])
            minutes_to_free = predict_minutes_to_free_adaptive(
                zone_id=incoming.zone_id,
                exercise=zone.current_exercise,
                dwell_seconds=zone.dwell_seconds,
                exercise_seconds=zone.exercise_seconds,
                total_rep_count=zone.total_rep_count,
                historical_dwell_seconds=history,
            )

            await websocket.send_json(
                {
                    "zone": zone.to_dict(),
                    "sadla_phase": sadla.current_phase,
                    "minutes_to_free": minutes_to_free,
                    "supported_exercises": [
                        "ResistanceBand",
                        "PushUps",
                        "Squats",
                        "RunInPlace",
                    ],
                }
            )
    except WebSocketDisconnect:
        return
