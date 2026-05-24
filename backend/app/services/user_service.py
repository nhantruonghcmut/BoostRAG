"""User CRUD + group/level management.

Logic này tách rời khỏi auth flow để cả admin endpoints và worker scripts
đều dùng được. Mọi function nhận `db: AsyncSession`.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.core.logging import get_logger
from app.models.user import Group, User, UserRole, UserStatus
from app.schemas.user import UserUpdate

logger = get_logger(__name__)


async def get_by_id(db: AsyncSession, user_id: UUID) -> User:
    """Load user theo UUID hoặc raise NotFoundError."""
    user = await db.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found", details={"user_id": str(user_id)})
    return user


async def get_by_email(db: AsyncSession, email: str) -> User | None:
    """Load user theo email — return None nếu không tồn tại (cho login flow)."""
    stmt = select(User).where(User.email == email.lower())
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_users(
    db: AsyncSession,
    *,
    status: UserStatus | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[User], int]:
    """List users với filter + pagination.

    Returns:
        Tuple `(items, total_count)`.
    """
    base_stmt = select(User)
    count_stmt = select(func.count()).select_from(User)
    if status is not None:
        base_stmt = base_stmt.where(User.status == status)
        count_stmt = count_stmt.where(User.status == status)

    offset = (page - 1) * page_size
    stmt = base_stmt.order_by(User.created_at.desc()).offset(offset).limit(page_size)

    items = (await db.execute(stmt)).scalars().unique().all()
    total = (await db.execute(count_stmt)).scalar_one()
    return list(items), int(total)


async def update_user(db: AsyncSession, user_id: UUID, payload: UserUpdate) -> User:
    """Admin update user fields (level/groups/role/status/full_name)."""
    user = await get_by_id(db, user_id)
    data: dict[str, Any] = payload.model_dump(exclude_unset=True)

    if "groups" in data and data["groups"] is not None:
        user.groups = await _resolve_groups(db, data.pop("groups"))

    for field, value in data.items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)
    logger.info("user.update", user_id=str(user.id), fields=list(data.keys()))
    return user


async def approve_user(
    db: AsyncSession,
    user_id: UUID,
    *,
    access_level: int,
    groups: list[str],
) -> User:
    """Approve pending user — set status=ACTIVE + assign level/groups."""
    user = await get_by_id(db, user_id)
    if user.status != UserStatus.PENDING_APPROVAL:
        raise ConflictError(
            "User not in pending approval state",
            details={"user_id": str(user_id), "current_status": user.status.value},
        )
    user.status = UserStatus.ACTIVE
    user.access_level = access_level
    user.groups = await _resolve_groups(db, groups)
    await db.commit()
    await db.refresh(user)
    logger.info("user.approve", user_id=str(user.id), level=access_level, groups=groups)
    return user


async def unlock_user(db: AsyncSession, user_id: UUID) -> User:
    """Reset failed_login_count + clear locked_until + status → ACTIVE."""
    user = await get_by_id(db, user_id)
    user.failed_login_count = 0
    user.locked_until = None
    if user.status == UserStatus.LOCKED:
        user.status = UserStatus.ACTIVE
    await db.commit()
    await db.refresh(user)
    logger.info("user.unlock", user_id=str(user.id))
    return user


async def disable_user(db: AsyncSession, user_id: UUID) -> User:
    """Soft delete = set status=DISABLED (giữ row cho audit + FK toàn vẹn)."""
    user = await get_by_id(db, user_id)
    user.status = UserStatus.DISABLED
    await db.commit()
    await db.refresh(user)
    logger.info("user.disable", user_id=str(user.id))
    return user


async def ensure_admin_exists(
    db: AsyncSession,
    *,
    email: str,
    password_hash: str,
    full_name: str,
) -> User:
    """Idempotent: tạo admin nếu chưa có (dùng bởi seed_admin script).

    Nếu user tồn tại nhưng KHÔNG phải admin → upgrade role + activate.
    """
    existing = await get_by_email(db, email)
    if existing is not None:
        if existing.role != UserRole.ADMIN or existing.status != UserStatus.ACTIVE:
            existing.role = UserRole.ADMIN
            existing.status = UserStatus.ACTIVE
            existing.access_level = 5
            await db.commit()
            await db.refresh(existing)
            logger.info("admin.seed_upgrade", user_id=str(existing.id))
        return existing

    user = User(
        email=email.lower(),
        password_hash=password_hash,
        full_name=full_name,
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
        access_level=5,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    logger.info("admin.seed_create", user_id=str(user.id))
    return user


# ── Internal helpers ────────────────────────────────────────────────────────


async def _resolve_groups(db: AsyncSession, names: Iterable[str]) -> list[Group]:
    """Map group names → Group instances, auto-create nếu chưa có."""
    cleaned = sorted({n.strip() for n in names if n and n.strip()})
    if not cleaned:
        return []

    stmt = select(Group).where(Group.name.in_(cleaned))
    existing = {g.name: g for g in (await db.execute(stmt)).scalars().all()}

    new_groups: list[Group] = []
    for name in cleaned:
        if name not in existing:
            g = Group(name=name)
            db.add(g)
            new_groups.append(g)
            existing[name] = g

    if new_groups:
        await db.flush()
    return list(existing.values())
