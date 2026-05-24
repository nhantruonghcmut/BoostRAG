"""Cross-encoder reranker — BGE default, mandatory in retrieval pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, cast, runtime_checkable

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RetrievedChunk:
    """Chunk after retrieval + rerank with scores and metadata."""

    chunk_id: str
    document_id: str
    document_name: str
    text: str
    page_number: int | None
    section_path: list[str]
    heading_context: str
    vector_score: float
    rerank_score: float | None = None
    citation_id: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize for JSONB storage."""
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "document_name": self.document_name,
            "text": self.text,
            "page_number": self.page_number,
            "section_path": self.section_path,
            "heading_context": self.heading_context,
            "vector_score": self.vector_score,
            "rerank_score": self.rerank_score,
            "citation_id": self.citation_id,
        }


@runtime_checkable
class Reranker(Protocol):
    """Protocol for cross-encoder reranking."""

    async def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        top_k: int,
    ) -> list[RetrievedChunk]: ...


class BGEReranker:
    """BGE-reranker-v2-m3 via sentence-transformers CrossEncoder."""

    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or settings.default_reranker_model
        self._model: object | None = None

    def _get_model(self) -> object:
        if self._model is None:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(self.model_name)
        return self._model

    async def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        top_k: int,
    ) -> list[RetrievedChunk]:
        """Rerank chunks by cross-encoder score."""
        if not chunks:
            return []

        try:
            model = cast("Any", self._get_model())
            pairs = [[query, c.text] for c in chunks]
            scores = model.predict(pairs)
            scored = sorted(
                zip(chunks, scores, strict=False),
                key=lambda x: float(x[1]),
                reverse=True,
            )
            result: list[RetrievedChunk] = []
            for chunk, score in scored[:top_k]:
                chunk.rerank_score = float(score)
                result.append(chunk)
            return result
        except Exception:
            logger.warning(
                "reranker.fallback",
                model=self.model_name,
                reason="rerank_failed_using_vector_score",
            )
            fallback = sorted(chunks, key=lambda c: c.vector_score, reverse=True)
            for chunk in fallback[:top_k]:
                chunk.rerank_score = chunk.vector_score
            return fallback[:top_k]


class FakeReranker:
    """Test reranker — preserves vector score order."""

    async def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        top_k: int,
    ) -> list[RetrievedChunk]:
        del query
        sorted_chunks = sorted(chunks, key=lambda c: c.vector_score, reverse=True)
        for chunk in sorted_chunks[:top_k]:
            chunk.rerank_score = chunk.vector_score
        return sorted_chunks[:top_k]


def get_reranker(*, use_fake: bool = False) -> Reranker:
    """Factory for reranker."""
    if use_fake or settings.is_test():
        return FakeReranker()
    return BGEReranker()
