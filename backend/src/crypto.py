"""Application-level encryption for sensitive user data (API keys).

Uses Fernet (AES-128-CBC + HMAC) with a key derived from JWT_SECRET.
Legacy plaintext values are detected and passed through during migration.
"""

import base64
import hashlib

from cryptography.fernet import Fernet

from .config import settings


def _get_fernet() -> Fernet:
    """Derive a Fernet key from the server JWT secret."""
    key = base64.urlsafe_b64encode(hashlib.sha256(settings.jwt_secret.encode()).digest())
    return Fernet(key)


def encrypt_api_key(plain: str | None) -> str | None:
    """Encrypt an API key for storage. Returns None/empty string unchanged."""
    if not plain:
        return plain
    return _get_fernet().encrypt(plain.encode()).decode()


def decrypt_api_key(cipher: str | None) -> str | None:
    """Decrypt an API key from storage. Falls back to plaintext for legacy data."""
    if not cipher:
        return cipher
    try:
        return _get_fernet().decrypt(cipher.encode()).decode()
    except Exception:
        # Legacy: value was stored in plaintext before encryption was added
        return cipher
