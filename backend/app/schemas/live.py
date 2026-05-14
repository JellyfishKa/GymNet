from pydantic import BaseModel, Field


class LiveUpdateRequest(BaseModel):
    zone_id: str = Field(default="treadmill_zone_1")
    is_present: bool
    exercise: str | None = Field(
        default=None,
        description="ResistanceBand | PushUps | Squats | RunInPlace",
    )
    phase: str | None = Field(
        default=None,
        description="Neutral | TransitionDown | Bottom | TransitionUp | Standing",
    )
    form_penalty: float = Field(default=0.0, ge=0.0, le=100.0)
