import os
import time
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Base


def _default_database_url() -> str:
    return "sqlite:///./gymnet.db"


DATABASE_URL = os.getenv("DATABASE_URL", _default_database_url())

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def init_db() -> None:
    # На старте контейнера БД может быть еще не готова.
    for _ in range(20):
        try:
            Base.metadata.create_all(bind=engine)
            return
        except OperationalError:
            time.sleep(1)
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
