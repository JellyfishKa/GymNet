from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ZoneSession(Base):
    __tablename__ = "zone_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    zone_id: Mapped[str] = mapped_column(String(64), index=True)
    exercise: Mapped[str] = mapped_column(String(64))
    dwell_seconds: Mapped[int] = mapped_column(Integer)
    exercise_seconds: Mapped[int] = mapped_column(Integer, default=0)
    rep_count: Mapped[int] = mapped_column(Integer, default=0)
    form_score: Mapped[float] = mapped_column(Float, default=100.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
