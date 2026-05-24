"""Chat session, message, and chunk trace models.

`ChunkTrace` lưu debug info cho mỗi câu trả lời assistant — xem
`docs/RAG_PIPELINE.md` §5.
"""

from __future__ import annotations

import enum
from datetime import datetime
from uuid import UUID

from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from app.models.user import User


class MessageRole(str, enum.Enum):
    """Role của chat message."""

    USER = "user"
    ASSISTANT = "assistant"


class ChatSession(UUIDPKMixin, TimestampMixin, Base):
    """Một phiên chat của user."""

    __tablename__ = "chat_sessions"

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="New chat")

    user: Mapped["User"] = relationship("User", lazy="raise")
    messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="session",
        lazy="raise",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )

    def __repr__(self) -> str:
        return f"<ChatSession id={self.id} user_id={self.user_id}>"


class ChatMessage(UUIDPKMixin, Base):
    """Một message trong session — user hoặc assistant."""

    __tablename__ = "chat_messages"

    session_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[MessageRole] = mapped_column(
        SAEnum(
            MessageRole,
            name="message_role",
            values_callable=lambda x: [m.value for m in x],
        ),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    citations: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    session: Mapped[ChatSession] = relationship(
        "ChatSession",
        back_populates="messages",
        lazy="raise",
    )
    trace: Mapped["ChunkTrace | None"] = relationship(
        "ChunkTrace",
        back_populates="message",
        uselist=False,
        lazy="raise",
    )

    def __repr__(self) -> str:
        return f"<ChatMessage id={self.id} role={self.role}>"


class ChunkTrace(UUIDPKMixin, Base):
    """Debug trace cho một assistant message."""

    __tablename__ = "chunk_traces"

    message_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("chat_messages.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(128), nullable=False)
    llm_model: Mapped[str] = mapped_column(String(128), nullable=False)
    retrieved_chunks: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    used_chunks: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    final_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    tool_calls: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    latency_breakdown: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    token_usage: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    message: Mapped[ChatMessage] = relationship(
        "ChatMessage",
        back_populates="trace",
        lazy="raise",
    )

    def __repr__(self) -> str:
        return f"<ChunkTrace id={self.id} message_id={self.message_id}>"
