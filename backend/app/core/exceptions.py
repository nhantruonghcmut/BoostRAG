"""Domain exception hierarchy.

`AppError` là root. Mọi service raise subclass có sẵn (vd `ACLError`,
`NotFoundError`). Global FastAPI handler convert → JSON response chuẩn
(xem `app.main`).

KHÔNG dùng `raise HTTPException` trong service — đó là concern của API layer.
"""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base error type cho toàn application.

    Attributes:
        code: machine-readable error code (vd `ACL_DENIED`).
        http_status: HTTP status code mapping.
        message: human-readable message (có thể trả ra client).
        details: arbitrary extra context (KHÔNG đặt secret vào đây).
    """

    code: str = "INTERNAL_ERROR"
    http_status: int = 500

    def __init__(self, message: str = "", details: dict[str, Any] | None = None) -> None:
        self.message = message or self.__class__.__name__
        self.details: dict[str, Any] = details or {}
        super().__init__(self.message)


# ── Auth ────────────────────────────────────────────────────────────────────


class AuthError(AppError):
    """Base cho mọi lỗi authentication."""

    code = "AUTH_ERROR"
    http_status = 401


class InvalidCredentialsError(AuthError):
    code = "AUTH_INVALID_CREDENTIALS"


class TokenExpiredError(AuthError):
    code = "AUTH_TOKEN_EXPIRED"


class TokenInvalidError(AuthError):
    code = "AUTH_TOKEN_INVALID"


class AccountLockedError(AuthError):
    code = "AUTH_ACCOUNT_LOCKED"


class PendingApprovalError(AuthError):
    code = "AUTH_PENDING_APPROVAL"
    http_status = 403


class AccountDisabledError(AuthError):
    code = "AUTH_ACCOUNT_DISABLED"
    http_status = 403


# ── Authorization ───────────────────────────────────────────────────────────


class AuthorizationError(AppError):
    """User authenticated nhưng không có quyền."""

    code = "AUTHORIZATION_DENIED"
    http_status = 403


class ACLError(AuthorizationError):
    code = "ACL_DENIED"


# ── Validation / resource ──────────────────────────────────────────────────


class ValidationError(AppError):
    code = "VALIDATION_ERROR"
    http_status = 400


class NotFoundError(AppError):
    code = "RESOURCE_NOT_FOUND"
    http_status = 404


class ConflictError(AppError):
    code = "RESOURCE_CONFLICT"
    http_status = 409


class RateLimitError(AppError):
    code = "RATE_LIMITED"
    http_status = 429


# ── RAG / LLM / Tool (placeholder cho Phase 2-4) ───────────────────────────


class RAGError(AppError):
    code = "RAG_ERROR"
    http_status = 500


class LLMError(AppError):
    code = "LLM_ERROR"
    http_status = 503


class LLMTimeoutError(AppError):
    code = "LLM_TIMEOUT"
    http_status = 503


class IngestionError(AppError):
    code = "INGESTION_FAILED"
    http_status = 500


class PromptInjectionError(AppError):
    code = "PROMPT_INJECTION_DETECTED"
    http_status = 400


class ToolError(AppError):
    code = "TOOL_EXECUTION_FAILED"
    http_status = 503


class ToolValidationError(AppError):
    code = "TOOL_VALIDATION_ERROR"
    http_status = 400
