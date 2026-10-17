"""SQLAlchemy engine / session / declarative base."""
from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings

settings = get_settings()


def _normalize_db_url(url: str) -> str:
    """Anchor a relative sqlite path to the backend dir so the DB is found
    regardless of the current working directory."""
    prefix = "sqlite:///"
    if url.startswith(prefix):
        raw = url[len(prefix):]
        if raw and not raw.startswith("/"):  # relative path like ./dorkhub.db
            backend_dir = Path(__file__).resolve().parents[2]
            return prefix + str((backend_dir / raw).resolve())
    return url


_db_url = _normalize_db_url(settings.database_url)
_connect_args = {"check_same_thread": False} if _db_url.startswith("sqlite") else {}
engine = create_engine(_db_url, connect_args=_connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables. MVP uses create_all; Alembic can be layered on later."""
    from app import db  # noqa: F401  ensure models are imported
    from app.db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
