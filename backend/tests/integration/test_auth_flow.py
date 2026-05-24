"""End-to-end auth flow: register → approve → login → me → refresh → logout."""

from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class TestRegisterFlow:
    async def test_register_creates_pending_user(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "new@example.com",
                "password": "Newpass1234",
                "full_name": "New User",
            },
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["status"] == "pending_approval"
        assert body["message"]

    async def test_register_rejects_duplicate(self, client: AsyncClient, active_user: User) -> None:
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": active_user.email,
                "password": "Otherpass123",
                "full_name": "Dup",
            },
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "RESOURCE_CONFLICT"

    async def test_register_rejects_weak_password(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "x@example.com", "password": "short", "full_name": "X"},
        )
        # Either 422 (pydantic) or 400 (policy) — both indicate rejection
        assert resp.status_code in (400, 422)


class TestLoginFlow:
    async def test_pending_user_cannot_login(self, client: AsyncClient, pending_user: User) -> None:
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": pending_user.email, "password": "PendingPass123"},
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "AUTH_PENDING_APPROVAL"

    async def test_active_user_logs_in(self, client: AsyncClient, active_user: User) -> None:
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": active_user.email, "password": "UserPass123"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["token_type"] == "bearer"
        assert body["expires_in"] > 0
        assert body["access_token"]
        assert body["user"]["email"] == active_user.email
        # Refresh token set via cookie
        assert "refresh_token" in resp.cookies

    async def test_login_wrong_password(self, client: AsyncClient, active_user: User) -> None:
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": active_user.email, "password": "WrongPass123"},
        )
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "AUTH_INVALID_CREDENTIALS"


class TestMeEndpoint:
    async def test_me_requires_token(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/auth/me")
        # FastAPI HTTPBearer trả 403 (older) hoặc 401 (newer) khi thiếu credentials
        assert resp.status_code in {401, 403}

    async def test_me_returns_user_info(self, client: AsyncClient, active_user: User) -> None:
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": active_user.email, "password": "UserPass123"},
        )
        access = login.json()["access_token"]
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access}"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["email"] == active_user.email
        assert body["role"] == "user"
        assert body["access_level"] == active_user.access_level


class TestRefreshFlow:
    async def test_refresh_rotates_token(self, client: AsyncClient, active_user: User) -> None:
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": active_user.email, "password": "UserPass123"},
        )
        assert login.status_code == 200
        cookies = login.cookies
        old_refresh = cookies.get("refresh_token")

        resp = await client.post("/api/v1/auth/refresh", cookies=cookies)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["access_token"]
        new_refresh = resp.cookies.get("refresh_token")
        assert new_refresh and new_refresh != old_refresh

    async def test_refresh_replay_rejected(
        self, client: AsyncClient, active_user: User, db: AsyncSession
    ) -> None:
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": active_user.email, "password": "UserPass123"},
        )
        cookies = login.cookies
        # Use refresh once → revokes old
        first = await client.post("/api/v1/auth/refresh", cookies=cookies)
        assert first.status_code == 200
        # Replay with old cookie
        replay = await client.post("/api/v1/auth/refresh", cookies=cookies)
        assert replay.status_code == 401
        assert replay.json()["error"]["code"] == "AUTH_TOKEN_INVALID"


class TestLogoutFlow:
    async def test_logout_revokes_refresh(self, client: AsyncClient, active_user: User) -> None:
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": active_user.email, "password": "UserPass123"},
        )
        cookies = login.cookies
        resp = await client.post("/api/v1/auth/logout", cookies=cookies)
        assert resp.status_code == 200
        # Subsequent refresh with same cookie → invalid
        retry = await client.post("/api/v1/auth/refresh", cookies=cookies)
        assert retry.status_code == 401
