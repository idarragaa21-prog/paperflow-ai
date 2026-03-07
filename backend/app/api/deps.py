from __future__ import annotations

from collections.abc import AsyncGenerator
from uuid import UUID

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.config import settings
from app.core.security import decode_token
from app.database import async_session_maker
from app.models.auth import AuthSession
from app.models.user import User


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="No autenticado")

    payload = decode_token(token, "access")
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token inválido")

    session_id = payload.get("sid")
    if session_id:
        session = await db.get(AuthSession, UUID(session_id))
        if not session or session.revoked_at is not None:
            raise HTTPException(status_code=401, detail="Sesión revocada")
    elif settings.ENV == "production":
        raise HTTPException(status_code=401, detail="Token legacy no permitido")

    user = await db.get(User, UUID(user_id))
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Usuario inválido")

    return user
