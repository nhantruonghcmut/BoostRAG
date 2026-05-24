"""Authentication flows: register, login, refresh, logout.

Lockout policy: 5 fail liên tiếp → lock 15 phút (configurable qua env).
Refresh token rotation: mỗi lần refresh → revoke old jti + cấp mới.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    AccountDisabledError,
    AccountLockedError,
    ConflictError,
    InvalidCredentialsError,
    PendingApprovalError,
    TokenInvalidError,
)
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    validate_password_strength,
    verify_password,
)
from app.models.user import RevokedToken, User, UserStatus
from app.services import user_service

logger = get_logger(__name__)


# ── Register ────────────────────────────────────────────────────────────────


async def register_user(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    full_name: str,
) -> User:
    """Tạo user mới với status=PENDING_APPROVAL.

    Raises:
        ConflictError: email đã tồn tại.
        ValidationError: password không đạt policy.
    """
    validate_password_strength(password)

    existing = await user_service.get_by_email(db, email)
    if existing is not None:
        raise ConflictError(
            "Email already registered",
            details={"email": email},
        )

    user = User(
        email=email.lower(),
        password_hash=hash_password(password),
        full_name=full_name,
        status=UserStatus.PENDING_APPROVAL,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    logger.info("auth.register", user_id=str(user.id), email=email)
    return user


# ── Login ───────────────────────────────────────────────────────────────────


async def authenticate(
    db: AsyncSession,
    *,
    email: str,
    password: str,
) -> tuple[User, tuple[str, int], tuple[str, str, datetime]]:
    """Verify credentials + cấp tokens.

    Returns:
        Tuple `(user, (access_token, expires_in), (refresh_token, refresh_jti, refresh_exp))`.

    Raises:
        InvalidCredentialsError: email/password không đúng.
        AccountLockedError: lock active.
        PendingApprovalError: chưa duyệt.
        AccountDisabledError: bị disable.
    """
    user = await user_service.get_by_email(db, email)
    if user is None:
        raise InvalidCredentialsError("Invalid email or password")

    _ensure_login_eligible(user)

    if not verify_password(password, user.password_hash):
        await _register_failed_attempt(db, user)
        raise InvalidCredentialsError("Invalid email or password")

    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = datetime.now(tz=UTC)
    await db.commit()
    await db.refresh(user)

    access = create_access_token(str(user.id), user.role.value)
    refresh = create_refresh_token(str(user.id), user.role.value)
    logger.info("auth.login_success", user_id=str(user.id))
    return user, access, refresh


def _ensure_login_eligible(user: User) -> None:
    """Throw lockout/pending/disabled error nếu user không đủ điều kiện."""
    if user.status == UserStatus.PENDING_APPROVAL:
        raise PendingApprovalError("Account is pending admin approval")
    if user.status == UserStatus.DISABLED:
        raise AccountDisabledError("Account is disabled")
    if user.status == UserStatus.LOCKED:
        now = datetime.now(tz=UTC)
        if user.locked_until is not None and user.locked_until > now:
            raise AccountLockedError(
                "Account is temporarily locked",
                details={"locked_until": user.locked_until.isoformat()},
            )


async def _register_failed_attempt(db: AsyncSession, user: User) -> None:
    """Tăng counter + lock nếu đạt ngưỡng."""
    user.failed_login_count = (user.failed_login_count or 0) + 1
    if user.failed_login_count >= settings.max_failed_login_attempts:
        user.status = UserStatus.LOCKED
        user.locked_until = datetime.now(tz=UTC) + timedelta(minutes=settings.account_lock_minutes)
        logger.warning(
            "auth.lockout",
            user_id=str(user.id),
            attempts=user.failed_login_count,
            locked_until=user.locked_until.isoformat(),
        )
    await db.commit()


# ── Refresh ─────────────────────────────────────────────────────────────────


async def refresh_tokens(
    db: AsyncSession,
    *,
    refresh_token: str,
) -> tuple[User, tuple[str, int], tuple[str, str, datetime]]:
    """Validate refresh token, revoke old jti, cấp tokens mới.

    Raises:
        TokenInvalidError: token sai / revoked / user không tồn tại.
    """
    payload = decode_token(refresh_token, expected_type="refresh")
    jti = payload.get("jti")
    sub = payload.get("sub")
    if not isinstance(jti, str) or not isinstance(sub, str):
        raise TokenInvalidError("Refresh token missing claims")

    revoked = await db.get(RevokedToken, jti)
    if revoked is not None:
        revoked.is_used_for_replay = True
        await db.commit()
        logger.warning("auth.refresh_replay", jti=jti, user_id=sub)
        raise TokenInvalidError("Refresh token has been revoked")

    user = await user_service.get_by_id(db, UUID(sub))
    _ensure_login_eligible(user)

    db.add(
        RevokedToken(
            jti=jti,
            user_id=user.id,
            revoked_at=datetime.now(tz=UTC),
            expires_at=datetime.fromtimestamp(payload["exp"], tz=UTC),
            reason="rotated",
        )
    )

    access = create_access_token(str(user.id), user.role.value)
    new_refresh = create_refresh_token(str(user.id), user.role.value)
    await db.commit()
    logger.info("auth.refresh", user_id=str(user.id))
    return user, access, new_refresh


# ── Logout ──────────────────────────────────────────────────────────────────


async def logout(db: AsyncSession, *, refresh_token: str | None) -> None:
    """Revoke refresh token nếu có. Idempotent."""
    if not refresh_token:
        return
    try:
        payload = decode_token(refresh_token, expected_type="refresh")
    except TokenInvalidError:
        return

    jti = payload.get("jti")
    sub = payload.get("sub")
    if not isinstance(jti, str) or not isinstance(sub, str):
        return

    existing = await db.get(RevokedToken, jti)
    if existing is not None:
        return

    db.add(
        RevokedToken(
            jti=jti,
            user_id=UUID(sub),
            revoked_at=datetime.now(tz=UTC),
            expires_at=datetime.fromtimestamp(payload["exp"], tz=UTC),
            reason="logout",
        )
    )
    await db.commit()
    logger.info("auth.logout", user_id=sub)


async def is_jti_revoked(db: AsyncSession, jti: str) -> bool:
    """Check 1 jti đã revoke chưa (helper cho test)."""
    stmt = select(RevokedToken).where(RevokedToken.jti == jti)
    return (await db.execute(stmt)).scalar_one_or_none() is not None
