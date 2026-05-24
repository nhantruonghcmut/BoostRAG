"""Chat session and message business logic."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.models.chat import ChatMessage, ChatSession, ChunkTrace, MessageRole
from app.models.user import User
from app.rag.engine import TraceData


async def create_session(
    db: AsyncSession,
    user: User,
    *,
    title: str | None = None,
) -> ChatSession:
    """Create a new chat session for user."""
    session = ChatSession(
        user_id=user.id,
        title=title or "New chat",
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def list_sessions(
    db: AsyncSession,
    user: User,
) -> tuple[list[tuple[ChatSession, int]], int]:
    """List user sessions with message counts."""
    count_subq = (
        select(
            ChatMessage.session_id,
            func.count(ChatMessage.id).label("msg_count"),
        )
        .group_by(ChatMessage.session_id)
        .subquery()
    )

    stmt = (
        select(ChatSession, func.coalesce(count_subq.c.msg_count, 0))
        .outerjoin(count_subq, ChatSession.id == count_subq.c.session_id)
        .where(ChatSession.user_id == user.id)
        .order_by(ChatSession.updated_at.desc())
    )
    result = await db.execute(stmt)
    rows = list(result.all())

    total_stmt = select(func.count()).select_from(ChatSession).where(
        ChatSession.user_id == user.id
    )
    total = int((await db.execute(total_stmt)).scalar_one())
    return rows, total


async def get_session(
    db: AsyncSession,
    session_id: UUID,
    user: User,
) -> ChatSession:
    """Load session owned by user."""
    session = await db.get(ChatSession, session_id)
    if session is None or session.user_id != user.id:
        raise NotFoundError("Chat session not found")
    return session


async def list_messages(
    db: AsyncSession,
    session_id: UUID,
    user: User,
) -> list[ChatMessage]:
    """Load message history for session."""
    await get_session(db, session_id, user)
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def save_user_message(
    db: AsyncSession,
    session_id: UUID,
    content: str,
) -> ChatMessage:
    """Persist user message."""
    msg = ChatMessage(
        session_id=session_id,
        role=MessageRole.USER,
        content=content,
    )
    db.add(msg)
    await db.flush()
    return msg


async def save_assistant_message(
    db: AsyncSession,
    *,
    session_id: UUID,
    message_id: UUID,
    content: str,
    citations: list[dict[str, Any]] | None = None,
    error_code: str | None = None,
) -> ChatMessage:
    """Persist assistant message with optional pre-assigned id."""
    msg = ChatMessage(
        id=message_id,
        session_id=session_id,
        role=MessageRole.ASSISTANT,
        content=content,
        citations=citations,
        error_code=error_code,
    )
    db.add(msg)
    await db.flush()
    return msg


async def save_chunk_trace(
    db: AsyncSession,
    *,
    message_id: UUID,
    user_id: UUID,
    trace: TraceData,
) -> ChunkTrace:
    """Persist chunk trace for debug."""
    record = ChunkTrace(
        message_id=message_id,
        user_id=user_id,
        query=trace.query,
        embedding_model=trace.embedding_model,
        llm_model=trace.llm_model,
        retrieved_chunks=trace.retrieved_chunks,
        used_chunks=trace.used_chunks,
        final_prompt=trace.final_prompt,
        tool_calls=trace.tool_calls,
        latency_ms=trace.latency_ms,
        latency_breakdown=trace.latency_breakdown,
        token_usage=trace.token_usage,
    )
    db.add(record)
    await db.flush()
    return record


async def get_chunk_trace_for_message(
    db: AsyncSession,
    message_id: UUID,
    user: User,
    *,
    include_full: bool = False,
) -> ChunkTrace:
    """Load chunk trace if message belongs to user."""
    stmt = (
        select(ChatMessage)
        .options(
            selectinload(ChatMessage.session),
            selectinload(ChatMessage.trace),
        )
        .where(ChatMessage.id == message_id)
    )
    result = await db.execute(stmt)
    message = result.scalar_one_or_none()
    if message is None:
        raise NotFoundError("Message not found")
    if message.session.user_id != user.id:
        raise NotFoundError("Message not found")

    if message.trace is None:
        raise NotFoundError("Trace not found for this message")

    if not include_full and message.trace.final_prompt:
        # Basic mode still returns trace but caller may strip final_prompt
        pass

    return message.trace


async def auto_title_from_query(db: AsyncSession, session_id: UUID, query: str) -> None:
    """Set session title from first user query if still default."""
    session = await db.get(ChatSession, session_id)
    if session is None:
        return
    if session.title == "New chat" or not session.title.strip():
        title = query.strip()[:80]
        if len(query.strip()) > 80:
            title += "..."
        session.title = title or "New chat"
        await db.flush()


def new_assistant_message_id() -> UUID:
    """Generate assistant message id before streaming."""
    return uuid4()
