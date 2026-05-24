"""Unit tests cho password policy + hash/verify."""

from __future__ import annotations

import pytest

from app.core.exceptions import ValidationError
from app.core.security import (
    hash_password,
    validate_password_strength,
    verify_password,
)


class TestValidatePasswordStrength:
    def test_accepts_valid_password(self) -> None:
        validate_password_strength("Strongpass1")  # no raise

    def test_rejects_too_short(self) -> None:
        with pytest.raises(ValidationError, match="at least 10"):
            validate_password_strength("Short1")

    def test_rejects_no_letter(self) -> None:
        with pytest.raises(ValidationError, match="letter"):
            validate_password_strength("1234567890")

    def test_rejects_no_digit(self) -> None:
        with pytest.raises(ValidationError, match="digit"):
            validate_password_strength("ABCdefghij")

    def test_unicode_only_letters_rejected(self) -> None:
        # Policy chỉ count ASCII letter — password chỉ có chữ unicode + digit → fail
        with pytest.raises(ValidationError, match="letter"):
            validate_password_strength("ñöäüñöäü12!")


class TestHashVerify:
    def test_hash_is_not_plaintext(self) -> None:
        plain = "SecretValue123"
        hashed = hash_password(plain)
        assert hashed != plain
        assert hashed.startswith("$2")

    def test_verify_matches(self) -> None:
        plain = "AnotherSecret9"
        hashed = hash_password(plain)
        assert verify_password(plain, hashed) is True

    def test_verify_rejects_wrong(self) -> None:
        hashed = hash_password("RightPass001")
        assert verify_password("WrongPass001", hashed) is False

    def test_verify_handles_invalid_hash(self) -> None:
        assert verify_password("anything9", "not-a-valid-hash") is False
