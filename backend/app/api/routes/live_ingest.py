from typing import cast

from fastapi import APIRouter

from app.schemas.ingest import PoseIngestRequest, PoseIngestResponse
from app.schemas.live import ExerciseName, LiveUpdateRequest, PhaseName
from app.services.landmark_sequence import get_ready_window, push_landmark_frame
from app.services.live_update import apply_live_update
from app.services.pose_pipeline import (
    RoiRect,
    classify_exercise,
    detect_presence,
    form_penalty,
    infer_phase,
)
from app.services.training_data_sink import append_live_training_window

router = APIRouter(prefix="/live", tags=["live-ingest"])


@router.post("/ingest", response_model=PoseIngestResponse)
def ingest_pose(payload: PoseIngestRequest) -> PoseIngestResponse:
    points = [(lm.x, lm.y) for lm in payload.landmarks]
    named_points = {lm.name: (lm.x, lm.y) for lm in payload.landmarks}

    roi = RoiRect(
        x_min=payload.roi.x_min,
        y_min=payload.roi.y_min,
        x_max=payload.roi.x_max,
        y_max=payload.roi.y_max,
    )
    is_present = detect_presence(points, roi)
    exercise = classify_exercise(named_points, treadmill_zone=payload.treadmill_zone)
    phase = infer_phase(exercise, named_points)
    penalty = form_penalty(exercise, named_points)

    if payload.landmarks:
        push_landmark_frame(payload.zone_id, payload.landmarks)
        if is_present:
            window = get_ready_window(payload.zone_id)
            if window is not None:
                append_live_training_window(
                    zone_id=payload.zone_id,
                    exercise=exercise,
                    window=window,
                )

    live_result = apply_live_update(
        LiveUpdateRequest(
            zone_id=payload.zone_id,
            is_present=is_present,
            exercise=cast(ExerciseName, exercise),
            phase=cast(PhaseName, phase),
            form_penalty=penalty,
        )
    )
    zone = live_result["zone"]

    return PoseIngestResponse(
        zone_id=payload.zone_id,
        is_present=is_present,
        exercise=exercise,
        phase=phase,
        form_penalty=penalty,
        minutes_to_free=live_result.get("minutes_to_free"),
        sadla_phase=live_result.get("sadla_phase"),
        zone_status=zone.get("status"),
        dwell_seconds=zone.get("dwell_seconds"),
        rep_count=zone.get("rep_count"),
    )
