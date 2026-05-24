"""Auth endpoints — register, login, refresh, logout, me."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Request, Response, status

from app.core.config import settings
from app.core.deps import DbSession, get_client_ip, require_active_user
from app.core.exceptions import TokenInvalidError
from app.core.logging import get_logger
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    MessageResponse,
    RefreshResponse,
    RegisterRequest,
    RegisterResponse,
)
from app.schemas.user import UserRead, UserSummary
from app.services import auth_service

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/api/v1/auth"


def _set_refresh_cookie(response: Response, token: str, max_age_s: int) -> None:
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        token,
        max_age=max_age_s,
        httponly=True,
        secure=settings.is_prod(),
        samesite="strict",
        path=REFRESH_COOKIE_PATH,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    payload: RegisterRequest,
    db: DbSession,
    request: Request,
) -> RegisterResponse:
    """Tạo tài khoản mới. Status = PENDING_APPROVAL cho đến khi admin duyệt."""
    user = await auth_service.register_user(
        db,
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name,
    )
    logger.info("auth.register_request", email=payload.email, ip=get_client_ip(request))
    return RegisterResponse(
        user_id=user.id,
        status=user.status,
        message="Account created, waiting for admin approval",
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    db: DbSession,
    response: Response,
    request: Request,
) -> LoginResponse:
    """Xác thực + cấp access token (body) + refresh token (httpOnly cookie)."""
    (
        user,
        (access_token, expires_in),
        (refresh_token, _jti, _exp),
    ) = await auth_service.authenticate(
        db,
        email=payload.email,
        password=payload.password,
    )
    _set_refresh_cookie(
        response,
        refresh_token,
        max_age_s=settings.jwt_refresh_ttl_days * 86400,
    )
    logger.info("auth.login", user_id=str(user.id), ip=get_client_ip(request))
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in,
        user=UserSummary.model_validate(user),
    )


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(
    db: DbSession,
    response: Response,
    refresh_token: Annotated[str | None, Cookie(alias=REFRESH_COOKIE_NAME)] = None,
) -> RefreshResponse:
    """Rotate refresh — revoke old jti, cấp tokens mới."""
    if refresh_token is None:
        raise TokenInvalidError("Missing refresh token")

    (
        _user,
        (access_token, expires_in),
        (new_refresh, _jti, _exp),
    ) = await auth_service.refresh_tokens(db, refresh_token=refresh_token)
    _set_refresh_cookie(
        response,
        new_refresh,
        max_age_s=settings.jwt_refresh_ttl_days * 86400,
    )
    return RefreshResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in,
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    db: DbSession,
    response: Response,
    refresh_token: Annotated[str | None, Cookie(alias=REFRESH_COOKIE_NAME)] = None,
) -> MessageResponse:
    """Revoke refresh token + clear cookie. Idempotent."""
    await auth_service.logout(db, refresh_token=refresh_token)
    _clear_refresh_cookie(response)
    return MessageResponse(message="Logged out")


@router.get("/me", response_model=UserRead)
async def me(user: Annotated[User, Depends(require_active_user)]) -> UserRead:
    """Thông tin user hiện tại (fresh từ DB qua dependency)."""
    return UserRead.model_validate(user)
