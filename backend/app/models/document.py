"""Document + DocumentChunk models cho ingestion pipeline.

`Document` track file metadata, ACL fields, ingestion status.
`DocumentChunk` lưu metadata chunk (vector nằm trong Qdrant).
"""

from __future__ import annotations

import enum
from uuid import UUID

from sqlalchemy import JSON, Enum as SAEnum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class DocumentStatus(str, enum.Enum):
    """Ingestion lifecycle — xem `docs/RAG_PIPELINE.md` §1.6."""

    PENDING = "pending"
    PARSING = "parsing"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    READY = "ready"
    FAILED = "failed"


class Document(UUIDPKMixin, TimestampMixin, Base):
    """Uploaded document với ACL metadata và ingestion status."""

    __tablename__ = "documents"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(127), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)

    status: Mapped[DocumentStatus] = mapped_column(
        SAEnum(
            DocumentStatus,
            name="document_status",
            values_callable=lambda x: [m.value for m in x],
        ),
        default=DocumentStatus.PENDING,
        nullable=False,
        index=True,
    )
    required_level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    allowed_groups: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list
    )
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    uploaded_by: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    chunks: Mapped[list[DocumentChunk]] = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Document id={self.id} name={self.name!r} status={self.status.value}>"


class DocumentChunk(UUIDPKMixin, TimestampMixin, Base):
    """Metadata chunk — vector stored in Qdrant, referenced by `qdrant_point_id`."""

    __tablename__ = "document_chunks"

    document_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section_path: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    qdrant_point_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    document: Mapped[Document] = relationship("Document", back_populates="chunks")

    def __repr__(self) -> str:
        return f"<DocumentChunk id={self.id} doc={self.document_id} idx={self.chunk_index}>"
