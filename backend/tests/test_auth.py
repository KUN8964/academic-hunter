"""Tests for authentication logic: password hashing, JWT, user CRUD."""

import os
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import bcrypt
import pytest
from sqlalchemy import select

# Ensure config uses test values so validators don't block
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-unit-tests-only-minimum-32-chars!!")


class TestPasswordHashing:
    """Password hashing and verification using bcrypt."""

    def test_hash_returns_different_from_input(self):
        from src.services.auth import hash_password

        hashed = hash_password("mysecret")
        assert hashed != "mysecret"
        assert hashed.startswith("$2b$") or hashed.startswith("$2a$")

    def test_verify_correct_password(self):
        from src.services.auth import hash_password, verify_password

        hashed = hash_password("correct-horse-battery-staple")
        assert verify_password("correct-horse-battery-staple", hashed) is True

    def test_verify_wrong_password(self):
        from src.services.auth import hash_password, verify_password

        hashed = hash_password("correct-password")
        assert verify_password("wrong-password", hashed) is False

    def test_same_password_produces_different_hashes(self):
        from src.services.auth import hash_password

        h1 = hash_password("same-password")
        h2 = hash_password("same-password")
        assert h1 != h2  # Different salts


class TestJWT:
    """JWT token creation and decoding."""

    def test_create_and_decode_token(self):
        from src.services.auth import create_access_token, decode_access_token

        token = create_access_token("user-123")
        user_id = decode_access_token(token)
        assert user_id == "user-123"

    def test_decode_invalid_token_returns_none(self):
        from src.services.auth import decode_access_token

        assert decode_access_token("not-a-valid-token") is None
        assert decode_access_token("") is None

    def test_decode_expired_token_returns_none(self):
        from src.services.auth import create_access_token, decode_access_token

        with patch("src.services.auth.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2020, 1, 1, tzinfo=timezone.utc)
            token = create_access_token("user-456")

        # Token is now 6+ years expired — should return None
        assert decode_access_token(token) is None


class TestPasswordValidation:
    """Pydantic schema validation for password minimum length."""

    def test_password_too_short(self):
        from pydantic import ValidationError
        from src.schemas import UserRegister

        with pytest.raises(ValidationError) as exc:
            UserRegister(email="test@test.com", password="short")
        assert "at least 8 characters" in str(exc.value)

    def test_password_minimum_length(self):
        from src.schemas import UserRegister

        user = UserRegister(email="test@test.com", password="12345678")
        assert user.password == "12345678"
