"""Unit tests for retriever ACL filtering."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.rag.llm.embedder import FakeEmbedder
from app.rag.retrieval.acl_filter import ACLFilter
from app.rag.retrieval.reranker import FakeReranker
from app.rag.retrieval.retriever import Retriever
from app.rag.retrieval.vector_store import ChunkPayload, ChunkUpsert, InMemoryVectorStore


def _payload(
    *,
    doc_id: str,
    level: int,
    groups: list[str],
    text: str = "sample text",
) -> ChunkPayload:
    return ChunkPayload(
        document_id=doc_id,
        document_name="Test Doc",
        chunk_index=0,
        text=text,
        page_number=1,
        section_path=[],
        heading_context="",
        required_level=level,
        allowed_groups=groups,
        uploaded_by=str(uuid4()),
        uploaded_at="2026-01-01T00:00:00Z",
    )


@pytest.fixture
def seeded_store() -> InMemoryVectorStore:
    store = InMemoryVectorStore()
    store.upsert(
        [
            ChunkUpsert(
                point_id="low-public",
                vector=[1.0] * 8,
                payload=_payload(doc_id="d1", level=1, groups=[]),
            ),
            ChunkUpsert(
                point_id="high-hr",
                vector=[1.0] * 8,
                payload=_payload(doc_id="d2", level=3, groups=["HR"], text="HR secret"),
            ),
            ChunkUpsert(
                point_id="high-finance",
                vector=[1.0] * 8,
                payload=_payload(
                    doc_id="d3", level=3, groups=["Finance"], text="Finance secret"
                ),
            ),
        ],
    )
    return store


async def test_user_level1_cannot_retrieve_level3(seeded_store: InMemoryVectorStore) -> None:
    retriever = Retriever(
        vector_store=seeded_store,
        embedder=FakeEmbedder(),
        reranker=FakeReranker(),
    )
    acl = ACLFilter(max_level=1, groups=["HR"])
    reranked, context, _ = await retriever.retrieve_with_acl("query", acl)
    chunk_ids = {c.chunk_id for c in reranked}
    assert "high-hr" not in chunk_ids
    assert "high-finance" not in chunk_ids
    assert "low-public" in chunk_ids
    assert len(context) <= 1


async def test_user_level5_hr_sees_hr_doc(seeded_store: InMemoryVectorStore) -> None:
    retriever = Retriever(
        vector_store=seeded_store,
        embedder=FakeEmbedder(),
        reranker=FakeReranker(),
    )
    acl = ACLFilter(max_level=5, groups=["HR"])
    reranked, context, _ = await retriever.retrieve_with_acl("query", acl)
    chunk_ids = {c.chunk_id for c in reranked}
    assert "high-hr" in chunk_ids
    assert "high-finance" not in chunk_ids


async def test_public_doc_visible_to_all(seeded_store: InMemoryVectorStore) -> None:
    retriever = Retriever(
        vector_store=seeded_store,
        embedder=FakeEmbedder(),
        reranker=FakeReranker(),
    )
    acl = ACLFilter(max_level=1, groups=[])
    reranked, _, _ = await retriever.retrieve_with_acl("query", acl)
    assert any(c.chunk_id == "low-public" for c in reranked)
