from pydantic import BaseModel, Field


class RoiSchema(BaseModel):
    x_min: float = Field(ge=0.0, le=1.0)
    y_min: float = Field(ge=0.0, le=1.0)
    x_max: float = Field(ge=0.0, le=1.0)
    y_max: float = Field(ge=0.0, le=1.0)


class LandmarkInput(BaseModel):
    name: str
    x: float
    y: float


class PoseIngestRequest(BaseModel):
    zone_id: str = "treadmill_zone_1"
    roi: RoiSchema
    landmarks: list[LandmarkInput] = Field(default_factory=list, max_length=33)


class ZoneSnapshot(BaseModel):
    zone_id: str
    status: str
    dwell_seconds: int = 0
    current_exercise: str | None = None
    exercise_seconds: int = 0
    rep_count: int = 0
    rep_tempo_seconds: float | None = None
    total_exercise_seconds: int = 0
    total_rep_count: int = 0
    total_rep_tempo_seconds: float | None = None
    tracks_rep_and_time: bool = False
    form_score: float = 100.0


class PoseIngestResponse(BaseModel):
    zone_id: str
    is_present: bool
    in_roi: bool = False
    activity_rejected: str | None = None
    exercise: str
    phase: str
    form_penalty: float
    minutes_to_free: int | None = None
    sadla_phase: str | None = None
    zone: ZoneSnapshot | None = None
    classification_source: str | None = None
    detected_exercise_confidence: float | None = None
    classification_scores: dict[str, float] | None = None
    heuristic_scores: dict[str, float] | None = None
    ml_probs: dict[str, float] | None = None
    body_orientation: str | None = None
    pose_debug: dict[str, float | None] | None = None
    roi_debug: dict[str, float | str | list[str] | bool | None] | None = None
    supported_exercises: list[str] = Field(
        default_factory=lambda: ["PushUps", "Squats", "RunInPlace"]
    )
