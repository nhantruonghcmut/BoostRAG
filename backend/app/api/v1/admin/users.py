"""Admin user management endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.core.deps import DbSession, require_admin
from app.models.user import User, UserStatus
from app.schemas.common import PaginatedResponse
from app.schemas.user import UserApprove, UserListItem, UserRead, UserUpdate
from app.services import user_service

router = APIRouter(
    prefix="/admin/users",
    tags=["admin-users"],
    dependencies=[Depends(require_admin)],
)


@router.get("", response_model=PaginatedResponse[UserListItem])
async def list_users(
    db: DbSession,
    status_filter: Annotated[UserStatus | None, Query(alias="status")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 20,
) -> PaginatedResponse[UserListItem]:
    """List users với optional `status` filter + pagination."""
    items, total = await user_service.list_users(
        db,
        status=status_filter,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse[UserListItem](
        items=[UserListItem.model_validate(u) for u in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{user_id}", response_model=UserRead)
async def get_user(user_id: UUID, db: DbSession) -> UserRead:
    """Detail user theo UUID."""
    user = await user_service.get_by_id(db, user_id)
    return UserRead.model_validate(user)


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: UUID,
    payload: UserUpdate,
    db: DbSession,
) -> UserRead:
    """Update level/groups/role/status/full_name."""
    user = await user_service.update_user(db, user_id, payload)
    return UserRead.model_validate(user)


@router.post("/{user_id}/approve", response_model=UserRead)
async def approve_user(
    user_id: UUID,
    payload: UserApprove,
    db: DbSession,
) -> UserRead:
    """Duyệt user pending → ACTIVE + gán level/groups."""
    user = await user_service.approve_user(
        db,
        user_id,
        access_level=payload.access_level,
        groups=payload.groups,
    )
    return UserRead.model_validate(user)


@router.post("/{user_id}/unlock", response_model=UserRead)
async def unlock_user(user_id: UUID, db: DbSession) -> UserRead:
    """Reset failed attempt counter + clear lock."""
    user = await user_service.unlock_user(db, user_id)
    return UserRead.model_validate(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def disable_user(user_id: UUID, db: DbSession) -> None:
    """Soft delete = set status=DISABLED."""
    await user_service.disable_user(db, user_id)


# ── Self ────────────────────────────────────────────────────────────────────


@router.get("/_/whoami", response_model=UserRead, include_in_schema=False)
async def whoami(admin: Annotated[User, Depends(require_admin)]) -> UserRead:
    """Quick check admin dep — debug only."""
    return UserRead.model_validate(admin)
