"""
Database encryption helpers.

On desktop/laptop: derives an encryption key from the ASD_DB_KEY env var.
On Android: should be replaced with an Android Keystore-backed derivation.

The key is passed to SQLCipher via the PRAGMA key mechanism.
"""

from __future__ import annotations

import hashlib
import os

from asd_backend.config import settings


def get_db_key() -> str:
    """
    Return the SQLCipher encryption key as a hex string.

    In production the raw key should come from a hardware-backed keystore.
    For development it is derived from ASD_DB_KEY via PBKDF2-SHA256 so that
    even a weak passphrase produces a proper 256-bit key.
    """
    raw = settings.db_key.encode("utf-8")
    # A fixed but non-secret salt is acceptable here because the key
    # confidentiality comes from the ASD_DB_KEY env secret, not the salt.
    salt = b"asd-edge-st-2.0-db-salt"
    derived = hashlib.pbkdf2_hmac("sha256", raw, salt, iterations=100_000)
    return derived.hex()


def get_db_url() -> str:
    """
    Return the async SQLAlchemy database URL.

    Uses aiosqlite driver (plain SQLite) for cross-platform dev convenience.
    On Android, swap to the SQLCipher-backed driver and apply the PRAGMA key.
    """
    path = settings.db_path.resolve()
    return f"sqlite+aiosqlite:///{path}"
