from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from jose import jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def dummy_verify() -> None:
    pwd_context.dummy_verify()


def create_access_token(user_id: UUID, *, session_id: UUID | None = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": str(user_id), "exp": expire, "type": "access"}
    if session_id:
        payload["sid"] = str(session_id)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(
    user_id: UUID,
    *,
    session_id: UUID | None = None,
    token_family: str | None = None,
    refresh_jti: str | None = None,
) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    payload = {"sub": str(user_id), "exp": expire, "type": "refresh"}
    if session_id:
        payload["sid"] = str(session_id)
    if token_family:
        payload["fam"] = token_family
    if refresh_jti:
        payload["jti"] = refresh_jti
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token_payload(token: str, token_type: str) -> dict | None:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        if payload.get("type") != token_type:
            return None
        return payload
    except Exception:
        return None


def verify_token(token: str, token_type: str = "access") -> UUID | None:
    payload = decode_token_payload(token, token_type)
    if not payload:
        return None
    try:
        return UUID(payload["sub"])
    except Exception:
        return None


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)
