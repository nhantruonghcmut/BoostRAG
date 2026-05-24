"""Ingestion pipeline — parse → chunk → embed → upsert Qdrant."""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.exceptions import IngestionError
from app.core.logging import get_logger
from app.models.document import Document, DocumentChunk, DocumentStatus
from app.rag.ingestion.chunker import Chunk, StructuralChunker
from app.rag.ingestion.parsers import get_parser
from app.rag.llm.embedder import EmbeddingProvider, get_embedding_provider
from app.rag.retrieval.vector_store import (
    ChunkPayload,
    ChunkUpsert,
    VectorStore,
    get_vector_store,
)

if TYPE_CHECKING:
    from app.core.storage import StorageClient

logger = get_logger(__name__)


def _text_to_embed(chunk: Chunk) -> str:
    if chunk.heading_context:
        return f"{chunk.heading_context}\n\n{chunk.text}"
    return chunk.text


class IngestionPipeline:
    """Orchestrate document ingestion with status transitions."""

    def __init__(
        self,
        *,
        db: Session,
        storage: StorageClient,
        vector_store: VectorStore | None = None,
        embedder: EmbeddingProvider | None = None,
        chunker: StructuralChunker | None = None,
    ) -> None:
        self._db = db
        self._storage = storage
        self._vector_store = vector_store or get_vector_store()
        self._embedder = embedder or get_embedding_provider()
        self._chunker = chunker or StructuralChunker()

    def run(self, document_id: UUID) -> None:
        """Run full ingestion pipeline — idempotent (delete old points first)."""
        document = self._db.get(Document, document_id)
        if document is None:
            msg = f"Document not found: {document_id}"
            raise IngestionError(msg, details={"document_id": str(document_id)})

        try:
            self._vector_store.delete_by_document(str(document_id))
            self._clear_chunk_rows(document_id)

            self._set_status(document, DocumentStatus.PARSING)
            chunks = self._parse_and_chunk(document)

            self._set_status(document, DocumentStatus.EMBEDDING)
            self._embed_and_upsert(document, chunks)

            document.chunk_count = len(chunks)
            document.error_message = None
            self._set_status(document, DocumentStatus.READY)
            logger.info(
                "ingestion.complete",
                document_id=str(document_id),
                chunk_count=len(chunks),
            )
        except Exception as exc:
            document.status = DocumentStatus.FAILED
            document.error_message = str(exc)[:2000]
            self._db.commit()
            logger.exception("ingestion.failed", document_id=str(document_id))
            raise IngestionError(
                f"Ingestion failed: {exc}",
                details={"document_id": str(document_id)},
            ) from exc

    def _set_status(self, document: Document, status: DocumentStatus) -> None:
        document.status = status
        self._db.commit()
        self._db.refresh(document)

    def _clear_chunk_rows(self, document_id: UUID) -> None:
        self._db.execute(
            delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
        )
        self._db.commit()

    def _parse_and_chunk(self, document: Document) -> list[Chunk]:
        suffix = Path(document.original_filename).suffix or ".bin"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp_path = Path(tmp.name)
            data = self._storage.download(document.storage_key)
            tmp.write(data)

        try:
            parser = get_parser(document.mime_type)
            parsed = parser.parse(tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)

        self._set_status(document, DocumentStatus.CHUNKING)
        return self._chunker.chunk(parsed, str(document.id))

    def _embed_and_upsert(self, document: Document, chunks: list[Chunk]) -> None:
        if not chunks:
            return

        texts = [_text_to_embed(c) for c in chunks]
        import asyncio

        vectors = asyncio.run(self._embedder.embed(texts))

        upserts: list[ChunkUpsert] = []
        chunk_rows: list[DocumentChunk] = []
        uploaded_at = (
            document.created_at.isoformat()
            if document.created_at
            else datetime.now(tz=UTC).isoformat()
        )

        for idx, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True)):
            payload: ChunkPayload = {
                "document_id": str(document.id),
                "document_name": document.name,
                "chunk_index": idx,
                "text": chunk.text,
                "page_number": chunk.page_number,
                "section_path": chunk.section_path,
                "heading_context": chunk.heading_context,
                "required_level": document.required_level,
                "allowed_groups": document.allowed_groups or [],
                "uploaded_by": str(document.uploaded_by)
                if document.uploaded_by
                else "",
                "uploaded_at": uploaded_at,
            }
            upserts.append(
                ChunkUpsert(point_id=chunk.chunk_id, vector=vector, payload=payload),
            )
            chunk_rows.append(
                DocumentChunk(
                    document_id=document.id,
                    chunk_index=idx,
                    page_number=chunk.page_number,
                    section_path=chunk.section_path,
                    qdrant_point_id=chunk.chunk_id,
                ),
            )

        self._vector_store.upsert(upserts)
        self._db.add_all(chunk_rows)
        self._db.commit()


def run_ingestion(
    document_id: UUID,
    *,
    db: Session,
    storage: StorageClient,
    vector_store: VectorStore | None = None,
    embedder: EmbeddingProvider | None = None,
) -> None:
    """Convenience entrypoint for Celery task."""
    pipeline = IngestionPipeline(
        db=db,
        storage=storage,
        vector_store=vector_store,
        embedder=embedder,
    )
    pipeline.run(document_id)
