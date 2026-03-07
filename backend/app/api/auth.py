from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    generate_csrf_token,
    verify_password,
    verify_token,
)
from app.models.user import User
from app.schemas.auth import UserLogin

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


@router.post("/login")
async def login(
    credentials: UserLogin,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict:
    q = await db.execute(select(User).where(User.email == credentials.email))
    user = q.scalar_one_or_none()

    if not user or not user.is_active or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    csrf_token = generate_csrf_token()

    _set_auth_cookies(response, access_token, refresh_token)
    _set_csrf_cookie(response, csrf_token)

    user.last_login = datetime.utcnow()
    await db.commit()

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

    user_id = verify_token(token, "refresh")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token inválido")

    # Optional: could verify user still exists/active
    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Usuario inválido")

    # Nuevo access + nuevo CSRF
    new_access = create_access_token(user_id)
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
    _set_csrf_cookie(response, new_csrf)

    # Rotación opcional de refresh si expira en <24h
    # (simple: re-emitimos un refresh nuevo cuando está cerca)
    try:
        from jose import jwt

        payload = jwt.get_unverified_claims(token)
        exp = payload.get("exp")
        if exp:
            from datetime import datetime, timedelta

            exp_dt = datetime.utcfromtimestamp(exp)
            if exp_dt - datetime.utcnow() < timedelta(hours=24):
                new_refresh = create_refresh_token(user_id)
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
    except Exception:
        pass

    return {"status": "refreshed"}


@router.post("/logout")
async def logout(response: Response) -> dict:
    response.delete_cookie("access_token", path="/")
    # delete both paths for safety (if older cookie was set at '/')
    response.delete_cookie("refresh_token", path="/auth/refresh")
    response.delete_cookie("refresh_token", path="/")
    response.delete_cookie("csrf_token", path="/")
    return {"status": "logged out"}


@router.get("/me")
async def me(user: User = Depends(get_current_user)) -> dict:
    return {"id": user.id, "email": user.email, "full_name": user.full_name}
