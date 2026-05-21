from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.services.rep_exercise_metrics import is_rep_based, rep_tempo_seconds


@dataclass(slots=True)
class ZoneState:
    zone_id: str
    status: str = "Free"
    dwell_seconds: int = 0
    last_entered_at: datetime | None = None
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    current_exercise: str | None = None
    exercise_seconds: int = 0
    exercise_started_at: datetime | None = None
    total_exercise_seconds: int = 0
    total_exercise_started_at: datetime | None = None
    rep_count: int = 0
    total_rep_count: int = 0
    form_score: float = 100.0

    def to_dict(self) -> dict:
        tempo = (
            rep_tempo_seconds(self.exercise_seconds, self.rep_count)
            if is_rep_based(self.current_exercise)
            else None
        )
        total_tempo = (
            rep_tempo_seconds(self.total_exercise_seconds, self.total_rep_count)
            if is_rep_based(self.current_exercise)
            else None
        )
        return {
            "zone_id": self.zone_id,
            "status": self.status,
            "dwell_seconds": self.dwell_seconds,
            "last_entered_at": self.last_entered_at.isoformat() if self.last_entered_at else None,
            "updated_at": self.updated_at.isoformat(),
            "current_exercise": self.current_exercise,
            "exercise_seconds": self.exercise_seconds,
            "rep_count": self.rep_count,
            "rep_tempo_seconds": tempo,
            "total_exercise_seconds": self.total_exercise_seconds,
            "total_rep_count": self.total_rep_count,
            "total_rep_tempo_seconds": total_tempo,
            "tracks_rep_and_time": is_rep_based(self.current_exercise),
            "form_score": round(self.form_score, 2),
        }
