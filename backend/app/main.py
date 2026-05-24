"""FastAPI app factory + global handlers + middleware."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response

from app.api.v1 import api_router
from app.core.config import settings
from app.core.exceptions import AppError
from app.core.logging import configure_logging, get_logger
from app.schemas.common import ErrorPayload, ErrorResponse

logger = get_logger(__name__)

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.rate_limit_default_per_min}/minute"],
    enabled=not settings.is_test(),
)


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[no-untyped-def]
    """Startup/shutdown hooks."""
    configure_logging()
    logger.info("app.startup", env=settings.app_env, name=settings.app_name)
    yield
    logger.info("app.shutdown")


def create_app() -> FastAPI:
    """Factory pattern — dùng cho production + test (override deps trong test)."""
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="BoostRAG — enterprise RAG backend.",
        docs_url="/docs" if not settings.is_prod() else None,
        redoc_url="/redoc" if not settings.is_prod() else None,
        openapi_url="/api/v1/openapi.json",
        lifespan=lifespan,
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
    app.add_middleware(SlowAPIMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    _register_exception_handlers(app)
    _register_middlewares(app)
    _register_routes(app)
    return app


def _register_exception_handlers(app: FastAPI) -> None:
    """Convert `AppError` subclasses sang JSON response chuẩn."""

    @app.exception_handler(AppError)
    async def _app_error_handler(_: StarletteRequest, exc: AppError) -> JSONResponse:
        logger.warning(
            "app.error",
            code=exc.code,
            status=exc.http_status,
            message=exc.message,
            details=exc.details,
        )
        return JSONResponse(
            status_code=exc.http_status,
            content=ErrorResponse(
                error=ErrorPayload(
                    code=exc.code,
                    message=exc.message,
                    details=exc.details,
                )
            ).model_dump(),
        )

    @app.exception_handler(Exception)
    async def _generic_handler(_: StarletteRequest, exc: Exception) -> JSONResponse:
        logger.exception("app.unhandled", error=str(exc))
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error=ErrorPayload(
                    code="INTERNAL_ERROR",
                    message="Internal server error",
                )
            ).model_dump(),
        )


def _register_middlewares(app: FastAPI) -> None:
    @app.middleware("http")
    async def _log_requests(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        latency_ms = int((time.perf_counter() - start) * 1000)
        logger.info(
            "http.request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            latency_ms=latency_ms,
        )
        return response


def _register_routes(app: FastAPI) -> None:
    app.include_router(api_router, prefix="/api/v1")

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, Any]:
        """Lightweight liveness check — không touch DB."""
        return {"status": "ok", "service": settings.app_name, "version": app.version}


app = create_app()
