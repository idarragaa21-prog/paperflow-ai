from __future__ import annotations

from collections.abc import AsyncGenerator
from uuid import UUID

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.core.security import decode_token_payload
from app.database import async_session_maker
from app.models.user import User
from app.services import auth_sessions


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

    payload = decode_token_payload(token, "access")
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido")
    try:
        user_id = UUID(str(payload["sub"]))
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Token inválido") from exc

    session_id = payload.get("sid")
    if session_id:
        try:
            session_uuid = UUID(str(session_id))
        except Exception as exc:
            raise HTTPException(status_code=401, detail="Sesión inválida") from exc
        session = await auth_sessions.get_auth_session(db, session_uuid)
        if session is None or not auth_sessions.is_session_active(session) or session.user_id != user_id:
            raise HTTPException(status_code=401, detail="Sesión inválida")

    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Usuario inválido")

    return user
