"""RAG engine — sanitize → retrieve → generate → stream events."""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Literal
from uuid import UUID, uuid4

from langdetect import DetectorFactory, detect

from app.core.config import settings
from app.core.logging import get_logger
from app.rag.guardrails.injection import detect_injection
from app.rag.guardrails.messages import NO_CONTEXT, POLITE_FALLBACK, POLITE_REFUSAL
from app.rag.guardrails.system_prompt import (
    build_system_prompt,
    format_context_block,
    wrap_user_query,
)
from app.rag.llm.embedder import EmbeddingProvider, get_embedding_provider
from app.rag.llm.provider import LLMProvider, Message, get_llm_provider
from app.rag.retrieval.acl_filter import ACLFilter
from app.rag.retrieval.reranker import RetrievedChunk
from app.rag.retrieval.retriever import Retriever

DetectorFactory.seed = 0

logger = get_logger(__name__)

FINAL_PROMPT_MAX_CHARS = 100_000


@dataclass(frozen=True)
class UserContext:
    """User ACL context passed from service layer."""

    user_id: UUID
    access_level: int
    groups: list[str]


@dataclass
class RunOptions:
    """Options for a single RAG run."""

    message_id: UUID = field(default_factory=uuid4)
    include_debug: bool = False
    history: list[dict[str, str]] = field(default_factory=list)


@dataclass
class CitationData:
    """Citation emitted to client."""

    citation_id: int
    document_id: str
    doc_name: str
    page: int | None = None


@dataclass
class TraceData:
    """Data for ChunkTrace persistence."""

    query: str
    embedding_model: str
    llm_model: str
    retrieved_chunks: list[dict[str, Any]]
    used_chunks: list[dict[str, Any]]
    final_prompt: str
    tool_calls: list[dict[str, Any]] | None
    latency_ms: int
    latency_breakdown: dict[str, int]
    token_usage: dict[str, int]


@dataclass
class EngineEvent:
    """Base SSE engine event."""

    event: str
    data: Any


def _detect_language(text: str) -> str:
    try:
        lang = detect(text)
        return "vi" if lang.startswith("vi") else "en"
    except Exception:
        return "vi"


def _format_history(history: list[dict[str, str]], max_turns: int = 6) -> str:
    recent = history[-max_turns:]
    lines: list[str] = []
    for msg in recent:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        lines.append(f"{role}: {content[:500]}")
    return "\n".join(lines)


