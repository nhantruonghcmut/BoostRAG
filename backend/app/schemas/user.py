"""User schemas (request/response DTOs)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.user import UserRole, UserStatus


class GroupRead(BaseModel):
    """Group serialized minimal cho nested response."""

    id: UUID
    name: str
    description: str | None = None

    model_config = ConfigDict(from_attributes=True)


class UserBase(BaseModel):
    """Common user fields."""

    email: EmailStr
    full_name: str = Field(min_length=1, max_length=150)


class UserCreate(UserBase):
    """Body cho registration (POST /auth/register)."""

    password: str = Field(min_length=10, max_length=128)


class UserUpdate(BaseModel):
    """Admin PATCH body — mọi field optional."""

    full_name: str | None = Field(default=None, min_length=1, max_length=150)
    access_level: int | None = Field(default=None, ge=1, le=5)
    groups: list[str] | None = None
    role: UserRole | None = None
    status: UserStatus | None = None


class UserApprove(BaseModel):
    """Body cho POST /admin/users/{id}/approve."""

    access_level: int = Field(ge=1, le=5, default=1)
    groups: list[str] = Field(default_factory=list)


class UserRead(UserBase):
    """Full user response cho /auth/me + /admin/users/{id}."""

    id: UUID
    role: UserRole
    access_level: int
    status: UserStatus
    groups: list[GroupRead] = Field(default_factory=list)
    last_login_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserListItem(BaseModel):
    """Compact item cho admin /users list."""

    id: UUID
    email: EmailStr
    full_name: str
    role: UserRole
    access_level: int
    status: UserStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserSummary(BaseModel):
    """Embedded user info trong response auth (vd LoginResponse.user)."""

    id: UUID
    email: EmailStr
    full_name: str
    role: UserRole

    model_config = ConfigDict(from_attributes=True)


class GroupCreate(BaseModel):
    """Body tạo group mới (phase sau dùng)."""

    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, v: str) -> str:
        return v.strip()
