"""Single-user password auth with a signed session cookie."""
from __future__ import annotations

import bcrypt
from fastapi import Depends, HTTPException, Request, status
from itsdangerous import BadSignature, URLSafeSerializer

from app.config import get_settings

COOKIE_NAME = "dorkhub_session"


def _pw_bytes(password: str) -> bytes:
    # bcrypt only considers the first 72 bytes; truncate to avoid a ValueError
    # on newer bcrypt builds for longer inputs.
    return password.encode("utf-8")[:72]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_pw_bytes(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    if not hashed:
        return False
    try:
        return bcrypt.checkpw(_pw_bytes(password), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def _serializer() -> URLSafeSerializer:
    return URLSafeSerializer(get_settings().secret_key, salt="dorkhub-session")


def make_session_token() -> str:
    return _serializer().dumps({"auth": True})


def _valid_token(token: str) -> bool:
    try:
        data = _serializer().loads(token)
        return bool(data.get("auth"))
    except BadSignature:
        return False


def require_auth(request: Request) -> None:
    # If no password is configured, auth is open (first-run convenience).
    if not get_settings().auth_password_hash:
        return
    token = request.cookies.get(COOKIE_NAME, "")
    if not token or not _valid_token(token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not authenticated")


AuthDep = Depends(require_auth)
