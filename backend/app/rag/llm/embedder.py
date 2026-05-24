"""Embedding providers — LiteLLM + FakeEmbedder for tests."""

from __future__ import annotations

import hashlib
from typing import Protocol, runtime_checkable

import litellm

from app.core.config import settings
from app.core.exceptions import LLMError
from app.core.logging import get_logger

logger = get_logger(__name__)

# Known dimensions for common models
_EMBEDDING_DIMENSIONS: dict[str, int] = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-004": 768,
    "nomic-embed-text": 768,
    "bge-m3": 1024,
}


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Protocol cho embedding provider."""

    name: str
    dimension: int
    max_batch_size: int

    async def embed(self, texts: list[str]) -> list[list[float]]: ...


class LiteLLMEmbedding:
    """Embedding via LiteLLM — supports OpenAI, Google, Ollama, etc."""

    def __init__(
        self,
        *,
        provider: str | None = None,
        model: str | None = None,
        max_batch_size: int = 64,
    ) -> None:
        self.provider = provider or settings.default_embedding_provider
        self.model = model or settings.default_embedding_model
        self.name = f"{self.provider}/{self.model}"
        self.dimension = _EMBEDDING_DIMENSIONS.get(self.model, 1536)
        self.max_batch_size = max_batch_size

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed texts in batches via LiteLLM."""
        if not texts:
            return []

        results: list[list[float]] = []
        for i in range(0, len(texts), self.max_batch_size):
            batch = texts[i : i + self.max_batch_size]
            try:
                response = await litellm.aembedding(
                    model=f"{self.provider}/{self.model}",
                    input=batch,
                )
                batch_vectors = [item["embedding"] for item in response.data]
                results.extend(batch_vectors)
            except Exception as exc:
                logger.exception(
                    "embedder.failed", model=self.model, batch_size=len(batch)
                )
                raise LLMError(f"Embedding failed: {exc}") from exc
        return results


class FakeEmbedder:
    """Deterministic fake embedder for tests — không gọi external API."""

    name = "fake/test"
    dimension = 8
    max_batch_size = 128

    async def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            digest = hashlib.sha256(text.encode()).digest()
            vec = [float(b) / 255.0 for b in digest[: self.dimension]]
            vectors.append(vec)
        return vectors


def get_embedding_provider(*, use_fake: bool = False) -> EmbeddingProvider:
    """Factory — trả embedder theo config hoặc fake cho test."""
    if use_fake or settings.is_test():
        return FakeEmbedder()
    return LiteLLMEmbedding()
