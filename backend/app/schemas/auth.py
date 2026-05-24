"""Auth schemas — register/login/refresh/logout."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserStatus
from app.schemas.user import UserSummary


class RegisterRequest(BaseModel):
    """POST /auth/register body."""

    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    full_name: str = Field(min_length=1, max_length=150)


class RegisterResponse(BaseModel):
    """Trả về sau register thành công — status = PENDING_APPROVAL."""

    user_id: UUID
    status: UserStatus
    message: str

    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    """POST /auth/login body."""

    email: EmailStr
    password: str


class TokenPayload(BaseModel):
    """Inner token info đính kèm trong response auth."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="seconds until access token expires")


class LoginResponse(TokenPayload):
    """Body trả về sau login thành công (refresh token set qua cookie)."""

    user: UserSummary


class RefreshResponse(TokenPayload):
    """Body trả về sau refresh — chỉ có access token mới."""


class MessageResponse(BaseModel):
    """Generic message response (vd logout)."""

    message: str
