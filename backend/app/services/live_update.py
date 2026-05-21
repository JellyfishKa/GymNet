"""Общая логика live-обновления зоны (WS и HTTP ingest)."""

from __future__ import annotations

import logging
from collections import deque

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
from app.services.zone_locks import zone_lock

logger = logging.getLogger(__name__)

REP_BASED_EXERCISES = {"PushUps", "Squats", "ResistanceBand"}
HISTORY_MAXLEN = 50
_absent_streak: dict[str, int] = {}


def _history_list(zone_id: str) -> list[int]:
    bucket = history_store.get(zone_id)
    if bucket is None:
        return []
    return list(bucket)


def _append_history(zone_id: str, dwell_seconds: int) -> None:
    bucket = history_store.setdefault(zone_id, deque(maxlen=HISTORY_MAXLEN))
    bucket.append(dwell_seconds)


def _finalize_session(
    *,
    zone_id: str,
    previous_exercise: str | None,
    previous_dwell: int,
    previous_total_rep_count: int,
    previous_total_exercise_seconds: int,
    previous_form_score: float,
) -> None:
    _append_history(zone_id, previous_dwell)

    db: Session = SessionLocal()
    try:
        save_zone_session(
            db,
            zone_id=zone_id,
            exercise=previous_exercise or "Неизвестно",
            dwell_seconds=previous_dwell,
            rep_count=previous_total_rep_count,
            form_score=previous_form_score,
        )
    except Exception:
        logger.exception("Не удалось сохранить сессию в БД: zone=%s", zone_id)
    finally:
        db.close()

    if not previous_exercise:
        return

    try:
        window = get_ready_window(zone_id)
        if window is not None:
            append_live_training_window(
                zone_id=zone_id,
                exercise=previous_exercise,
                window=window,
                force=True,
            )
    except Exception:
        logger.exception("Не удалось записать live_train: zone=%s", zone_id)

    clear_landmark_buffer(zone_id)

    try:
        update_online_profile(
            zone_id=zone_id,
            exercise=previous_exercise,
            dwell_seconds=previous_dwell,
            total_exercise_seconds=previous_total_exercise_seconds,
            total_rep_count=previous_total_rep_count,
        )
    except Exception:
        logger.exception("Не удалось обновить online-профиль: zone=%s", zone_id)

    try:
        append_completed_session_sample(
            zone_id=zone_id,
            exercise=previous_exercise,
            dwell_seconds=previous_dwell,
            total_exercise_seconds=previous_total_exercise_seconds,
            total_rep_count=previous_total_rep_count,
            form_score=previous_form_score,
        )
    except Exception:
        logger.exception("Не удалось записать live_sessions: zone=%s", zone_id)


def apply_live_update(incoming: LiveUpdateRequest) -> dict:
    with zone_lock(incoming.zone_id):
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

        # Дебаунс выхода: две подряд is_present=false перед сохранением сессии.
        if incoming.is_present:
            _absent_streak[incoming.zone_id] = 0
        else:
            _absent_streak[incoming.zone_id] = _absent_streak.get(incoming.zone_id, 0) + 1

        if (
            not incoming.is_present
            and _absent_streak.get(incoming.zone_id, 0) >= 2
            and previous_dwell > 0
        ):
            _finalize_session(
                zone_id=incoming.zone_id,
                previous_exercise=previous_exercise,
                previous_dwell=previous_dwell,
                previous_total_rep_count=previous_total_rep_count,
                previous_total_exercise_seconds=previous_total_exercise_seconds,
                previous_form_score=previous_form_score,
            )
            _absent_streak[incoming.zone_id] = 0

        zone_store[incoming.zone_id] = zone
        if incoming.is_present and is_rep_exercise:
            sadla_store[incoming.zone_id] = sadla
        else:
            sadla_store.pop(incoming.zone_id, None)

        history = _history_list(incoming.zone_id)
        minutes_to_free = predict_minutes_to_free_adaptive(
            zone_id=incoming.zone_id,
            exercise=zone.current_exercise,
            dwell_seconds=zone.dwell_seconds,
            exercise_seconds=zone.exercise_seconds,
            total_rep_count=zone.total_rep_count,
            historical_dwell_seconds=history,
        )

        return {
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
