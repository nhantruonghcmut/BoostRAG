"""Pydantic DTOs cho chat API."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ChatSessionCreate(BaseModel):
    """Request body cho POST /chat/sessions."""

    title: str | None = Field(default=None, max_length=255)


class ChatSessionRead(BaseModel):
    """Response cho session."""

    session_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatSessionListItem(BaseModel):
    """Item trong list sessions."""

    session_id: UUID
    title: str
    updated_at: datetime
    message_count: int = 0


class ChatSessionListResponse(BaseModel):
    """List sessions response."""

    items: list[ChatSessionListItem]
    total: int


class Citation(BaseModel):
    """Citation reference trong assistant message."""

    citation_id: int
    document_id: str
    doc_name: str
    page: int | None = None


class ChatMessageRead(BaseModel):
    """Single chat message."""

    message_id: UUID
    role: str
    content: str
    citations: list[Citation] | None = None
    error_code: str | None = None
    created_at: datetime


class ChatMessageListResponse(BaseModel):
    """Message history response."""

    items: list[ChatMessageRead]


class ChatStreamRequest(BaseModel):
    """Request body cho POST /chat/stream."""

    session_id: UUID | None = None
    query: str = Field(min_length=1, max_length=8000)
    include_debug: bool = False


class ChunkTraceChunkRead(BaseModel):
    """Chunk detail trong trace."""

    chunk_id: str
    document_id: str
    document_name: str
    text: str
    page_number: int | None = None
    section_path: list[str] = Field(default_factory=list)
    heading_context: str = ""
    vector_score: float = 0.0
    rerank_score: float | None = None
    citation_id: int = 0


class ChunkTraceRead(BaseModel):
    """Full chunk trace for debug."""

    trace_id: UUID
    message_id: UUID
    query: str
    embedding_model: str
    llm_model: str
    retrieved_chunks: list[ChunkTraceChunkRead]
    used_chunks: list[ChunkTraceChunkRead]
    final_prompt: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    latency_ms: int
    latency_breakdown: dict[str, Any] | None = None
    token_usage: dict[str, Any] | None = None
    created_at: datetime
