from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from uuid import UUID
import uuid

from jose import jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: UUID, *, session_id: UUID | None = None, jti: str | None = None) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expire, "type": "access", "jti": jti or str(uuid.uuid4())}
    if session_id is not None:
        payload["sid"] = str(session_id)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(
    user_id: UUID,
    *,
    session_id: UUID,
    token_family: str,
    refresh_jti: str,
) -> str:
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return jwt.encode(
        {
            "sub": str(user_id),
            "exp": expire,
            "type": "refresh",
            "sid": str(session_id),
            "family": token_family,
            "jti": refresh_jti,
        },
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def decode_token(token: str, token_type: str | None = None) -> dict | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if token_type and payload.get("type") != token_type:
            return None
        return payload
    except Exception:
        return None


def verify_token(token: str, token_type: str = "access") -> UUID | None:
    payload = decode_token(token, token_type)
    if not payload:
        return None
    try:
        return UUID(payload["sub"])
    except Exception:
        return None


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)
