"""Symmetric encryption for secrets stored in the DB (e.g. AI provider keys).

The Fernet key is derived from DORKHUB_SECRET_KEY, so the database never holds a
usable key on its own — you also need the .env secret to decrypt.
"""
from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings

_ENC_PREFIX = "enc:"


def _fernet() -> Fernet:
    digest = hashlib.sha256(get_settings().secret_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt(value: str) -> str:
    if not value:
        return ""
    token = _fernet().encrypt(value.encode("utf-8")).decode("utf-8")
    return _ENC_PREFIX + token


def decrypt(value: str) -> str:
    if not value:
        return ""
    if not value.startswith(_ENC_PREFIX):
        return value  # tolerate legacy/plaintext
    try:
        return _fernet().decrypt(value[len(_ENC_PREFIX):].encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return ""
