"""Account lockout sau N lần fail login liên tiếp."""

from __future__ import annotations

from httpx import AsyncClient

from app.core.config import settings
from app.models.user import User


class TestLockout:
    async def test_lockout_after_threshold(self, client: AsyncClient, active_user: User) -> None:
        attempts = settings.max_failed_login_attempts
        # Trigger N fail logins
        for _ in range(attempts):
            resp = await client.post(
                "/api/v1/auth/login",
                json={"email": active_user.email, "password": "WrongPass!"},
            )
            assert resp.status_code == 401

        # Next attempt — even with correct password — should be locked
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": active_user.email, "password": "UserPass123"},
        )
        assert resp.status_code == 401
        code = resp.json()["error"]["code"]
        assert code in {"AUTH_ACCOUNT_LOCKED", "AUTH_INVALID_CREDENTIALS"}
        # After locked, the next correct-password attempt should reveal LOCKED specifically
        resp2 = await client.post(
            "/api/v1/auth/login",
            json={"email": active_user.email, "password": "UserPass123"},
        )
        assert resp2.status_code == 401
        assert resp2.json()["error"]["code"] == "AUTH_ACCOUNT_LOCKED"
