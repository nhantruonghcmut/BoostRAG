"""Document CRUD + ACL + ingestion orchestration."""

from __future__ import annotations

import json
import re
import unicodedata
from typing import Any
from uuid import UUID, uuid4

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ACLError, NotFoundError, ValidationError
from app.core.logging import get_logger
from app.core.storage import (
    StorageClient,
    build_document_storage_key,
    get_storage_client,
)
from app.models.document import Document, DocumentStatus
from app.models.user import User, UserRole
from app.rag.ingestion.parsers import supported_mime_types
from app.rag.retrieval.vector_store import VectorStore, get_vector_store
from app.schemas.document import DocumentUpdate

logger = get_logger(__name__)

_ALLOWED_MIMES = supported_mime_types()


def user_can_access_document(user: User, document: Document) -> bool:
    """ACL check — user reads doc if level sufficient AND group match."""
    if user.access_level < document.required_level:
        return False
    allowed = document.allowed_groups or []
    if not allowed:
        return True
    user_groups = {g.name for g in user.groups}
    return bool(user_groups & set(allowed))


def _sanitize_filename(filename: str) -> str:
    normalized = unicodedata.normalize("NFKC", filename)
    normalized = normalized.replace("\\", "/").split("/")[-1]
    normalized = re.sub(r"[^\w.\- ]", "_", normalized)
    return normalized[:500] or "upload.bin"


def _detect_mime(content_type: str | None, data: bytes) -> str:
    mime = (content_type or "").split(";")[0].strip().lower()
    if mime in _ALLOWED_MIMES:
        return mime
    try:
        import magic

        detected = magic.from_buffer(data, mime=True)
        if detected in _ALLOWED_MIMES:
            return detected
    except Exception:
        pass
    if mime:
        return mime
    return "application/octet-stream"


async def upload_document(
    db: AsyncSession,
    *,
    file: UploadFile,
    uploaded_by: User,
    required_level: int = 1,
    allowed_groups: list[str] | None = None,
    name: str | None = None,
    storage: StorageClient | None = None,
    enqueue_task: bool = True,
) -> Document:
    """Upload file to MinIO, create DB row, enqueue ingestion task."""
    data = await file.read()
    if len(data) > settings.max_file_size_bytes:
        raise ValidationError(
            f"File exceeds max size of {settings.max_file_size_mb}MB",
            details={"size_bytes": len(data)},
        )
    if not data:
        raise ValidationError("Empty file")

    mime_type = _detect_mime(file.content_type, data)
    if mime_type not in _ALLOWED_MIMES:
        raise ValidationError(
            f"Unsupported file type: {mime_type}",
            details={"mime_type": mime_type, "allowed": sorted(_ALLOWED_MIMES)},
        )

    original_filename = _sanitize_filename(file.filename or "upload.bin")
    doc_id = uuid4()
    storage_key = build_document_storage_key(str(doc_id), original_filename)
    doc_name = name or original_filename

    storage_client = storage or get_storage_client()
    storage_client.upload(storage_key, data, mime_type)

    document = Document(
        id=doc_id,
        name=doc_name,
        original_filename=original_filename,
        mime_type=mime_type,
        size_bytes=len(data),
        storage_key=storage_key,
        status=DocumentStatus.PENDING,
        required_level=required_level,
        allowed_groups=allowed_groups or [],
        uploaded_by=uploaded_by.id,
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)

    logger.info(
        "doc.upload",
        document_id=str(document.id),
        mime_type=mime_type,
        size=len(data),
    )

    if enqueue_task:
        from app.workers.ingestion_tasks import parse_and_embed_document

        parse_and_embed_document.delay(str(document.id))

    return document


async def list_documents(
    db: AsyncSession,
    *,
    user: User,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Document], int]:
    """List documents — admin sees all, user sees ACL-filtered."""
    if user.role == UserRole.ADMIN:
        base = select(Document)
        count_stmt = select(func.count()).select_from(Document)
    else:
        all_docs = (
            (await db.execute(select(Document).order_by(Document.created_at.desc())))
            .scalars()
            .all()
        )
        filtered = [d for d in all_docs if user_can_access_document(user, d)]
        total = len(filtered)
        offset = (page - 1) * page_size
        return filtered[offset : offset + page_size], total

    offset = (page - 1) * page_size
    stmt = base.order_by(Document.created_at.desc()).offset(offset).limit(page_size)
    items = list((await db.execute(stmt)).scalars().all())
    total = int((await db.execute(count_stmt)).scalar_one())
    return items, total


async def get_document(
    db: AsyncSession,
    document_id: UUID,
    *,
    user: User | None = None,
) -> Document:
    """Get document by ID — optional ACL check for non-admin."""
    document = await db.get(Document, document_id)
    if document is None:
        raise NotFoundError(
            "Document not found",
            details={"document_id": str(document_id)},
        )
    if user is not None and user.role != UserRole.ADMIN:
        if not user_can_access_document(user, document):
            raise ACLError(
                "You do not have access to this document",
                details={"document_id": str(document_id)},
            )
    return document


async def update_document_acl(
    db: AsyncSession,
    document_id: UUID,
    payload: DocumentUpdate,
) -> Document:
    """Admin update ACL fields."""
    document = await get_document(db, document_id)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(document, field, value)
    await db.commit()
    await db.refresh(document)
    logger.info(
        "doc.acl_update", document_id=str(document_id), fields=list(data.keys())
    )
    return document


async def delete_document(
    db: AsyncSession,
    document_id: UUID,
    *,
    storage: StorageClient | None = None,
    vector_store: VectorStore | None = None,
) -> None:
    """Hard delete — Qdrant → MinIO → DB (fail-safe order)."""
    document = await db.get(Document, document_id)
    if document is None:
        raise NotFoundError(
            "Document not found",
            details={"document_id": str(document_id)},
        )

    vs = vector_store or get_vector_store()
    vs.delete_by_document(str(document_id))

    storage_client = storage or get_storage_client()
    storage_client.delete_prefix(f"documents/{document_id}/")

    await db.delete(document)
    await db.commit()
    logger.info("doc.delete", document_id=str(document_id))


async def reindex_document(
    db: AsyncSession,
    document_id: UUID,
) -> Document:
    """Re-run ingestion pipeline."""
    document = await get_document(db, document_id)
    document.status = DocumentStatus.PENDING
    document.error_message = None
    await db.commit()
    await db.refresh(document)

    from app.workers.ingestion_tasks import parse_and_embed_document

    parse_and_embed_document.delay(str(document.id))
    logger.info("doc.reindex", document_id=str(document_id))
    return document


async def get_status(db: AsyncSession, document_id: UUID) -> dict[str, Any]:
    """Return ingestion status for polling."""
    document = await get_document(db, document_id)
    return {
        "document_id": str(document.id),
        "status": document.status.value,
        "chunk_count": document.chunk_count,
        "error_message": document.error_message,
    }


def parse_allowed_groups(raw: str | None) -> list[str]:
    """Parse allowed_groups from multipart JSON string."""
    if not raw or not raw.strip():
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValidationError(
            "allowed_groups must be a JSON array string",
            details={"value": raw},
        ) from exc
    if not isinstance(parsed, list):
        raise ValidationError("allowed_groups must be a JSON array")
    return [str(g) for g in parsed]
