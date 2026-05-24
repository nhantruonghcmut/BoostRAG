"""Application settings loaded từ environment variables (Pydantic Settings).

Singleton `settings` được expose ở module level. Mọi nơi cần config nên import:

    from app.core.config import settings

Không hardcode giá trị nào — tất cả qua env (xem `.env.example`).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed env-driven application settings.

    Env vars được parse case-insensitive. Default chỉ dùng cho local dev —
    production phải override toàn bộ secret-related fields.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ───────────────────────────────────────────────────────────────
    app_env: Literal["development", "staging", "production", "test"] = "development"
    app_name: str = "BoostRAG"
    app_secret_key: str = Field(default="changeme-app-secret-key", min_length=8)
    master_key: str = Field(
        default="changeme-base64-fernet-key-44-chars-replace-this==",
        description="Fernet key cho encrypt LLM API key trong DB",
    )

    # ── Database ─────────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://boostrag:boostrag@postgres:5432/boostrag"

    # ── Qdrant ───────────────────────────────────────────────────────────
    qdrant_url: str = "http://qdrant:6333"
    qdrant_api_key: str | None = None

    # ── Redis ────────────────────────────────────────────────────────────
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"

    # ── MinIO ────────────────────────────────────────────────────────────
    minio_endpoint: str = "minio:9000"
    minio_public_endpoint: str = "http://localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "boostrag-documents"
    minio_use_ssl: bool = False

    # ── JWT ──────────────────────────────────────────────────────────────
    jwt_secret: str = Field(default="changeme-jwt-secret-please-rotate", min_length=8)
    jwt_algorithm: str = "HS256"
    jwt_access_ttl_min: int = 15
    jwt_refresh_ttl_days: int = 7

    # ── Lockout / rate limit ─────────────────────────────────────────────
    max_failed_login_attempts: int = 5
    account_lock_minutes: int = 15
    rate_limit_login_per_min: int = 5
    rate_limit_register_per_min: int = 3
    rate_limit_default_per_min: int = 60

    # ── File upload ──────────────────────────────────────────────────────
    max_file_size_mb: int = 50

    # ── CORS ─────────────────────────────────────────────────────────────
    allowed_origins: str = "http://localhost:3000"

    # ── LLM placeholders (Phase 3) ───────────────────────────────────────
    openai_api_key: str | None = None
    google_api_key: str | None = None
    anthropic_api_key: str | None = None
    azure_openai_api_key: str | None = None
    azure_openai_endpoint: str | None = None
    ollama_base_url: str = "http://host.docker.internal:11434"

    # ── RAG defaults ─────────────────────────────────────────────────────
    default_embedding_provider: str = "openai"
    default_embedding_model: str = "text-embedding-3-small"
    qdrant_collection: str | None = None  # auto-derived nếu None
    default_llm_provider: str = "openai"
    default_llm_model: str = "gpt-4o-mini"
    default_reranker_model: str = "BAAI/bge-reranker-v2-m3"
    llm_timeout_s: int = 60
    injection_check: Literal["off", "basic", "strict"] = "basic"
    chunk_size: int = 800
    chunk_overlap: int = 100

    # ── Seed admin ───────────────────────────────────────────────────────
    seed_admin_email: str = "admin@boostrag.local"
    seed_admin_password: str = "Changeme1!"
    seed_admin_full_name: str = "Boost Admin"

    # ── Logging ──────────────────────────────────────────────────────────
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_format: Literal["pretty", "json"] = "pretty"

    # ─────────────────────────────────────────────────────────────────────
    # Computed / helpers
    # ─────────────────────────────────────────────────────────────────────

    @computed_field  # type: ignore[prop-decorator]
    @property
    def allowed_origins_list(self) -> list[str]:
        """Parse CSV `allowed_origins` env thành list."""
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    def is_dev(self) -> bool:
        """True nếu chạy local dev environment."""
        return self.app_env == "development"

    def is_prod(self) -> bool:
        """True nếu chạy production."""
        return self.app_env == "production"

    def is_test(self) -> bool:
        """True nếu chạy test suite."""
        return self.app_env == "test"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def qdrant_collection_name(self) -> str:
        """Qdrant collection name derived from embedding model.

        Format: ``boostrag_<provider>_<model_slug>`` — vd ``boostrag_openai_emb3small``.
        """
        if self.qdrant_collection:
            return self.qdrant_collection
        model_slug = (
            self.default_embedding_model.replace("text-embedding-", "emb")
            .replace("-", "")
            .replace(".", "")
            .lower()
        )
        return f"boostrag_{self.default_embedding_provider}_{model_slug}"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def max_file_size_bytes(self) -> int:
        """Max upload size in bytes."""
        return self.max_file_size_mb * 1024 * 1024


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached singleton accessor — dùng khi cần inject thay vì global."""
    return Settings()


settings: Settings = get_settings()
