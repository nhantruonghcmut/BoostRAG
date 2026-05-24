"""Auth primitives: password hash, JWT encode/decode, password policy.

KHÔNG đặt `access_level`/`groups` vào JWT — luôn load fresh từ DB (xem
`docs/SECURITY.md` mục 4.2).
"""

from __future__ import annotations

import re
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import uuid4

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.exceptions import TokenExpiredError, TokenInvalidError, ValidationError

TokenType = Literal["access", "refresh"]

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

_PASSWORD_MIN_LEN = 10
_PASSWORD_LETTER_RE = re.compile(r"[A-Za-z]")
_PASSWORD_DIGIT_RE = re.compile(r"\d")


# ── Password ────────────────────────────────────────────────────────────────


def hash_password(plain: str) -> str:
    """Hash plaintext password bằng bcrypt cost 12.

    Args:
        plain: password chưa hash.

    Returns:
        Bcrypt hash string an toàn để lưu DB.
    """
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify plaintext khớp với hash đã lưu.

    Constant-time so sánh bằng bcrypt internals (không sớm return).
    """
    try:
        return _pwd_context.verify(plain, hashed)
    except ValueError:
        return False


def validate_password_strength(password: str) -> None:
    """Enforce policy: min 10 chars + ≥1 letter + ≥1 digit.

    Raises:
        ValidationError: nếu không đạt policy.
    """
    if len(password) < _PASSWORD_MIN_LEN:
        raise ValidationError(
            f"Password must be at least {_PASSWORD_MIN_LEN} characters",
            details={"min_length": _PASSWORD_MIN_LEN},
        )
    if not _PASSWORD_LETTER_RE.search(password):
        raise ValidationError("Password must contain at least 1 letter")
    if not _PASSWORD_DIGIT_RE.search(password):
        raise ValidationError("Password must contain at least 1 digit")


# ── JWT ─────────────────────────────────────────────────────────────────────


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _build_payload(
    subject: str,
    role: str,
    token_type: TokenType,
    expires: datetime,
    *,
    jti: str | None = None,
) -> dict[str, Any]:
    return {
        "sub": subject,
        "role": role,
        "type": token_type,
        "iat": int(_now().timestamp()),
        "exp": int(expires.timestamp()),
        "jti": jti or str(uuid4()),
    }


def create_access_token(subject: str, role: str) -> tuple[str, int]:
    """Tạo access token JWT.

    Args:
        subject: thường là user UUID.
        role: `"admin"` | `"user"`.

    Returns:
        Tuple `(token, expires_in_seconds)`.
    """
    expires = _now() + timedelta(minutes=settings.jwt_access_ttl_min)
    payload = _build_payload(subject, role, "access", expires)
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, settings.jwt_access_ttl_min * 60


def create_refresh_token(subject: str, role: str) -> tuple[str, str, datetime]:
    """Tạo refresh token JWT với `jti` (cho rotation).

    Returns:
        Tuple `(token, jti, expires_at)`.
    """
    expires = _now() + timedelta(days=settings.jwt_refresh_ttl_days)
    jti = str(uuid4())
    payload = _build_payload(subject, role, "refresh", expires, jti=jti)
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, jti, expires


def decode_token(token: str, expected_type: TokenType | None = None) -> dict[str, Any]:
    """Decode + validate JWT.

    Args:
        token: JWT string.
        expected_type: nếu set, raise nếu `type` claim không khớp.

    Returns:
        Decoded payload dict.

    Raises:
        TokenExpiredError: nếu token đã hết hạn.
        TokenInvalidError: signature sai, claims thiếu, hoặc type mismatch.
    """
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except JWTError as e:
        if "expired" in str(e).lower():
            raise TokenExpiredError("Token expired") from e
        raise TokenInvalidError("Invalid token") from e

    if expected_type is not None and payload.get("type") != expected_type:
        raise TokenInvalidError(
            f"Expected token type '{expected_type}', got '{payload.get('type')}'"
        )

    if "sub" not in payload or "role" not in payload:
        raise TokenInvalidError("Token missing required claims")

    return payload


def generate_secure_token(length: int = 32) -> str:
    """Tạo URL-safe random token (cho password reset, ...) — chưa dùng Phase 1."""
    return secrets.token_urlsafe(length)
