"""Integration tests for chat SSE streaming."""

from __future__ import annotations

import json
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def _login(client: AsyncClient, email: str, password: str) -> str:
    resp = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


def _parse_sse(body: str) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    blocks = body.strip().split("\n\n")
    for block in blocks:
        if not block.strip():
            continue
        event_type = "message"
        data: dict = {}
        for line in block.split("\n"):
            if line.startswith("event:"):
                event_type = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data = json.loads(line.split(":", 1)[1].strip())
        events.append((event_type, data))
    return events


async def test_chat_stream_zero_chunks_polite_fallback(
    client: AsyncClient,
    active_user: User,
) -> None:
    """Empty vector store → NO_CONTEXT polite message."""
    token = await _login(client, active_user.email, "UserPass123")
    resp = await client.post(
        "/api/v1/chat/stream",
        json={"query": "Câu hỏi về chính sách nghỉ phép?"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    events = _parse_sse(resp.text)
    event_types = [e[0] for e in events]
    assert "start" in event_types
    assert "token" in event_types
    assert "done" in event_types
    tokens = "".join(d.get("text", "") for t, d in events if t == "token")
    assert "Xin lỗi" in tokens or "Sorry" in tokens


async def test_create_session_and_list(
    client: AsyncClient,
    active_user: User,
) -> None:
    token = await _login(client, active_user.email, "UserPass123")
    headers = {"Authorization": f"Bearer {token}"}

    create = await client.post(
        "/api/v1/chat/sessions",
        json={"title": "Test session"},
        headers=headers,
    )
    assert create.status_code == 201
    session_id = create.json()["session_id"]

    listing = await client.get("/api/v1/chat/sessions", headers=headers)
    assert listing.status_code == 200
    ids = {item["session_id"] for item in listing.json()["items"]}
    assert session_id in ids

    msgs = await client.get(
        f"/api/v1/chat/sessions/{session_id}/messages",
        headers=headers,
    )
    assert msgs.status_code == 200
    assert msgs.json()["items"] == []


async def test_stream_with_session_persists_messages(
    client: AsyncClient,
    active_user: User,
) -> None:
    token = await _login(client, active_user.email, "UserPass123")
    headers = {"Authorization": f"Bearer {token}"}

    session_resp = await client.post(
        "/api/v1/chat/sessions",
        json={},
        headers=headers,
    )
    session_id = session_resp.json()["session_id"]

    stream = await client.post(
        "/api/v1/chat/stream",
        json={"session_id": session_id, "query": "Hello test"},
        headers=headers,
    )
    assert stream.status_code == 200
    events = _parse_sse(stream.text)
    assert any(e[0] == "done" for e in events)

    msgs = await client.get(
        f"/api/v1/chat/sessions/{session_id}/messages",
        headers=headers,
    )
    items = msgs.json()["items"]
    assert len(items) >= 2
    roles = {m["role"] for m in items}
    assert "user" in roles
    assert "assistant" in roles
