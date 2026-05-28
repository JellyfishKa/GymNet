"""Сохранение zone_sessions при выходе из ROI (дебаунс is_present)."""

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, ZoneSession
from app.schemas.live import LiveUpdateRequest
from app.services import live_update
from app.services.runtime_store import zone_store


def _reset_runtime() -> None:
    zone_store.clear()
    live_update._absent_streak.clear()
    live_update._pending_finalize.clear()
    live_update.history_store.clear()


def test_finalize_session_after_two_absent_frames(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)

    monkeypatch.setattr(live_update, "SessionLocal", TestSession)
    monkeypatch.setattr(live_update, "_append_history", lambda *args, **kwargs: None)
    monkeypatch.setattr(live_update, "append_completed_session_sample", lambda **kw: None)
    monkeypatch.setattr(live_update, "update_online_profile", lambda **kw: None)
    monkeypatch.setattr(live_update, "clear_landmark_buffer", lambda *args, **kwargs: None)
    monkeypatch.setattr(live_update, "get_ready_window", lambda *args, **kwargs: None)
    monkeypatch.setattr(live_update, "append_live_training_window", lambda **kw: False)
    monkeypatch.setattr(live_update, "cleanup_zone_presence", lambda *args, **kwargs: None)

    _reset_runtime()
    zone_id = "test_zone"

    present = LiveUpdateRequest(
        zone_id=zone_id,
        is_present=True,
        exercise="Squats",
        phase="Standing",
        form_penalty=0.0,
    )
    live_update.apply_live_update(present)
    zone = zone_store[zone_id]
    zone.dwell_seconds = 30
    zone.total_rep_count = 5
    zone.total_exercise_seconds = 25
    zone.form_score = 88.0
    zone_store[zone_id] = zone

    absent = LiveUpdateRequest(
        zone_id=zone_id,
        is_present=False,
        exercise="Squats",
        phase="Neutral",
        form_penalty=0.0,
    )
    live_update.apply_live_update(absent)
    live_update.apply_live_update(absent)

    db = TestSession()
    try:
        rows = db.scalars(select(ZoneSession).where(ZoneSession.zone_id == zone_id)).all()
    finally:
        db.close()

    assert len(rows) == 1
    assert rows[0].dwell_seconds == 30
    assert rows[0].rep_count == 5
    assert rows[0].exercise_seconds == 25
    assert rows[0].form_score == 88.0
