from typing import Literal

from pydantic import BaseModel, Field

ExerciseName = Literal["ResistanceBand", "PushUps", "Squats", "RunInPlace"]
PhaseName = Literal["Neutral", "TransitionDown", "Bottom", "TransitionUp", "Standing"]


class LiveUpdateRequest(BaseModel):
    zone_id: str = Field(default="treadmill_zone_1")
    is_present: bool
    exercise: ExerciseName | None = None
    phase: PhaseName | None = None
    form_penalty: float = Field(default=0.0, ge=0.0, le=100.0)
