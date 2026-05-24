"""LLM provider — LiteLLM streaming + FakeLLM for tests."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable

import litellm

from app.core.config import settings
from app.core.exceptions import LLMError
from app.core.logging import get_logger

logger = get_logger(__name__)

StreamEventType = Literal["token", "tool_call", "done"]


@dataclass(frozen=True)
class Message:
    """Chat message for LLM."""

    role: Literal["system", "user", "assistant"]
    content: str


@dataclass(frozen=True)
class StreamEvent:
    """Event emitted during LLM streaming."""

    type: StreamEventType
    text: str = ""
    tool_name: str = ""
    args: dict[str, Any] = field(default_factory=dict)
    usage: dict[str, int] = field(default_factory=dict)


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol for LLM streaming completion."""

    model: str

    def stream_complete(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        **params: Any,
    ) -> AsyncIterator[StreamEvent]: ...


class LiteLLMProvider:
    """Production LLM via LiteLLM."""

    def __init__(
        self,
        *,
        provider: str | None = None,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> None:
        self.provider = provider or settings.default_llm_provider
        self.model_name = model or settings.default_llm_model
        self.model = f"{self.provider}/{self.model_name}"
        self.temperature = temperature
        self.max_tokens = max_tokens

    async def stream_complete(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        **params: Any,
    ) -> AsyncIterator[StreamEvent]:
        """Stream tokens from LiteLLM."""
        litellm_messages = [{"role": m.role, "content": m.content} for m in messages]
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": litellm_messages,
            "stream": True,
            "temperature": params.get("temperature", self.temperature),
            "max_tokens": params.get("max_tokens", self.max_tokens),
        }
        if tools:
            kwargs["tools"] = tools

        usage: dict[str, int] = {}
        try:
            response = await litellm.acompletion(**kwargs)
            async for chunk in response:
                delta = chunk.choices[0].delta
                if delta.content:
                    yield StreamEvent(type="token", text=delta.content)
                if getattr(chunk, "usage", None):
                    u = chunk.usage
                    usage = {
                        "prompt_tokens": getattr(u, "prompt_tokens", 0) or 0,
                        "completion_tokens": getattr(u, "completion_tokens", 0) or 0,
                    }
        except Exception as exc:
            logger.exception("llm.stream_failed", model=self.model)
            raise LLMError(f"LLM streaming failed: {exc}") from exc

        yield StreamEvent(type="done", usage=usage)


class FakeLLMProvider:
    """Deterministic fake LLM for tests — streams canned response."""

    model = "fake/test"

    def __init__(self, response: str = "Đây là câu trả lời thử nghiệm [1].") -> None:
        self._response = response

    async def stream_complete(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        **params: Any,
    ) -> AsyncIterator[StreamEvent]:
        del messages, tools, params
        for word in self._response.split(" "):
            yield StreamEvent(type="token", text=word + " ")
        yield StreamEvent(
            type="done",
            usage={"prompt_tokens": 10, "completion_tokens": len(self._response.split())},
        )


def get_llm_provider(*, use_fake: bool = False) -> LLMProvider:
    """Factory for LLM provider."""
    if use_fake or settings.is_test():
        return FakeLLMProvider()
    return LiteLLMProvider()
