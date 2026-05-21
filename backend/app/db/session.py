import os
import time
from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Base


def _default_database_url() -> str:
    return "sqlite:///./gymnet.db"


DATABASE_URL = os.getenv("DATABASE_URL", _default_database_url())

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def _ensure_zone_sessions_columns() -> None:
    inspector = inspect(engine)
    if "zone_sessions" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("zone_sessions")}
    if "exercise_seconds" not in columns:
        with engine.begin() as conn:
            conn.execute(
                text("ALTER TABLE zone_sessions ADD COLUMN exercise_seconds INTEGER NOT NULL DEFAULT 0")
            )


def init_db() -> None:
    # На старте контейнера БД может быть еще не готова.
    for _ in range(20):
        try:
            Base.metadata.create_all(bind=engine)
            _ensure_zone_sessions_columns()
            return
        except OperationalError:
            time.sleep(1)
    Base.metadata.create_all(bind=engine)
    _ensure_zone_sessions_columns()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
