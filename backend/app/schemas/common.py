"""Shared schema primitives (pagination, error envelope, ...)."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic list wrapper — `items[]` + total + pagination."""

    items: list[T]
    total: int = Field(ge=0)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)


class ErrorPayload(BaseModel):
    """Body của `AppError` đã serialize cho client."""

    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    """Wrapper response error chuẩn `{"error": {...}}` — xem `docs/API.md`."""

    error: ErrorPayload
