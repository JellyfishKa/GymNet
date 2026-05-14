from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(slots=True)
class ZoneState:
    zone_id: str
    status: str = "Free"
    dwell_seconds: int = 0
    last_entered_at: datetime | None = None
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    current_exercise: str | None = None
    rep_count: int = 0
    form_score: float = 100.0

    def to_dict(self) -> dict:
        return {
            "zone_id": self.zone_id,
            "status": self.status,
            "dwell_seconds": self.dwell_seconds,
            "last_entered_at": self.last_entered_at.isoformat() if self.last_entered_at else None,
            "updated_at": self.updated_at.isoformat(),
            "current_exercise": self.current_exercise,
            "rep_count": self.rep_count,
            "form_score": round(self.form_score, 2),
        }
