"""SQLAlchemy async engine + session factory.

Phơi ra `engine`, `AsyncSessionLocal`, và async generator `get_db` để inject
qua FastAPI Depends.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings


def _engine_kwargs() -> dict[str, Any]:
    """Pool kwargs phụ thuộc dialect — SQLite (test) không hỗ trợ pool_size."""
    url = settings.database_url
    if url.startswith(("sqlite", "sqlite+")):
        return {"echo": False, "future": True}
    return {
        "echo": False,
        "pool_pre_ping": True,
        "pool_size": 10,
        "max_overflow": 20,
        "future": True,
    }


engine = create_async_engine(settings.database_url, **_engine_kwargs())

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncIterator[AsyncSession]:
    """Async generator session — yield 1 session/request, commit/rollback tự động.

    Yields:
        Active `AsyncSession`. Caller (service) chịu trách nhiệm commit
        các write ops của mình; generator chỉ ensure rollback khi exception.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
