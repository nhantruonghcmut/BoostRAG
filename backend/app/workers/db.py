"""Sync DB session helper for Celery workers."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def _sync_database_url() -> str:
    url = settings.database_url
    return url.replace("+asyncpg", "+psycopg2").replace("sqlite+aiosqlite", "sqlite")


_sync_engine = create_engine(_sync_database_url(), pool_pre_ping=True)
SyncSessionLocal = sessionmaker(bind=_sync_engine, expire_on_commit=False)


@contextmanager
def get_sync_db() -> Iterator[Session]:
    """Yield sync SQLAlchemy session for Celery tasks."""
    session = SyncSessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
