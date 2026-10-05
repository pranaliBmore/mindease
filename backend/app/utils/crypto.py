"""Application-level encryption for private free-text stored in MongoDB.

Sensitive fields (emotion "reason" notes, chat messages, solo journal text, direct
messages) are encrypted with Fernet (AES-128-CBC + HMAC) before they are written, so
a database dump or a compromised Atlas snapshot does not expose them.

Design goals:
- **Optional.** With no ``DATA_ENCRYPTION_KEY`` set, everything is a no-op and text is
  stored as-is. Local dev keeps working with zero config.
- **Mixed-database safe.** Ciphertext is tagged with an ``enc:v1:`` prefix. ``decrypt_text``
  passes through anything without that prefix, so old plaintext rows and rows written
  while the key was unset still read fine.
- **Fail-soft on read.** If a value cannot be decrypted (wrong/rotated key), the raw
  stored value is returned rather than raising, so history endpoints never 500.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from app.config.settings import get_settings

logger = logging.getLogger(__name__)

_PREFIX = "enc:v1:"


@lru_cache
def _fernet() -> Optional[Fernet]:
    key = (get_settings().data_encryption_key or "").strip()
    if not key:
        return None
    try:
        return Fernet(key.encode())
    except (ValueError, TypeError) as exc:  # malformed key
        logger.error("DATA_ENCRYPTION_KEY is set but invalid; storing text unencrypted: %s", exc)
        return None


def encryption_enabled() -> bool:
    return _fernet() is not None


def encrypt_text(value: str) -> str:
    f = _fernet()
    if f is None or not value:
        return value
    if value.startswith(_PREFIX):  # already encrypted
        return value
    return _PREFIX + f.encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_text(value: str) -> str:
    if not value or not value.startswith(_PREFIX):
        return value
    f = _fernet()
    if f is None:
        return value  # key removed since write; return raw rather than crash
    try:
        return f.decrypt(value[len(_PREFIX):].encode("ascii")).decode("utf-8")
    except InvalidToken:
        logger.warning("Could not decrypt a stored value (key mismatch?); returning it raw.")
        return value


def encrypt_optional(value: Optional[str]) -> Optional[str]:
    return None if value is None else encrypt_text(value)


def decrypt_optional(value: Optional[str]) -> Optional[str]:
    return None if value is None else decrypt_text(value)
