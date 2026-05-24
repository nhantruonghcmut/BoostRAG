"""Unit tests cho JWT encode/decode + token type validation."""

from __future__ import annotations

import time
from uuid import uuid4

import pytest
from jose import jwt

from app.core.config import settings
from app.core.exceptions import TokenExpiredError, TokenInvalidError
from app.core.security import create_access_token, create_refresh_token, decode_token


class TestAccessToken:
    def test_create_returns_valid_payload(self) -> None:
        sub = str(uuid4())
        token, expires_in = create_access_token(sub, "admin")
        payload = decode_token(token, expected_type="access")
        assert payload["sub"] == sub
        assert payload["role"] == "admin"
        assert payload["type"] == "access"
        assert expires_in == settings.jwt_access_ttl_min * 60

    def test_decode_rejects_wrong_type(self) -> None:
        token, _ = create_access_token(str(uuid4()), "user")
        with pytest.raises(TokenInvalidError):
            decode_token(token, expected_type="refresh")

    def test_decode_rejects_invalid_signature(self) -> None:
        token = jwt.encode(
            {"sub": "x", "role": "user", "type": "access", "exp": int(time.time()) + 60},
            "wrong-secret",
            algorithm=settings.jwt_algorithm,
        )
        with pytest.raises(TokenInvalidError):
            decode_token(token)

    def test_decode_rejects_expired(self) -> None:
        token = jwt.encode(
            {
                "sub": "x",
                "role": "user",
                "type": "access",
                "iat": int(time.time()) - 200,
                "exp": int(time.time()) - 100,
            },
            settings.jwt_secret,
            algorithm=settings.jwt_algorithm,
        )
        with pytest.raises(TokenExpiredError):
            decode_token(token)


class TestRefreshToken:
    def test_create_returns_jti(self) -> None:
        sub = str(uuid4())
        token, jti, _exp = create_refresh_token(sub, "user")
        payload = decode_token(token, expected_type="refresh")
        assert payload["jti"] == jti
        assert payload["sub"] == sub

    def test_two_tokens_have_distinct_jti(self) -> None:
        sub = str(uuid4())
        _, jti1, _ = create_refresh_token(sub, "user")
        _, jti2, _ = create_refresh_token(sub, "user")
        assert jti1 != jti2
