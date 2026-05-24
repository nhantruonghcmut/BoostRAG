"""Pydantic schemas cho document endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.document import DocumentStatus


class DocumentCreate(BaseModel):
    """Metadata khi upload document (ACL fields)."""

    required_level: int = Field(default=1, ge=1, le=5)
    allowed_groups: list[str] = Field(default_factory=list)
    name: str | None = Field(default=None, max_length=255)


class DocumentUpdate(BaseModel):
    """Admin PATCH — update ACL only."""

    required_level: int | None = Field(default=None, ge=1, le=5)
    allowed_groups: list[str] | None = None


class DocumentUploadResponse(BaseModel):
    """Response 202 sau upload."""

    document_id: UUID
    status: DocumentStatus


class DocumentListItem(BaseModel):
    """Document trong list view."""

    document_id: UUID
    name: str
    size_bytes: int
    uploaded_at: datetime
    status: DocumentStatus
    required_level: int = 1
    allowed_groups: list[str] = Field(default_factory=list)
    mime_type: str | None = None

    model_config = ConfigDict(from_attributes=True)


class DocumentRead(BaseModel):
    """Full document detail (admin)."""

    id: UUID
    name: str
    original_filename: str
    mime_type: str
    size_bytes: int
    status: DocumentStatus
    required_level: int
    allowed_groups: list[str]
    chunk_count: int
    error_message: str | None
    uploaded_by: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_document(cls, doc: object) -> DocumentRead:
        return cls.model_validate(doc)
