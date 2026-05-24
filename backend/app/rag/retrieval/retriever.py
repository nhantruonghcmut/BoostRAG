"""Retriever skeleton — orchestrates embed + vector search with ACL."""

from __future__ import annotations

from app.rag.llm.embedder import EmbeddingProvider, get_embedding_provider
from app.rag.retrieval.acl_filter import ACLFilter
from app.rag.retrieval.vector_store import ScoredChunk, VectorStore, get_vector_store


class Retriever:
    """Skeleton retriever — embed query rồi search với ACL filter mandatory."""

    def __init__(
        self,
        *,
        vector_store: VectorStore | None = None,
        embedder: EmbeddingProvider | None = None,
    ) -> None:
        self._vector_store = vector_store or get_vector_store()
        self._embedder = embedder or get_embedding_provider()

    async def retrieve_with_acl(
        self,
        query: str,
        acl: ACLFilter,
        top_k: int = 20,
    ) -> list[ScoredChunk]:
        """Retrieve top-k chunks matching query, filtered by ACL."""
        vectors = await self._embedder.embed([query])
        if not vectors:
            return []
        return self._vector_store.search(vectors[0], top_k, acl)
