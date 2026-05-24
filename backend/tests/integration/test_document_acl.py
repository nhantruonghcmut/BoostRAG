"""ACL integration tests for document listing."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentStatus
from app.models.user import User


async def _login(client: AsyncClient, email: str, password: str) -> str:
    resp = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.fixture
async def level3_document(db: AsyncSession, admin_user: User) -> Document:
    doc = Document(
        id=uuid4(),
        name="Secret Doc",
        original_filename="secret.txt",
        mime_type="text/plain",
        size_bytes=100,
        storage_key=f"documents/{uuid4()}/original.txt",
        status=DocumentStatus.READY,
        required_level=3,
        allowed_groups=[],
        uploaded_by=admin_user.id,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


async def test_user_level1_cannot_list_level3_document(
    client: AsyncClient,
    active_user: User,
    level3_document: Document,
    db: AsyncSession,
) -> None:
    """User access_level=2 không thấy doc required_level=3."""
    active_user.access_level = 1
    await db.commit()
    await db.refresh(active_user)
    token = await _login(client, active_user.email, "UserPass123")

    resp = await client.get(
        "/api/v1/documents",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    ids = {item["document_id"] for item in resp.json()["items"]}
    assert str(level3_document.id) not in ids


async def test_admin_sees_all_documents(
    client: AsyncClient,
    admin_user: User,
    level3_document: Document,
) -> None:
    token = await _login(client, admin_user.email, "AdminPass123")
    resp = await client.get(
        "/api/v1/admin/documents",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    ids = {item["document_id"] for item in resp.json()["items"]}
    assert str(level3_document.id) in ids
