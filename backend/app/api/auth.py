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
    decode_token_payload,
    generate_csrf_token,
    hash_password,
    verify_password,
    verify_token,
)
from app.models.audit_log import AuditLog
from app.models.membership import ProjectInvitation, ProjectMembership
from app.models.project import Project
from app.models.user import User
from app.schemas.auth import ForgotPasswordRequest, ResetPasswordRequest, UserLogin, UserRegister
from app.services import auth_rate_limit, auth_sessions

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
    request: Request,
    credentials: UserLogin,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict:
    identifier = credentials.email.lower().strip()
    client_ip = request.client.host if request.client else "unknown"

    q = await db.execute(select(User).where(User.email == credentials.email))
    user = q.scalar_one_or_none()

    try:
        auth_rate_limit.hit("login_email", identifier, limit=5, window_seconds=300)
        auth_rate_limit.hit("login_ip", client_ip, limit=25, window_seconds=300)
    except auth_rate_limit.AuthRateLimitExceeded as exc:
        raise HTTPException(
            status_code=429,
            detail="Too many authentication attempts",
            headers={"Retry-After": str(exc.retry_after_seconds)},
        ) from exc

    if not user or not user.is_active or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    session = await auth_sessions.create_auth_session(
        db,
        user_id=user.id,
        ip_address=client_ip,
        user_agent=request.headers.get("user-agent"),
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

    user.last_login = datetime.now(timezone.utc)
    db.add(
        AuditLog(
            user_id=user.id,
            action="login",
            entity_type="user",
            entity_id=user.id,
            details={"session_id": str(session.id)},
            ip_address=client_ip,
        )
    )
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

    payload = decode_token_payload(token, "refresh")
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido")
    user_id = UUID(str(payload["sub"]))
    session_id = payload.get("sid")
    token_family = payload.get("fam")
    refresh_jti = payload.get("jti")
    if not session_id or not token_family or not refresh_jti:
        raise HTTPException(status_code=401, detail="Token inválido")

    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Usuario inválido")

    session = await auth_sessions.get_auth_session(db, UUID(str(session_id)))
    if not auth_sessions.is_session_active(session) or session is None:
        raise HTTPException(status_code=401, detail="Sesión inválida")
    if session.token_family != token_family or session.refresh_jti != refresh_jti:
        await auth_sessions.revoke_session_family(db, user_id=user.id, token_family=token_family)
        await db.commit()
        raise HTTPException(status_code=401, detail="Refresh token reuse detected")

    next_refresh_jti = await auth_sessions.rotate_refresh_session(db, session=session, previous_jti=refresh_jti)
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
        samesite=settings.cookie_samesite,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        domain=settings.cookie_domain,
        path="/",
    )
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
    _set_csrf_cookie(response, new_csrf)
    await db.commit()

    return {"status": "refreshed"}


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict:
    token = request.cookies.get("access_token")
    payload = decode_token_payload(token, "access") if token else None
    session_id = payload.get("sid") if payload else None
    if session_id:
        session = await auth_sessions.get_auth_session(db, UUID(str(session_id)))
        if session is not None:
            await auth_sessions.revoke_session(db, session)
            await db.commit()
    _clear_auth_cookies(response)
    return {"status": "logged out"}


@router.post("/logout-all")
async def logout_all(
    response: Response,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    await auth_sessions.revoke_all_sessions(db, user_id=user.id)
    await db.commit()
    _clear_auth_cookies(response)
    return {"status": "logged out everywhere"}


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
    email = payload.email.lower().strip()

    invitation: ProjectInvitation | None = None
    project: Project | None = None
    if payload.invitation_token:
        invite_q = await db.execute(select(ProjectInvitation).where(ProjectInvitation.token == payload.invitation_token).limit(1))
        invitation = invite_q.scalar_one_or_none()
        if invitation is None or invitation.revoked_at is not None:
            raise HTTPException(status_code=404, detail="Invitation not found")
        if invitation.accepted_at is not None:
            raise HTTPException(status_code=409, detail="Invitation already accepted")
        if invitation.email.lower() != email:
            raise HTTPException(status_code=400, detail="Invitation email does not match the registration email")
        project = await db.get(Project, invitation.project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Invitation project not found")

    q = await db.execute(select(User).where(User.email == email).limit(1))
    if q.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        is_active=True,
    )
    db.add(user)
    await db.flush()

    accepted_project_id: str | None = None
    if invitation is not None:
        membership_q = await db.execute(
            select(ProjectMembership)
            .where(ProjectMembership.project_id == invitation.project_id)
            .where(ProjectMembership.user_id == user.id)
            .limit(1)
        )
        membership = membership_q.scalar_one_or_none()
        if membership is None:
            db.add(ProjectMembership(project_id=invitation.project_id, user_id=user.id, role=invitation.role))
        else:
            membership.role = "owner" if project and project.user_id == user.id else invitation.role
        invitation.accepted_at = datetime.now(timezone.utc)
        invitation.accepted_by_user_id = user.id
        accepted_project_id = str(invitation.project_id)

    await db.commit()
    await db.refresh(user)

    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "accepted_project_id": accepted_project_id,
    }


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
