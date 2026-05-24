"""Pytest fixtures — async DB (SQLite), test client, sample users.

Dùng SQLite trong test (file in-memory) để chạy không cần Postgres.
Production schema vẫn dùng Postgres-specific types (UUID, ENUM) — SQLite
backend của SQLAlchemy fallback OK với `String`-encoded UUID.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from typing import Any

import pytest

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-for-unit-tests")
os.environ.setdefault(
    "MASTER_KEY", "changeme-base64-fernet-key-44-chars-replace-this=="
)

from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.core.deps import get_db
from app.core.security import hash_password
from app.core.storage import InMemoryStorage
from app.main import create_app
from app.models.base import Base
from app.models.user import User, UserRole, UserStatus
from app.rag.retrieval.vector_store import InMemoryVectorStore

TEST_DB_URL = os.environ["DATABASE_URL"]


@pytest.fixture
async def engine() -> AsyncIterator[Any]:
    """Function-scoped async engine — schema fresh per test (SQLite :memory:).

    Dùng StaticPool để mọi connection trong cùng test share 1 DB instance.
    """
    eng = create_async_engine(
        TEST_DB_URL,
        echo=False,
        future=True,
        connect_args={"check_same_thread": False}
        if TEST_DB_URL.startswith("sqlite")
        else {},
        poolclass=StaticPool if TEST_DB_URL.startswith("sqlite") else None,
    )

    if TEST_DB_URL.startswith("sqlite"):

        @event.listens_for(eng.sync_engine, "connect")
        def _set_sqlite_pragma(dbapi_conn, _record):  # type: ignore[no-untyped-def]
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield eng
    finally:
        await eng.dispose()


@pytest.fixture
async def db(engine: Any) -> AsyncIterator[AsyncSession]:
    """Function-scoped session bound vào engine fresh."""
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_maker() as session:
        yield session


@pytest.fixture
async def client(db: AsyncSession) -> AsyncIterator[AsyncClient]:
    """FastAPI ASGI client với DB override."""
    app = create_app()

    async def _override_get_db() -> AsyncIterator[AsyncSession]:
        yield db

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def in_memory_storage() -> InMemoryStorage:
    """Shared in-memory MinIO mock."""
    return InMemoryStorage()


@pytest.fixture
def in_memory_vector_store() -> InMemoryVectorStore:
    """Shared in-memory Qdrant mock."""
    return InMemoryVectorStore()


# ── User fixtures ───────────────────────────────────────────────────────────


@pytest.fixture
async def admin_user(db: AsyncSession) -> User:
    """Active admin user."""
    user = User(
        email="admin@example.com",
        password_hash=hash_password("AdminPass123"),
        full_name="Test Admin",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
        access_level=5,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.fixture
async def active_user(db: AsyncSession) -> User:
    """Active regular user."""
    user = User(
        email="user@example.com",
        password_hash=hash_password("UserPass123"),
        full_name="Test User",
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
        access_level=2,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.fixture
async def pending_user(db: AsyncSession) -> User:
    """Pending approval user."""
    user = User(
        email="pending@example.com",
        password_hash=hash_password("PendingPass123"),
        full_name="Pending User",
        role=UserRole.USER,
        status=UserStatus.PENDING_APPROVAL,
        access_level=1,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
