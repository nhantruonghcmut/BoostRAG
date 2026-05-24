"""Admin user-management endpoints — list/get/approve/unlock/disable."""

from __future__ import annotations

from httpx import AsyncClient

from app.models.user import User


async def _admin_token(client: AsyncClient, admin_user: User) -> str:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": admin_user.email, "password": "AdminPass123"},
    )
    assert resp.status_code == 200, resp.text
    return str(resp.json()["access_token"])


class TestAdminUserList:
    async def test_admin_can_list(
        self, client: AsyncClient, admin_user: User, active_user: User
    ) -> None:
        token = await _admin_token(client, admin_user)
        resp = await client.get(
            "/api/v1/admin/users",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        emails = {item["email"] for item in body["items"]}
        assert admin_user.email in emails
        assert active_user.email in emails

    async def test_non_admin_cannot_list(self, client: AsyncClient, active_user: User) -> None:
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": active_user.email, "password": "UserPass123"},
        )
        access = login.json()["access_token"]
        resp = await client.get(
            "/api/v1/admin/users",
            headers={"Authorization": f"Bearer {access}"},
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "AUTHORIZATION_DENIED"


class TestApprove:
    async def test_admin_approves_pending(
        self, client: AsyncClient, admin_user: User, pending_user: User
    ) -> None:
        token = await _admin_token(client, admin_user)
        resp = await client.post(
            f"/api/v1/admin/users/{pending_user.id}/approve",
            headers={"Authorization": f"Bearer {token}"},
            json={"access_level": 3, "groups": ["HR", "Internal"]},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "active"
        assert body["access_level"] == 3
        assert {g["name"] for g in body["groups"]} == {"HR", "Internal"}

    async def test_cannot_approve_active_user(
        self, client: AsyncClient, admin_user: User, active_user: User
    ) -> None:
        token = await _admin_token(client, admin_user)
        resp = await client.post(
            f"/api/v1/admin/users/{active_user.id}/approve",
            headers={"Authorization": f"Bearer {token}"},
            json={"access_level": 2, "groups": []},
        )
        assert resp.status_code == 409


class TestUpdate:
    async def test_patch_user_level_and_groups(
        self, client: AsyncClient, admin_user: User, active_user: User
    ) -> None:
        token = await _admin_token(client, admin_user)
        resp = await client.patch(
            f"/api/v1/admin/users/{active_user.id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"access_level": 4, "groups": ["Finance"]},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["access_level"] == 4
        assert [g["name"] for g in body["groups"]] == ["Finance"]


class TestDisable:
    async def test_admin_disables_user(
        self, client: AsyncClient, admin_user: User, active_user: User
    ) -> None:
        token = await _admin_token(client, admin_user)
        resp = await client.delete(
            f"/api/v1/admin/users/{active_user.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 204