class RAGEngine:
    """RAG orchestrator — always calls mandatory rerank via Retriever."""

    def __init__(
        self,
        *,
        retriever: Retriever | None = None,
        llm: LLMProvider | None = None,
        embedder: EmbeddingProvider | None = None,
    ) -> None:
        self._retriever = retriever or Retriever()
        self._llm = llm or get_llm_provider()
        self._embedder = embedder or get_embedding_provider()

    async def run(
        self,
        query: str,
        user: UserContext,
        options: RunOptions | None = None,
    ) -> AsyncIterator[EngineEvent]:
        """Execute RAG pipeline and yield SSE-compatible events."""
        opts = options or RunOptions()
        message_id = opts.message_id
        lang = _detect_language(query)
        latency_breakdown: dict[str, int] = {}
        t_total = time.perf_counter()

        # Layer 1: sanitize + detect injection
        t0 = time.perf_counter()
        injection = detect_injection(query)
        latency_breakdown["sanitize_ms"] = int((time.perf_counter() - t0) * 1000)

        if injection.is_injection and settings.injection_check != "off":
            logger.warning(
                "rag.injection_detected",
                patterns=injection.matched_patterns,
                user_id=str(user.user_id),
            )
            refusal = POLITE_REFUSAL.get(lang, POLITE_REFUSAL["en"])
            yield EngineEvent(
                event="start",
                data={"message_id": str(message_id), "model": self._llm.model},
            )
            yield EngineEvent(event="token", data={"text": refusal})
            yield EngineEvent(
                event="citations",
                data=[],
            )
            yield EngineEvent(
                event="done",
                data={
                    "message_id": str(message_id),
                    "usage": {"prompt_tokens": 0, "completion_tokens": 0},
                    "latency_ms": int((time.perf_counter() - t_total) * 1000),
                    "content": refusal,
                    "error_code": "PROMPT_INJECTION_DETECTED",
                    "trace": None,
                },
            )
            return

        sanitized = injection.sanitized_text
        acl = ACLFilter(max_level=user.access_level, groups=user.groups)

        # Retrieve with mandatory rerank
        reranked, context_chunks, retrieve_latency = await self._retriever.retrieve_with_acl(
            sanitized,
            acl,
        )
        latency_breakdown.update(retrieve_latency)

        llm_model = getattr(self._llm, "model", settings.default_llm_model)

        # Zero chunks → polite no-context (skip LLM)
        if not context_chunks:
            no_ctx = NO_CONTEXT.get(lang, NO_CONTEXT["en"])
            trace = TraceData(
                query=sanitized,
                embedding_model=self._embedder.name,
                llm_model=llm_model,
                retrieved_chunks=[c.to_dict() for c in reranked],
                used_chunks=[],
                final_prompt="",
                tool_calls=None,
                latency_ms=int((time.perf_counter() - t_total) * 1000),
                latency_breakdown=latency_breakdown,
                token_usage={"prompt_tokens": 0, "completion_tokens": 0},
            )
            yield EngineEvent(
                event="start",
                data={"message_id": str(message_id), "model": llm_model},
            )
            yield EngineEvent(event="token", data={"text": no_ctx})
            yield EngineEvent(event="citations", data=[])
            yield EngineEvent(
                event="done",
                data={
                    "message_id": str(message_id),
                    "usage": {"prompt_tokens": 0, "completion_tokens": 0},
                    "latency_ms": trace.latency_ms,
                    "content": no_ctx,
                    "error_code": "NO_CONTEXT_FOUND",
                    "trace": trace,
                },
            )
            return

        # Build prompt
        context_dicts = [c.to_dict() for c in context_chunks]
        numbered_context = format_context_block(context_dicts)
        history_text = _format_history(opts.history)
        system_prompt = build_system_prompt(
            numbered_context=numbered_context,
            truncated_history=history_text,
        )
        user_message = wrap_user_query(sanitized)
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_message),
        ]
        final_prompt = f"{system_prompt}\n\n{user_message}"
        if len(final_prompt) > FINAL_PROMPT_MAX_CHARS:
            final_prompt = final_prompt[:FINAL_PROMPT_MAX_CHARS]

        citations = _build_citations(context_chunks)
        full_text = ""
        token_usage: dict[str, int] = {"prompt_tokens": 0, "completion_tokens": 0}
        error_code: str | None = None

        yield EngineEvent(
            event="start",
            data={"message_id": str(message_id), "model": llm_model},
        )

        t_llm = time.perf_counter()
        first_token_ms: int | None = None

        try:
            async with asyncio.timeout(settings.llm_timeout_s):
                async for stream_event in self._llm.stream_complete(messages):
                    if stream_event.type == "token" and stream_event.text:
                        if first_token_ms is None:
                            first_token_ms = int((time.perf_counter() - t_llm) * 1000)
                        full_text += stream_event.text
                        yield EngineEvent(
                            event="token",
                            data={"text": stream_event.text},
                        )
                    elif stream_event.type == "done":
                        token_usage = stream_event.usage or token_usage
        except TimeoutError:
            logger.warning("llm.timeout", user_id=str(user.user_id))
            error_code = "LLM_TIMEOUT"
            fallback = POLITE_FALLBACK.get(lang, POLITE_FALLBACK["en"])
            if not full_text:
                full_text = fallback
                yield EngineEvent(event="token", data={"text": fallback})
        except Exception:
            logger.exception("llm.error", user_id=str(user.user_id))
            error_code = "LLM_ERROR"
            fallback = POLITE_FALLBACK.get(lang, POLITE_FALLBACK["en"])
            if not full_text:
                full_text = fallback
                yield EngineEvent(event="token", data={"text": fallback})

        llm_total_ms = int((time.perf_counter() - t_llm) * 1000)
        latency_breakdown["llm_first_token_ms"] = first_token_ms or llm_total_ms
        latency_breakdown["llm_total_ms"] = llm_total_ms
        total_ms = int((time.perf_counter() - t_total) * 1000)
        latency_breakdown["total_ms"] = total_ms

        citation_payload = [
            {
                "citation_id": c.citation_id,
                "document_id": c.document_id,
                "doc_name": c.doc_name,
                "page": c.page,
            }
            for c in citations
        ]
        yield EngineEvent(event="citations", data=citation_payload)

        trace = TraceData(
            query=sanitized,
            embedding_model=self._embedder.name,
            llm_model=llm_model,
            retrieved_chunks=[c.to_dict() for c in reranked],
            used_chunks=[c.to_dict() for c in context_chunks],
            final_prompt=final_prompt,
            tool_calls=None,
            latency_ms=total_ms,
            latency_breakdown=latency_breakdown,
            token_usage=token_usage,
        )

        yield EngineEvent(
            event="done",
            data={
                "message_id": str(message_id),
                "usage": token_usage,
                "latency_ms": total_ms,
                "content": full_text,
                "error_code": error_code,
                "trace": trace,
                "citations": citation_payload,
            },
        )


def _build_citations(chunks: list[RetrievedChunk]) -> list[CitationData]:
    return [
        CitationData(
            citation_id=c.citation_id,
            document_id=c.document_id,
            doc_name=c.document_name,
            page=c.page_number,
        )
        for c in chunks
    ]
