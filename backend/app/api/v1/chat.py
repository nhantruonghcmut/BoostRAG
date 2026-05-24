"""Chat endpoints — sessions, history, SSE streaming, chunk trace."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse

from app.core.deps import DbSession, require_active_user
from app.core.logging import get_logger
from app.models.chat import ChatSession
from app.models.user import User
from app.rag.engine import RAGEngine, RunOptions, UserContext
from app.schemas.chat import (
    ChatMessageListResponse,
    ChatMessageRead,
    ChatSessionCreate,
    ChatSessionListItem,
    ChatSessionListResponse,
    ChatSessionRead,
    ChatStreamRequest,
    ChunkTraceChunkRead,
    ChunkTraceRead,
    Citation,
)
from app.services import chat_service

logger = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


def _session_read(session: ChatSession) -> ChatSessionRead:
    return ChatSessionRead(
        session_id=session.id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.post(
    "/sessions",
    response_model=ChatSessionRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_session(
    payload: ChatSessionCreate,
    db: DbSession,
    current_user: Annotated[User, Depends(require_active_user)],
) -> ChatSessionRead:
    """Tạo chat session mới."""
    session = await chat_service.create_session(
        db,
        current_user,
        title=payload.title,
    )
    return _session_read(session)


@router.get("/sessions", response_model=ChatSessionListResponse)
async def list_sessions(
    db: DbSession,
    current_user: Annotated[User, Depends(require_active_user)],
) -> ChatSessionListResponse:
    """List sessions của user hiện tại."""
    rows, total = await chat_service.list_sessions(db, current_user)
    items = [
        ChatSessionListItem(
            session_id=session.id,
            title=session.title,
            updated_at=session.updated_at,
            message_count=int(msg_count),
        )
        for session, msg_count in rows
    ]
    return ChatSessionListResponse(items=items, total=total)


@router.get(
    "/sessions/{session_id}/messages",
    response_model=ChatMessageListResponse,
)
async def get_messages(
    session_id: UUID,
    db: DbSession,
    current_user: Annotated[User, Depends(require_active_user)],
) -> ChatMessageListResponse:
    """Lịch sử messages của session."""
    messages = await chat_service.list_messages(db, session_id, current_user)
    items = [
        ChatMessageRead(
            message_id=m.id,
            role=m.role.value if hasattr(m.role, "value") else str(m.role),
            content=m.content,
            citations=[Citation(**c) for c in m.citations] if m.citations else None,
            error_code=m.error_code,
            created_at=m.created_at,
        )
        for m in messages
    ]
    return ChatMessageListResponse(items=items)


@router.post("/stream")
async def stream_chat(
    payload: ChatStreamRequest,
    db: DbSession,
    current_user: Annotated[User, Depends(require_active_user)],
) -> StreamingResponse:
    """SSE streaming chat — main RAG endpoint."""
    engine = RAGEngine()

    async def sse_generator() -> AsyncIterator[str]:
        session_id = payload.session_id
        try:
            if session_id is None:
                session = await chat_service.create_session(db, current_user)
                session_id = session.id
            else:
                await chat_service.get_session(db, session_id, current_user)

            await chat_service.save_user_message(db, session_id, payload.query)
            await chat_service.auto_title_from_query(db, session_id, payload.query)

            history_msgs = await chat_service.list_messages(db, session_id, current_user)
            history = [
                {
                    "role": m.role.value if hasattr(m.role, "value") else str(m.role),
                    "content": m.content,
                }
                for m in history_msgs[:-1]
            ]

            assistant_id = chat_service.new_assistant_message_id()
            user_ctx = UserContext(
                user_id=current_user.id,
                access_level=current_user.access_level,
                groups=[g.name for g in current_user.groups],
            )
            opts = RunOptions(
                message_id=assistant_id,
                include_debug=payload.include_debug,
                history=history,
            )

            final_content = ""
            final_citations: list[dict[str, Any]] | None = None
            error_code: str | None = None
            trace_data: Any = None

            async for event in engine.run(payload.query, user_ctx, opts):
                if event.event == "start":
                    start_payload = event.data if isinstance(event.data, dict) else {}
                    start_data = {**start_payload, "session_id": str(session_id)}
                    yield _sse(event.event, start_data)
                    continue
                if event.event == "done":
                    final_content = event.data.get("content", "")
                    final_citations = event.data.get("citations")
                    error_code = event.data.get("error_code")
                    trace_data = event.data.get("trace")
                    client_data = {
                        k: v
                        for k, v in event.data.items()
                        if k not in ("content", "trace", "citations", "error_code")
                    }
                    yield _sse(event.event, client_data)
                else:
                    yield _sse(event.event, event.data)

            await chat_service.save_assistant_message(
                db,
                session_id=session_id,
                message_id=assistant_id,
                content=final_content,
                citations=final_citations,
                error_code=error_code,
            )
            if trace_data is not None:
                await chat_service.save_chunk_trace(
                    db,
                    message_id=assistant_id,
                    user_id=current_user.id,
                    trace=trace_data,
                )
            await db.commit()

        except Exception as exc:
            logger.exception("chat.stream_error")
            yield _sse("error", {"code": "INTERNAL_ERROR", "message": str(exc)})

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/messages/{message_id}/trace", response_model=ChunkTraceRead)
async def get_message_trace(
    message_id: UUID,
    db: DbSession,
    current_user: Annotated[User, Depends(require_active_user)],
) -> ChunkTraceRead:
    """Chunk debug trace cho message (user-owned)."""
    trace = await chat_service.get_chunk_trace_for_message(
        db,
        message_id,
        current_user,
        include_full=True,
    )
    return ChunkTraceRead(
        trace_id=trace.id,
        message_id=trace.message_id,
        query=trace.query,
        embedding_model=trace.embedding_model,
        llm_model=trace.llm_model,
        retrieved_chunks=[ChunkTraceChunkRead(**c) for c in trace.retrieved_chunks],
        used_chunks=[ChunkTraceChunkRead(**c) for c in trace.used_chunks],
        final_prompt=trace.final_prompt,
        tool_calls=trace.tool_calls,
        latency_ms=trace.latency_ms,
        latency_breakdown=trace.latency_breakdown,
        token_usage=trace.token_usage,
        created_at=trace.created_at,
    )


def _sse(event: str, data: object) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"
