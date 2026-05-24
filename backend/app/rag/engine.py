"""RAG engine orchestrator (placeholder cho Phase 3).

`RAGEngine.run` sẽ implement: sanitize → embed query → vector_store.search +
ACL filter → **mandatory rerank** → build prompt (system + numbered context
+ wrapped user_query) → LLM stream → handle tool calls → save ChunkTrace.

Hiện tại chỉ định nghĩa skeleton để typing/imports khác referenc được.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from app.core.exceptions import RAGError


class RAGEngine:
    """RAG orchestrator. Sẽ impl ở Phase 3."""

    async def run(self, *_args: Any, **_kwargs: Any) -> AsyncIterator[Any]:
        """Stream events (start/token/citations/done/error).

        Raises:
            RAGError: chưa implement.
        """
        raise RAGError("RAGEngine.run is not implemented yet (Phase 3)")
        yield  # pragma: no cover — placeholder cho type checker
