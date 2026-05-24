"""Integration tests for document upload and delete."""

from __future__ import annotations

from io import BytesIO
from unittest.mock import patch
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import InMemoryStorage
from app.models.document import Document, DocumentStatus
from app.models.user import User
from app.rag.retrieval.vector_store import InMemoryVectorStore


async def _login(client: AsyncClient, email: str, password: str) -> str:
    resp = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.fixture
def memory_storage() -> InMemoryStorage:
    return InMemoryStorage()


@pytest.fixture
def memory_vector_store() -> InMemoryVectorStore:
    return InMemoryVectorStore()


async def test_upload_document_returns_202(
    client: AsyncClient,
    admin_user: User,
    memory_storage: InMemoryStorage,
) -> None:
    """Admin upload trả 202 + document_id."""
    token = await _login(client, admin_user.email, "AdminPass123")
    content = b"I. Section\nHello world test content."

    with patch(
        "app.services.document_service.get_storage_client", return_value=memory_storage
    ):
        with patch(
            "app.workers.ingestion_tasks.parse_and_embed_document.delay"
        ) as mock_delay:
            mock_delay.return_value = None
            resp = await client.post(
                "/api/v1/admin/documents",
                headers={"Authorization": f"Bearer {token}"},
                files={"file": ("test.txt", BytesIO(content), "text/plain")},
                data={"required_level": "1", "allowed_groups": "[]"},
            )

    assert resp.status_code == 202
    body = resp.json()
    assert "document_id" in body
    assert body["status"] in ("pending", "PENDING")
    mock_delay.assert_called_once()


async def test_delete_document_removes_row(
    client: AsyncClient,
    admin_user: User,
    db: AsyncSession,
    memory_storage: InMemoryStorage,
    memory_vector_store: InMemoryVectorStore,
) -> None:
    """DELETE admin document trả 204 và row biến mất."""
    doc = Document(
        id=uuid4(),
        name="To Delete",
        original_filename="delete.txt",
        mime_type="text/plain",
        size_bytes=10,
        storage_key=f"documents/{uuid4()}/original.txt",
        status=DocumentStatus.READY,
        required_level=1,
        allowed_groups=[],
        uploaded_by=admin_user.id,
    )
    db.add(doc)
    await db.commit()

    token = await _login(client, admin_user.email, "AdminPass123")

    with patch(
        "app.services.document_service.get_storage_client", return_value=memory_storage
    ):
        with patch(
            "app.services.document_service.get_vector_store",
            return_value=memory_vector_store,
        ):
            resp = await client.delete(
                f"/api/v1/admin/documents/{doc.id}",
                headers={"Authorization": f"Bearer {token}"},
            )

    assert resp.status_code == 204
    again = await client.get(
        f"/api/v1/admin/documents/{doc.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert again.status_code == 404
