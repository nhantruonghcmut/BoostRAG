"""Celery application config.

Phase 2 sẽ register `ingestion_tasks.parse_and_embed_document`. Hiện tại
chỉ có app instance + ping task để test infra (health check).
"""

from __future__ import annotations

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "boostrag",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_max_tasks_per_child=200,
    broker_connection_retry_on_startup=True,
)


@celery_app.task(name="boostrag.ping")  # type: ignore[untyped-decorator]
def ping() -> str:
    """Health check task — gọi bằng `celery_app.send_task('boostrag.ping')`."""
    return "pong"
