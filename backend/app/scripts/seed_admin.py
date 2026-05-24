"""Seed admin user từ env `SEED_ADMIN_*`. Idempotent.

Usage (trong container):
    python -m app.scripts.seed_admin

Hoặc qua make/tasks:
    make seed
    pwsh ./tasks.ps1 seed
"""

from __future__ import annotations

import asyncio
import sys

from app.core.config import settings
from app.core.db import AsyncSessionLocal
from app.core.logging import get_logger
from app.core.security import hash_password, validate_password_strength
from app.services.user_service import ensure_admin_exists

logger = get_logger(__name__)


async def main() -> None:
    """Tạo (hoặc upgrade) admin từ env."""
    try:
        validate_password_strength(settings.seed_admin_password)
    except Exception as e:
        logger.error("seed.invalid_password", error=str(e))
        sys.stderr.write(f"[seed_admin] Invalid SEED_ADMIN_PASSWORD: {e}\n")
        sys.exit(2)

    async with AsyncSessionLocal() as db:
        user = await ensure_admin_exists(
            db,
            email=settings.seed_admin_email,
            password_hash=hash_password(settings.seed_admin_password),
            full_name=settings.seed_admin_full_name,
        )
        sys.stdout.write(f"[seed_admin] OK — admin id={user.id} email={user.email}\n")


if __name__ == "__main__":
    asyncio.run(main())
