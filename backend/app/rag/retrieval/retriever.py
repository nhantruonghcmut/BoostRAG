"""Retriever — embed query → Qdrant search → mandatory rerank → context cut."""

from __future__ import annotations

import time

from app.core.config import settings
from app.core.logging import get_logger
from app.rag.llm.embedder import EmbeddingProvider, get_embedding_provider
from app.rag.retrieval.acl_filter import ACLFilter
from app.rag.retrieval.reranker import Reranker, RetrievedChunk, get_reranker
from app.rag.retrieval.vector_store import ScoredChunk, VectorStore, get_vector_store

logger = get_logger(__name__)


class Retriever:
    """Orchestrates embed + vector search + mandatory rerank."""

    def __init__(
        self,
        *,
        vector_store: VectorStore | None = None,
        embedder: EmbeddingProvider | None = None,
        reranker: Reranker | None = None,
        top_k_search: int | None = None,
        top_k_rerank: int | None = None,
        top_k_context: int | None = None,
    ) -> None:
        self._vector_store = vector_store or get_vector_store()
        self._embedder = embedder or get_embedding_provider()
        self._reranker = reranker or get_reranker()
        self.top_k_search = top_k_search or settings.top_k_search
        self.top_k_rerank = top_k_rerank or settings.top_k_rerank
        self.top_k_context = top_k_context or settings.top_k_context

    def _to_retrieved(self, raw: ScoredChunk) -> RetrievedChunk:
        payload = raw.payload
        return RetrievedChunk(
            chunk_id=raw.point_id,
            document_id=payload["document_id"],
            document_name=payload["document_name"],
            text=payload["text"],
            page_number=payload.get("page_number"),
            section_path=list(payload.get("section_path", [])),
            heading_context=payload.get("heading_context", ""),
            vector_score=raw.score,
        )

    async def retrieve_with_acl(
        self,
        query: str,
        acl: ACLFilter,
    ) -> tuple[list[RetrievedChunk], list[RetrievedChunk], dict[str, int]]:
        """Retrieve chunks: search → rerank → assign citation_ids.

        Args:
            query: User question.
            acl: ACL filter from fresh DB load.

        Returns:
            Tuple of (all_reranked_chunks, context_chunks, latency_breakdown_ms).
        """
        breakdown: dict[str, int] = {}
        t0 = time.perf_counter()

        t_embed = time.perf_counter()
        vectors = await self._embedder.embed([query])
        breakdown["embed_query_ms"] = int((time.perf_counter() - t_embed) * 1000)

        if not vectors:
            return [], [], breakdown

        t_search = time.perf_counter()
        raw_chunks = self._vector_store.search(
            vectors[0],
            self.top_k_search,
            acl,
        )
        breakdown["qdrant_search_ms"] = int((time.perf_counter() - t_search) * 1000)

        retrieved = [self._to_retrieved(c) for c in raw_chunks]

        t_rerank = time.perf_counter()
        reranked = await self._reranker.rerank(query, retrieved, self.top_k_rerank)
        breakdown["rerank_ms"] = int((time.perf_counter() - t_rerank) * 1000)

        context_chunks = reranked[: self.top_k_context]
        for idx, chunk in enumerate(context_chunks, start=1):
            chunk.citation_id = idx

        breakdown["retrieve_total_ms"] = int((time.perf_counter() - t0) * 1000)

        logger.info(
            "rag.retrieve",
            raw_count=len(raw_chunks),
            after_rerank=len(reranked),
            context_count=len(context_chunks),
            latency_ms=breakdown["retrieve_total_ms"],
        )
        return reranked, context_chunks, breakdown
