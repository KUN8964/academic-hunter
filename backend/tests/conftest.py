"""Shared test fixtures for Academic Hunter."""

import os

import pytest

# Ensure tests can import from src/
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-unit-tests-only-minimum-32-chars!!")
