"""FastAPI dependencies — `get_db`, `get_current_user`, `require_admin`, ...

Mọi router cần auth nên dùng các dep này thay vì decode JWT trực tiếp.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.exceptions import (
    AccountDisabledError,
    AccountLockedError,
    AuthorizationError,
    PendingApprovalError,
    TokenInvalidError,
)
from app.core.security import decode_token
from app.models.user import User, UserRole, UserStatus

bearer_scheme = HTTPBearer(auto_error=True, scheme_name="bearer")


DbSession = Annotated[AsyncSession, Depends(get_db)]
BearerCreds = Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)]


async def get_current_user(
    creds: BearerCreds,
    db: DbSession,
) -> User:
    """Decode JWT access token → load fresh User từ DB.

    KHÔNG trust claims trong JWT (chỉ dùng `sub`); load `access_level` và
    `groups` từ DB mỗi request (xem `docs/SECURITY.md` 4.2).

    Raises:
        TokenInvalidError: token sai format hoặc user không tồn tại.
        TokenExpiredError: token hết hạn.
    """
    payload = decode_token(creds.credentials, expected_type="access")
    user_id_raw = payload.get("sub")
    if not isinstance(user_id_raw, str):
        raise TokenInvalidError("Token subject is not a string")
    try:
        user_id = UUID(user_id_raw)
    except ValueError as e:
        raise TokenInvalidError("Token subject is not a valid UUID") from e

    user = await db.get(User, user_id)
    if user is None:
        raise TokenInvalidError("User not found")
    return user


async def require_active_user(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Yêu cầu user đã ACTIVE.

    Raises:
        PendingApprovalError: user chưa được admin duyệt.
        AccountLockedError: tài khoản đang lock.
        AccountDisabledError: tài khoản bị disable.
    """
    if user.status == UserStatus.PENDING_APPROVAL:
        raise PendingApprovalError("Account is pending admin approval")
    if user.status == UserStatus.LOCKED:
        raise AccountLockedError("Account is locked")
    if user.status == UserStatus.DISABLED:
        raise AccountDisabledError("Account is disabled")
    return user


async def require_admin(
    user: Annotated[User, Depends(require_active_user)],
) -> User:
    """Yêu cầu user có role admin.

    Raises:
        AuthorizationError: nếu không phải admin.
    """
    if user.role != UserRole.ADMIN:
        raise AuthorizationError("Admin role required")
    return user


def get_client_ip(request: Request) -> str:
    """Best-effort client IP — ưu tiên X-Forwarded-For (sau proxy)."""
    if (xff := request.headers.get("x-forwarded-for")) is not None:
        return xff.split(",")[0].strip()
    if request.client is None:
        return "unknown"
    return request.client.host
