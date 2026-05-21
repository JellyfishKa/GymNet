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
    treadmill_zone: bool = False
    landmarks: list[LandmarkInput] = Field(default_factory=list, max_length=33)


class PoseIngestResponse(BaseModel):
    zone_id: str
    is_present: bool
    exercise: str
    phase: str
    form_penalty: float
    minutes_to_free: int | None = None
    sadla_phase: str | None = None
    zone_status: str | None = None
    dwell_seconds: int | None = None
    rep_count: int | None = None
