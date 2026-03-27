from __future__ import annotations

from datetime import datetime, timedelta, timezone
import secrets
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.auth import AuthSession


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_token_family() -> str:
    return secrets.token_urlsafe(24)


def new_token_jti() -> str:
    return secrets.token_urlsafe(24)


async def create_auth_session(
    db: AsyncSession,
    *,
    user_id: UUID,
    ip_address: str | None,
    user_agent: str | None,
) -> AuthSession:
    now = _utcnow()
    session = AuthSession(
        user_id=user_id,
        refresh_jti=new_token_jti(),
        token_family=new_token_family(),
        issued_at=now,
        expires_at=now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        ip_address=ip_address,
        user_agent=(user_agent or "")[:512] or None,
    )
    db.add(session)
    await db.flush()
    return session


async def get_auth_session(db: AsyncSession, session_id: UUID) -> AuthSession | None:
    return await db.get(AuthSession, session_id)


def is_session_active(session: AuthSession | None) -> bool:
    return bool(
        session
        and session.revoked_at is None
        and (session.expires_at is None or session.expires_at > _utcnow())
    )


async def revoke_session(db: AsyncSession, session: AuthSession) -> None:
    if session.revoked_at is None:
        session.revoked_at = _utcnow()
    await db.flush()


async def revoke_session_family(db: AsyncSession, *, user_id: UUID, token_family: str) -> int:
    now = _utcnow()
    result = await db.execute(
        update(AuthSession)
        .where(AuthSession.user_id == user_id)
        .where(AuthSession.token_family == token_family)
        .where(AuthSession.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    return int(result.rowcount or 0)


async def revoke_all_sessions(db: AsyncSession, *, user_id: UUID) -> int:
    now = _utcnow()
    result = await db.execute(
        update(AuthSession)
        .where(AuthSession.user_id == user_id)
        .where(AuthSession.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    return int(result.rowcount or 0)


async def rotate_refresh_session(
    db: AsyncSession,
    *,
    session: AuthSession,
    previous_jti: str,
) -> str:
    next_jti = new_token_jti()
    session.issued_at = _utcnow()
    session.expires_at = _utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    session.replaced_by_jti = next_jti
    session.refresh_jti = next_jti
    if previous_jti == next_jti:
        session.refresh_jti = new_token_jti()
        session.replaced_by_jti = session.refresh_jti
    await db.flush()
    return session.refresh_jti


async def list_project_session_ids(db: AsyncSession, *, user_id: UUID) -> list[UUID]:
    result = await db.execute(select(AuthSession.id).where(AuthSession.user_id == user_id))
    return [item for item in result.scalars().all()]
