from __future__ import annotations

from datetime import datetime, timezone
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
    hash_password,
    verify_password,
    verify_token,
)
from app.models.user import User
from app.schemas.auth import ForgotPasswordRequest, ResetPasswordRequest, UserLogin, UserRegister

router = APIRouter(prefix="/auth", tags=["auth"])

# In-memory password reset codes (development). In production use Redis or DB table.
_reset_codes: dict[str, str] = {}


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
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
        samesite=settings.cookie_samesite,
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
        samesite=settings.cookie_samesite,
        max_age=86400,
        domain=settings.cookie_domain,
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    cookie_domains = [None]
    if settings.cookie_domain:
        cookie_domains.append(settings.cookie_domain)

    for domain in cookie_domains:
        response.delete_cookie("access_token", path="/", domain=domain)
        response.delete_cookie("refresh_token", path="/auth/refresh", domain=domain)
        response.delete_cookie("refresh_token", path="/", domain=domain)
        response.delete_cookie("csrf_token", path="/", domain=domain)


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

    user.last_login = datetime.now(timezone.utc)
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
        samesite=settings.cookie_samesite,
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
            from datetime import datetime, timedelta, timezone

            exp_dt = datetime.utcfromtimestamp(exp)
            if exp_dt - datetime.now(timezone.utc) < timedelta(hours=24):
                new_refresh = create_refresh_token(user_id)
                response.set_cookie(
                    key="refresh_token",
                    value=new_refresh,
                    httponly=True,
                    secure=settings.cookie_secure,
                    samesite=settings.cookie_samesite,
                    max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
                    domain=settings.cookie_domain,
                    path="/auth/refresh",
                )
    except Exception:
        pass

    return {"status": "refreshed"}


@router.post("/logout")
async def logout(response: Response) -> dict:
    _clear_auth_cookies(response)
    return {"status": "logged out"}


@router.get("/me")
async def me(user: User = Depends(get_current_user)) -> dict:
    return {"id": user.id, "email": user.email, "full_name": user.full_name}


@router.patch("/me")
async def update_me(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    body = await request.json()
    if "full_name" in body:
        user.full_name = body["full_name"]
    await db.commit()
    return {"id": user.id, "email": user.email, "full_name": user.full_name}


@router.post("/change-password")
async def change_password(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    body = await request.json()
    current = body.get("current_password", "")
    new_pw = body.get("new_password", "")
    if not current or not new_pw:
        raise HTTPException(status_code=400, detail="current_password and new_password required")
    if len(new_pw) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if not verify_password(current, user.password_hash):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    user.password_hash = hash_password(new_pw)
    await db.commit()
    return {"ok": True}


@router.post("/register")
async def register(
    payload: UserRegister,
    db: AsyncSession = Depends(get_db),
) -> dict:
    q = await db.execute(select(User).where(User.email == payload.email).limit(1))
    if q.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return {"id": str(user.id), "email": user.email, "full_name": user.full_name}


@router.post("/forgot-password")
async def forgot_password(
    payload: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    import secrets

    q = await db.execute(select(User).where(User.email == payload.email).limit(1))
    user = q.scalar_one_or_none()

    # Always return success to prevent email enumeration
    if not user:
        return {"ok": True}

    code = "".join([str(secrets.randbelow(10)) for _ in range(6)])
    _reset_codes[payload.email] = code

    # In development: print to console. In production: send email.
    from app.core.logger import logger
    logger.info(f"[RESET CODE] {payload.email} → {code}")
    print(f"\n{'='*50}")
    print(f"  PASSWORD RESET CODE for {payload.email}")
    print(f"  CODE: {code}")
    print(f"{'='*50}\n")

    return {"ok": True}


@router.post("/reset-password")
async def reset_password(
    payload: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    stored_code = _reset_codes.get(payload.email)
    if not stored_code or stored_code != payload.code:
        raise HTTPException(status_code=400, detail="Invalid or expired reset code")

    q = await db.execute(select(User).where(User.email == payload.email).limit(1))
    user = q.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.password_hash = hash_password(payload.new_password)
    await db.commit()

    # Invalidate the code
    _reset_codes.pop(payload.email, None)

    return {"ok": True}
