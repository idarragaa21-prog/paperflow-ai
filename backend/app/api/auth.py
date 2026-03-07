from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.config import settings
from app.core.metrics import auth_login_attempts_total, auth_rate_limited_total, token_refresh_reuse_total
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_csrf_token,
    verify_password,
)
from app.models.auth import AuthSession
from app.models.user import User
from app.schemas.auth import UserLogin
from app.services.audit import log_audit
from app.services.auth_rate_limit import AuthRateLimitExceeded, hit as auth_rate_limit_hit
from app.services.auth_sessions import (
    create_auth_session,
    get_auth_session,
    revoke_all_sessions,
    revoke_session,
    revoke_session_family,
    rotate_refresh_session,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        domain=settings.cookie_domain,
        path="/",
    )
    # Más restrictivo: refresh solo se envía a /auth/refresh
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        domain=settings.cookie_domain,
        path="/auth/refresh",
    )


def _set_csrf_cookie(response: Response, csrf_token: str) -> None:
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=False,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=86400,
        domain=settings.cookie_domain,
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/auth/refresh")
    response.delete_cookie("refresh_token", path="/")
    response.delete_cookie("csrf_token", path="/")


def _request_identity(request: Request) -> tuple[str | None, str | None]:
    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return ip, user_agent


def _raise_rate_limited(endpoint: str, exc: AuthRateLimitExceeded) -> None:
    auth_rate_limited_total.labels(endpoint=endpoint).inc()
    raise HTTPException(
        status_code=429,
        detail="Too many requests",
        headers={"Retry-After": str(exc.retry_after_seconds)},
    )


@router.post("/login")
async def login(
    request: Request,
    credentials: UserLogin,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict:
    ip, user_agent = _request_identity(request)
    rate_key = f"{(ip or 'unknown').strip()}:{credentials.email.lower().strip()}"
    try:
        auth_rate_limit_hit("login", rate_key, limit=5, window_seconds=60)
    except AuthRateLimitExceeded as exc:
        _raise_rate_limited("login", exc)

    q = await db.execute(select(User).where(User.email == credentials.email))
    user = q.scalar_one_or_none()

    if not user or not user.is_active or not verify_password(credentials.password, user.password_hash):
        auth_login_attempts_total.labels(result="invalid").inc()
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    session = await create_auth_session(
        db,
        user_id=user.id,
        ip_address=ip,
        user_agent=user_agent,
    )
    access_token = create_access_token(user.id, session_id=session.id)
    refresh_token = create_refresh_token(
        user.id,
        session_id=session.id,
        token_family=session.token_family,
        refresh_jti=session.refresh_jti,
    )
    csrf_token = generate_csrf_token()

    _set_auth_cookies(response, access_token, refresh_token)
    _set_csrf_cookie(response, csrf_token)

    user.last_login = datetime.utcnow()
    await db.commit()
    auth_login_attempts_total.labels(result="success").inc()
    await log_audit(
        db,
        user=user,
        action="login",
        entity_type="auth_session",
        entity_id=session.id,
        details={"ip_address": ip, "user_agent": user_agent},
        request=request,
    )

    return {"email": user.email, "full_name": user.full_name}


@router.post("/refresh")
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict:
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")

    payload = decode_token(token, "refresh")
    sid = str((payload or {}).get("sid") or "anonymous")
    try:
        auth_rate_limit_hit("refresh", sid, limit=20, window_seconds=60)
    except AuthRateLimitExceeded as exc:
        _raise_rate_limited("refresh", exc)

    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido")

    try:
        user_id = UUID(payload["sub"])
        session_id = UUID(payload["sid"])
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=401, detail="Token inválido") from exc

    session = await get_auth_session(db, session_id)
    if not session or session.user_id != user_id or session.revoked_at is not None:
        raise HTTPException(status_code=401, detail="Sesión inválida")

    if session.refresh_jti != payload.get("jti"):
        token_refresh_reuse_total.inc()
        await revoke_session_family(db, user_id=user_id, token_family=session.token_family)
        await db.commit()
        raise HTTPException(status_code=401, detail="Refresh token reuse detected")

    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Usuario inválido")

    next_refresh_jti = await rotate_refresh_session(db, session=session, previous_jti=str(payload.get("jti") or ""))
    new_access = create_access_token(user_id, session_id=session.id)
    new_refresh = create_refresh_token(
        user_id,
        session_id=session.id,
        token_family=session.token_family,
        refresh_jti=next_refresh_jti,
    )
    new_csrf = generate_csrf_token()

    response.set_cookie(
        key="access_token",
        value=new_access,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        domain=settings.cookie_domain,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=new_refresh,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        domain=settings.cookie_domain,
        path="/auth/refresh",
    )
    _set_csrf_cookie(response, new_csrf)
    await db.commit()

    return {"status": "refreshed"}


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict:
    session_id = getattr(request.state, "session_id", None)
    user_id = getattr(request.state, "user_id", None) or "anonymous"
    try:
        auth_rate_limit_hit("logout", str(user_id), limit=20, window_seconds=60)
    except AuthRateLimitExceeded as exc:
        _raise_rate_limited("logout", exc)

    if session_id:
        session = await db.get(AuthSession, UUID(str(session_id)))
        if session:
            await revoke_session(db, session)
            user = await db.get(User, session.user_id)
            if user:
                await log_audit(
                    db,
                    user=user,
                    action="logout",
                    entity_type="auth_session",
                    entity_id=session.id,
                    details={"scope": "current"},
                    request=request,
                )
            await db.commit()

    _clear_auth_cookies(response)
    return {"status": "logged out"}


@router.post("/logout-all")
async def logout_all(
    request: Request,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    revoked = await revoke_all_sessions(db, user_id=user.id)
    await db.commit()
    _clear_auth_cookies(response)
    await log_audit(
        db,
        user=user,
        action="logout_all",
        entity_type="user",
        entity_id=user.id,
        details={"revoked_sessions": revoked},
        request=request,
    )
    return {"status": "logged out", "revoked_sessions": revoked}


@router.get("/me")
async def me(
    request: Request,
    user: User = Depends(get_current_user),
) -> dict:
    try:
        auth_rate_limit_hit("me", str(user.id), limit=60, window_seconds=60)
    except AuthRateLimitExceeded as exc:
        _raise_rate_limited("me", exc)
    return {"id": user.id, "email": user.email, "full_name": user.full_name}
