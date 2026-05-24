"""Celery ingestion tasks — parse, chunk, embed, upsert."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.core.storage import get_storage_client
from app.rag.ingestion.pipeline import run_ingestion
from app.rag.llm.embedder import get_embedding_provider
from app.rag.retrieval.vector_store import get_vector_store
from app.workers.celery_app import celery_app
from app.workers.db import get_sync_db

logger = get_logger(__name__)


@celery_app.task(name="boostrag.ingestion.parse_and_embed_document", bind=True)  # type: ignore[untyped-decorator]
def parse_and_embed_document(self: Any, document_id: str) -> dict[str, str]:
    """Parse and embed document — idempotent (delete old points before upsert).

    Args:
        document_id: UUID string of document to process.

    Returns:
        Status dict with document_id and result.
    """
    logger.info(
        "ingestion.task.start", document_id=document_id, task_id=self.request.id
    )
    storage = get_storage_client()
    vector_store = get_vector_store()
    embedder = get_embedding_provider()

    with get_sync_db() as db:
        run_ingestion(
            UUID(document_id),
            db=db,
            storage=storage,
            vector_store=vector_store,
            embedder=embedder,
        )

    logger.info("ingestion.task.done", document_id=document_id)
    return {"document_id": document_id, "status": "done"}
