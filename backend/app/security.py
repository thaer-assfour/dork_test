"""Single-user password auth with a signed session cookie."""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from itsdangerous import BadSignature, URLSafeSerializer
from passlib.context import CryptContext

from app.config import get_settings

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
COOKIE_NAME = "dorkhub_session"


def hash_password(password: str) -> str:
    return _pwd.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    if not hashed:
        return False
    try:
        return _pwd.verify(password, hashed)
    except ValueError:
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
