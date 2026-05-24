"""User / Group / RevokedToken models.

Schema:
    - users           — account info + auth state + ACL fields
    - groups          — named tags cho ACL
    - user_groups     — m2m
    - revoked_tokens  — jti list để invalidate refresh trước expiry
"""

from __future__ import annotations

import enum
from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    String,
    Table,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class UserRole(str, enum.Enum):
    """Role of an account. Stored as VARCHAR in DB for migration safety."""

    ADMIN = "admin"
    USER = "user"


class UserStatus(str, enum.Enum):
    """Lifecycle state của user. Chỉ ACTIVE mới được dùng app."""

    PENDING_APPROVAL = "pending_approval"
    ACTIVE = "active"
    LOCKED = "locked"
    DISABLED = "disabled"


user_groups_table = Table(
    "user_groups",
    Base.metadata,
    Column(
        "user_id",
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "group_id",
        PG_UUID(as_uuid=True),
        ForeignKey("groups.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class User(UUIDPKMixin, TimestampMixin, Base):
    """User account.

    `access_level` (1..5) + `groups` (m2m) cấu thành ACL — xem
    `docs/SECURITY.md` mục 2.
    """

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)

    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role", values_callable=lambda x: [m.value for m in x]),
        default=UserRole.USER,
        nullable=False,
    )
    access_level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[UserStatus] = mapped_column(
        SAEnum(
            UserStatus,
            name="user_status",
            values_callable=lambda x: [m.value for m in x],
        ),
        default=UserStatus.PENDING_APPROVAL,
        nullable=False,
        index=True,
    )

    failed_login_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    groups: Mapped[list[Group]] = relationship(
        "Group",
        secondary=user_groups_table,
        lazy="selectin",
        back_populates="users",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} role={self.role.value}>"


class Group(UUIDPKMixin, TimestampMixin, Base):
    """ACL group / tag — VD `HR`, `Finance`, `Engineering`."""

    __tablename__ = "groups"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    users: Mapped[list[User]] = relationship(
        "User",
        secondary=user_groups_table,
        back_populates="groups",
    )

    def __repr__(self) -> str:
        return f"<Group id={self.id} name={self.name!r}>"


class RevokedToken(Base):
    """Refresh-token blacklist (jti) cho rotation.

    Khi user refresh, jti cũ ghi vào đây. Lookup nhanh qua PK `jti`.
    Worker cleanup periodic xóa row với `expires_at < now()`.
    """

    __tablename__ = "revoked_tokens"

    jti: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    revoked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_used_for_replay: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
