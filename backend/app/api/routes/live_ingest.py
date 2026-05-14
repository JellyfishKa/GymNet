from fastapi import APIRouter

from app.schemas.ingest import PoseIngestRequest, PoseIngestResponse
from app.services.pose_pipeline import (
    RoiRect,
    classify_exercise,
    detect_presence,
    form_penalty,
    infer_phase,
)

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

    return PoseIngestResponse(
        zone_id=payload.zone_id,
        is_present=is_present,
        exercise=exercise,
        phase=phase,
        form_penalty=penalty,
    )
