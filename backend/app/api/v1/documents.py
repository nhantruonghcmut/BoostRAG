"""User-facing document endpoints — ACL filtered."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from app.core.deps import DbSession, require_active_user
from app.models.document import Document
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.document import DocumentListItem
from app.services import document_service

router = APIRouter(prefix="/documents", tags=["documents"])


def _to_list_item(doc: Document) -> DocumentListItem:
    return DocumentListItem(
        document_id=doc.id,
        name=doc.name,
        size_bytes=doc.size_bytes,
        uploaded_at=doc.created_at,
        status=doc.status,
        required_level=doc.required_level,
        allowed_groups=doc.allowed_groups or [],
    )


@router.get("", response_model=PaginatedResponse[DocumentListItem])
async def list_documents(
    db: DbSession,
    user: Annotated[User, Depends(require_active_user)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 20,
) -> PaginatedResponse[DocumentListItem]:
    """List documents user có quyền đọc (ACL filtered)."""
    items, total = await document_service.list_documents(
        db,
        user=user,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse[DocumentListItem](
        items=[_to_list_item(d) for d in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{document_id}/file")
async def download_document_file(
    document_id: UUID,
    db: DbSession,
    user: Annotated[User, Depends(require_active_user)],
) -> Response:
    """Download file gốc — re-check ACL trước khi serve."""
    from app.core.storage import get_storage_client

    doc = await document_service.get_document(db, document_id, user=user)
    storage = get_storage_client()
    data = storage.download(doc.storage_key)
    return Response(
        content=data,
        media_type=doc.mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{doc.original_filename}"',
        },
    )
