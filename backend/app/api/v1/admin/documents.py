"""Admin document management endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status

from app.core.deps import DbSession, require_admin
from app.models.document import Document
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.document import (
    DocumentListItem,
    DocumentRead,
    DocumentUpdate,
    DocumentUploadResponse,
)
from app.services import document_service

router = APIRouter(
    prefix="/admin/documents",
    tags=["admin-documents"],
    dependencies=[Depends(require_admin)],
)


def _to_list_item(doc: Document) -> DocumentListItem:
    return DocumentListItem(
        document_id=doc.id,
        name=doc.name,
        size_bytes=doc.size_bytes,
        uploaded_at=doc.created_at,
        status=doc.status,
        required_level=doc.required_level,
        allowed_groups=doc.allowed_groups or [],
        mime_type=doc.mime_type,
    )


@router.post(
    "", response_model=DocumentUploadResponse, status_code=status.HTTP_202_ACCEPTED
)
async def upload_document(
    db: DbSession,
    admin: Annotated[User, Depends(require_admin)],
    file: Annotated[UploadFile, File()],
    required_level: Annotated[int, Form(ge=1, le=5)] = 1,
    allowed_groups: Annotated[str | None, Form()] = None,
    name: Annotated[str | None, Form()] = None,
) -> DocumentUploadResponse:
    """Upload file multipart + ACL metadata — trả 202 + document_id."""
    groups = document_service.parse_allowed_groups(allowed_groups)
    doc = await document_service.upload_document(
        db,
        file=file,
        uploaded_by=admin,
        required_level=required_level,
        allowed_groups=groups,
        name=name,
    )
    return DocumentUploadResponse(document_id=doc.id, status=doc.status)


@router.get("", response_model=PaginatedResponse[DocumentListItem])
async def list_documents(
    db: DbSession,
    admin: Annotated[User, Depends(require_admin)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 20,
) -> PaginatedResponse[DocumentListItem]:
    """List tất cả documents (admin xem hết)."""
    items, total = await document_service.list_documents(
        db,
        user=admin,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse[DocumentListItem](
        items=[_to_list_item(d) for d in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{document_id}", response_model=DocumentRead)
async def get_document(document_id: UUID, db: DbSession) -> DocumentRead:
    """Detail document + ingestion status."""
    doc = await document_service.get_document(db, document_id)
    return DocumentRead.model_validate(doc)


@router.patch("/{document_id}", response_model=DocumentRead)
async def update_document_acl(
    document_id: UUID,
    payload: DocumentUpdate,
    db: DbSession,
) -> DocumentRead:
    """Update ACL (required_level, allowed_groups)."""
    doc = await document_service.update_document_acl(db, document_id, payload)
    return DocumentRead.model_validate(doc)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(document_id: UUID, db: DbSession) -> None:
    """Hard delete document + vectors + MinIO file."""
    await document_service.delete_document(db, document_id)


@router.post(
    "/{document_id}/reindex",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def reindex_document(document_id: UUID, db: DbSession) -> DocumentUploadResponse:
    """Re-run ingestion pipeline."""
    doc = await document_service.reindex_document(db, document_id)
    return DocumentUploadResponse(document_id=doc.id, status=doc.status)
