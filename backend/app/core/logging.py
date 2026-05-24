"""Structlog-based logging.

`get_logger(__name__)` trả về logger structured. Format JSON ở prod, pretty
ở dev (xem `LOG_FORMAT` env). Không bao giờ dùng `print()` trong production code.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor

from app.core.config import settings


def _configure_stdlib() -> None:
    """Cấu hình stdlib `logging` để structlog có thể format ra."""
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=settings.log_level,
        force=True,
    )


def _add_service_info(_: Any, __: str, event_dict: EventDict) -> EventDict:
    """Inject metadata cố định vào mọi log record."""
    event_dict["service"] = settings.app_name
    event_dict["env"] = settings.app_env
    return event_dict


def configure_logging() -> None:
    """Cấu hình structlog (idempotent)."""
    _configure_stdlib()

    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        _add_service_info,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    renderer: Processor = (
        structlog.processors.JSONRenderer()
        if settings.log_format == "json"
        else structlog.dev.ConsoleRenderer(colors=True)
    )

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.log_level)
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Trả về structlog logger.

    Args:
        name: thường truyền `__name__` từ module gọi.

    Returns:
        Bound logger có thể `.info()/.warning()/.exception()` với `extra={...}`
        hoặc structured key-value `logger.info("event", user_id=...)`.
    """
    logger: structlog.stdlib.BoundLogger = structlog.get_logger(name)
    return logger


# Auto-configure on import
configure_logging()
