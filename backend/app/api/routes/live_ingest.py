import logging
from typing import cast

from fastapi import APIRouter, HTTPException

from app.schemas.ingest import PoseIngestRequest, PoseIngestResponse, ZoneSnapshot
from app.schemas.live import ExerciseName, LiveUpdateRequest, PhaseName
from app.services.exercise_classifier import classify_exercise
from app.services.landmark_sequence import get_ready_window, push_landmark_frame
from app.services.live_update import apply_live_update
from app.services.activity_gate import is_meaningful_activity
from app.services.pose_pipeline import PRESENCE_KEYPOINTS, RoiRect, _roi_presence_ratio, detect_presence_raw, form_penalty, infer_phase
from app.services.training_data_sink import append_live_training_window
from app.services.zone_presence import update_zone_presence

logger = logging.getLogger(__name__)

_VALID_EXERCISES: frozenset[str] = frozenset({"PushUps", "Squats", "RunInPlace"})

router = APIRouter(prefix="/live", tags=["live-ingest"])


@router.post("/ingest", response_model=PoseIngestResponse)
def ingest_pose(payload: PoseIngestRequest) -> PoseIngestResponse:
    named_points = {lm.name: (lm.x, lm.y) for lm in payload.landmarks}

    roi = RoiRect(
        x_min=payload.roi.x_min,
        y_min=payload.roi.y_min,
        x_max=payload.roi.x_max,
        y_max=payload.roi.y_max,
    )
    in_roi = detect_presence_raw(named_points, roi) if named_points else False
    presence_hits = [
        name
        for name in PRESENCE_KEYPOINTS
        if named_points.get(name)
        and roi.x_min <= named_points[name][0] <= roi.x_max
        and roi.y_min <= named_points[name][1] <= roi.y_max
    ]
    presence_required = max(2, int(len(PRESENCE_KEYPOINTS) * _roi_presence_ratio()))
    roi_debug = {
        "x_min": payload.roi.x_min,
        "y_min": payload.roi.y_min,
        "x_max": payload.roi.x_max,
        "y_max": payload.roi.y_max,
        "presence_required": presence_required,
        "presence_hits": presence_hits,
        "presence_ok": in_roi,
    }

    window = None
    if payload.landmarks:
        push_landmark_frame(payload.zone_id, payload.landmarks)
        window = get_ready_window(payload.zone_id)

    is_active, activity_rejected = is_meaningful_activity(window) if in_roi else (False, None)
    raw_present = in_roi and is_active
    is_present = update_zone_presence(payload.zone_id, raw_present)

    try:
        (
            exercise,
            classification_source,
            confidence,
            class_scores,
            pose_debug,
            body_orientation,
            ml_probs,
            heuristic_scores,
        ) = classify_exercise(
            payload.zone_id,
            window=window,
            landmarks=named_points,
        )
    except Exception:
        logger.exception("Classification failed for zone %s", payload.zone_id)
        exercise = "RunInPlace"
        classification_source = "error"
        confidence = 0.0
        class_scores = {}
        pose_debug = {}
        body_orientation = "unknown"
        ml_probs = None
        heuristic_scores = {}
    phase = infer_phase(exercise, named_points, payload.zone_id) if is_present else "Neutral"
    penalty = form_penalty(exercise, named_points, phase) if is_present else 0.0
    exercise_for_state = cast(ExerciseName, exercise) if (is_present and exercise in _VALID_EXERCISES) else None

    if is_present and window is not None:
        append_live_training_window(
            zone_id=payload.zone_id,
            exercise=exercise,
            window=window,
        )

    live_result = apply_live_update(
        LiveUpdateRequest(
            zone_id=payload.zone_id,
            is_present=is_present,
            exercise=exercise_for_state,
            phase=cast(PhaseName, phase),
            form_penalty=penalty,
        )
    )
    zone_dict = live_result.get("zone")
    if zone_dict is None:
        logger.error("apply_live_update returned no zone for %s", payload.zone_id)
        raise HTTPException(status_code=500, detail="Internal state error")

    return PoseIngestResponse(
        zone_id=payload.zone_id,
        is_present=is_present,
        in_roi=in_roi,
        activity_rejected=activity_rejected if in_roi and not is_active else None,
        exercise=exercise,
        phase=phase,
        form_penalty=penalty,
        minutes_to_free=live_result.get("minutes_to_free"),
        sadla_phase=live_result.get("sadla_phase"),
        zone=ZoneSnapshot(
            zone_id=zone_dict["zone_id"],
            status=zone_dict["status"],
            dwell_seconds=zone_dict.get("dwell_seconds", 0),
            current_exercise=zone_dict.get("current_exercise"),
            exercise_seconds=zone_dict.get("exercise_seconds", 0),
            rep_count=zone_dict.get("rep_count", 0),
            rep_tempo_seconds=zone_dict.get("rep_tempo_seconds"),
            total_exercise_seconds=zone_dict.get("total_exercise_seconds", 0),
            total_rep_count=zone_dict.get("total_rep_count", 0),
            total_rep_tempo_seconds=zone_dict.get("total_rep_tempo_seconds"),
            tracks_rep_and_time=bool(zone_dict.get("tracks_rep_and_time", False)),
            form_score=zone_dict.get("form_score", 100.0),
        ),
        classification_source=classification_source,
        detected_exercise_confidence=confidence,
        classification_scores=class_scores,
        heuristic_scores=heuristic_scores,
        ml_probs=ml_probs,
        body_orientation=body_orientation,
        pose_debug=pose_debug,
        roi_debug=roi_debug,
        supported_exercises=live_result.get("supported_exercises", ["PushUps", "Squats", "RunInPlace"]),
    )
