"""Qdrant vector store wrapper — upsert, search (ACL mandatory), delete."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, TypedDict, cast, runtime_checkable

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.core.config import settings
from app.core.logging import get_logger
from app.rag.retrieval.acl_filter import ACLFilter

logger = get_logger(__name__)


class ChunkPayload(TypedDict):
    """Payload stored alongside vector in Qdrant."""

    document_id: str
    document_name: str
    chunk_index: int
    text: str
    page_number: int | None
    section_path: list[str]
    heading_context: str
    required_level: int
    allowed_groups: list[str]
    uploaded_by: str
    uploaded_at: str


@dataclass(frozen=True)
class ChunkUpsert:
    """Single point to upsert into Qdrant."""

    point_id: str
    vector: list[float]
    payload: ChunkPayload


@dataclass(frozen=True)
class ScoredChunk:
    """Search result chunk with score."""

    point_id: str
    score: float
    payload: ChunkPayload


@runtime_checkable
class VectorStore(Protocol):
    """Protocol for vector store operations."""

    def upsert(self, chunks: list[ChunkUpsert]) -> None: ...
    def search(
        self,
        query_vec: list[float],
        top_k: int,
        acl_filter: ACLFilter,
    ) -> list[ScoredChunk]: ...
    def delete_by_document(self, document_id: str) -> None: ...


def _build_qdrant_filter(acl: ACLFilter) -> qmodels.Filter:
    """Convert ACLFilter to Qdrant Filter model."""
    spec = acl.to_qdrant_filter()
    must = [_dict_to_condition(c) for c in spec.get("must", [])]
    should = [_dict_to_condition(c) for c in spec.get("should", [])]
    return qmodels.Filter(
        must=must,
        should=should,
        min_should=qmodels.MinShould(
            conditions=should,
            min_count=spec.get("minimum_should_match", 1),
        )
        if should
        else None,
    )


def _dict_to_condition(d: dict[str, Any]) -> qmodels.Condition:
    if "key" in d and "range" in d:
        return qmodels.FieldCondition(
            key=d["key"],
            range=qmodels.Range(**d["range"]),
        )
    if "key" in d and "match" in d:
        return qmodels.FieldCondition(
            key=d["key"],
            match=qmodels.MatchAny(any=d["match"]["any"]),
        )
    if "is_empty" in d:
        return qmodels.IsEmptyCondition(
            is_empty=qmodels.PayloadField(key=d["is_empty"]["key"]),
        )
    msg = f"Unsupported filter condition: {d}"
    raise ValueError(msg)


class QdrantVectorStore:
    """Production Qdrant wrapper — ACL filter mandatory on search."""

    def __init__(
        self,
        *,
        collection: str | None = None,
        client: QdrantClient | None = None,
    ) -> None:
        self.collection = collection or settings.qdrant_collection_name
        self._client = client or QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
        )

    def upsert(self, chunks: list[ChunkUpsert]) -> None:
        if not chunks:
            return
        points = [
            qmodels.PointStruct(
                id=chunk.point_id,
                vector=chunk.vector,
                payload=dict(chunk.payload),
            )
            for chunk in chunks
        ]
        self._client.upsert(collection_name=self.collection, points=points)
        logger.info(
            "vector_store.upsert", collection=self.collection, count=len(points)
        )

    def search(
        self,
        query_vec: list[float],
        top_k: int,
        acl_filter: ACLFilter,
    ) -> list[ScoredChunk]:
        qfilter = _build_qdrant_filter(acl_filter)
        response = self._client.query_points(
            collection_name=self.collection,
            query=query_vec,
            query_filter=qfilter,
            limit=top_k,
            with_payload=True,
        )
        return [
            ScoredChunk(
                point_id=str(hit.id),
                score=float(hit.score or 0.0),
                payload=cast("ChunkPayload", dict(hit.payload or {})),
            )
            for hit in response.points
        ]

    def delete_by_document(self, document_id: str) -> None:
        self._client.delete(
            collection_name=self.collection,
            points_selector=qmodels.FilterSelector(
                filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="document_id",
                            match=qmodels.MatchValue(value=document_id),
                        ),
                    ],
                ),
            ),
        )
        logger.info("vector_store.delete_by_document", document_id=document_id)


class InMemoryVectorStore:
    """In-memory vector store for tests."""

    def __init__(self) -> None:
        self._points: dict[str, ChunkUpsert] = {}

    def upsert(self, chunks: list[ChunkUpsert]) -> None:
        for chunk in chunks:
            self._points[chunk.point_id] = chunk

    def search(
        self,
        query_vec: list[float],
        top_k: int,
        acl_filter: ACLFilter,
    ) -> list[ScoredChunk]:
        del query_vec
        results: list[ScoredChunk] = []
        for point_id, chunk in self._points.items():
            payload = chunk.payload
            if payload["required_level"] > acl_filter.max_level:
                continue
            allowed = payload.get("allowed_groups", [])
            if allowed and not set(allowed) & set(acl_filter.groups):
                continue
            results.append(
                ScoredChunk(point_id=point_id, score=1.0, payload=payload),
            )
        return results[:top_k]

    def delete_by_document(self, document_id: str) -> None:
        to_delete = [
            pid
            for pid, c in self._points.items()
            if c.payload["document_id"] == document_id
        ]
        for pid in to_delete:
            del self._points[pid]

    def count(self) -> int:
        return len(self._points)


def get_vector_store(*, in_memory: bool = False) -> VectorStore:
    """Factory for vector store."""
    if in_memory or settings.is_test():
        return InMemoryVectorStore()
    return QdrantVectorStore()
