from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.auth import router as auth_router
from app.models.auth import AuthSession
from app.models.audit_log import AuditLog
from app.models.user import User
from app.core.security import create_access_token, create_refresh_token, hash_password
from app.middleware.auth import AuthMiddleware
from app.middleware.csrf import CSRFMiddleware
from app.services import auth_rate_limit


def build_test_app() -> FastAPI:
    test_app = FastAPI()
    test_app.add_middleware(AuthMiddleware)
    test_app.add_middleware(CSRFMiddleware)
    test_app.include_router(auth_router)
    return test_app


class FakeScalarResult:
    def __init__(self, item, rowcount: int | None = None):
        self._item = item
        self.rowcount = rowcount

    def scalar_one_or_none(self):
        return self._item


class FakeSession:
    def __init__(self, user: User):
        self.user = user
        self.users = {user.id: user}
        self.auth_sessions: dict[uuid.UUID, AuthSession] = {}
        self.audit_entries: list[AuditLog] = []

    def add(self, obj):
        if isinstance(obj, AuthSession):
            obj.id = obj.id or uuid.uuid4()
            self.auth_sessions[obj.id] = obj
        elif isinstance(obj, AuditLog):
            self.audit_entries.append(obj)

    async def execute(self, stmt):
        stmt_text = str(stmt)
        if "UPDATE auth_sessions" in stmt_text:
            updated = 0
            now = datetime.now(timezone.utc)
            for session in self.auth_sessions.values():
                if session.user_id == self.user.id and session.revoked_at is None:
                    session.revoked_at = now
                    updated += 1
            return FakeScalarResult(None, rowcount=updated)
        return FakeScalarResult(self.user)

    async def get(self, model, obj_id):
        model_name = getattr(model, "__name__", "")
        if model_name == "User":
            return self.users.get(uuid.UUID(str(obj_id)))
        if model_name == "AuthSession":
            return self.auth_sessions.get(uuid.UUID(str(obj_id)))
        return None

    async def commit(self):
        return None

    async def flush(self):
        return None


@pytest.fixture(autouse=True)
def clear_auth_rate_limits(monkeypatch):
    auth_rate_limit._memory_windows.clear()
    monkeypatch.setattr(auth_rate_limit, "redis_available", lambda: False)
    yield
    auth_rate_limit._memory_windows.clear()


@pytest.fixture
def fake_db():
    user = User(
        id=uuid.uuid4(),
        email="tester@example.com",
        password_hash=hash_password("correct-password"),
        full_name="Tester",
        is_active=True,
    )
    return FakeSession(user)


@pytest_asyncio.fixture
async def auth_client(fake_db):
    from app.api import deps

    app = build_test_app()

    async def get_db_override():
        yield fake_db

    app.dependency_overrides[deps.get_db] = get_db_override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        try:
            yield client, fake_db
        finally:
            app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_login_creates_revocable_session_and_audit_entry(auth_client):
    client, db = auth_client
    response = await client.post("/auth/login", json={"email": db.user.email, "password": "correct-password"})
    assert response.status_code == 200
    assert len(db.auth_sessions) == 1
    session = next(iter(db.auth_sessions.values()))
    assert session.revoked_at is None
    assert any(entry.action == "login" for entry in db.audit_entries)


@pytest.mark.asyncio
async def test_login_is_rate_limited_after_five_invalid_attempts(auth_client):
    client, db = auth_client
    for _ in range(5):
        # Each attempt with wrong password is rejected (401) but still counted toward the rate limit.
        response = await client.post("/auth/login", json={"email": db.user.email, "password": "wrong-password"})
        assert response.status_code == 401
    blocked = await client.post("/auth/login", json={"email": db.user.email, "password": "wrong-password"})
    assert blocked.status_code == 429


@pytest.mark.asyncio
async def test_register_is_rate_limited(auth_client):
    client, db = auth_client
    for _ in range(2):
        response = await client.post("/auth/register", json={"email": "newuser@example.com", "password": "password123"})
        # Should be 409 because email might not be taken (in fake DB, or maybe it returns success/something else, but it counts).
    blocked = await client.post("/auth/register", json={"email": "newuser@example.com", "password": "password123"})
    assert blocked.status_code == 429


@pytest.mark.asyncio
async def test_forgot_password_is_rate_limited(auth_client):
    client, db = auth_client
    for _ in range(3):
        await client.post("/auth/forgot-password", json={"email": db.user.email})
    blocked = await client.post("/auth/forgot-password", json={"email": db.user.email})
    assert blocked.status_code == 429


@pytest.mark.asyncio
async def test_reset_password_is_rate_limited(auth_client):
    from app.services.reset_codes import store_reset_code
    client, db = auth_client

    store_reset_code(db.user.email, "123456")

    for _ in range(5):
        await client.post("/auth/reset-password", json={
            "email": db.user.email,
            "code": "000000",
            "new_password": "newpassword123"
        })

    blocked = await client.post("/auth/reset-password", json={
        "email": db.user.email,
        "code": "000000",
        "new_password": "newpassword123"
    })
    assert blocked.status_code == 429


@pytest.mark.asyncio
async def test_refresh_reuse_revokes_session(auth_client):
    client, db = auth_client
    session = AuthSession(
        id=uuid.uuid4(),
        user_id=db.user.id,
        refresh_jti="old-jti",
        token_family="family-1",
        issued_at=db.user.created_at,
        expires_at=db.user.created_at,
        revoked_at=None,
        replaced_by_jti=None,
        ip_address="127.0.0.1",
        user_agent="pytest",
    )
    db.add(session)
    valid_token = create_refresh_token(db.user.id, session_id=session.id, token_family=session.token_family, refresh_jti=session.refresh_jti)
    client.cookies.set("refresh_token", valid_token, path="/auth/refresh")
    refreshed = await client.post("/auth/refresh")
    assert refreshed.status_code == 200
    rotated_jti = db.auth_sessions[session.id].refresh_jti
    assert rotated_jti != "old-jti"

    stale_token = create_refresh_token(db.user.id, session_id=session.id, token_family=session.token_family, refresh_jti="old-jti")
    client.cookies.clear()
    client.cookies.set("refresh_token", stale_token, path="/auth/refresh")
    reused = await client.post("/auth/refresh")
    assert reused.status_code == 401
    assert db.auth_sessions[session.id].revoked_at is not None


@pytest.mark.asyncio
async def test_logout_revokes_current_session(auth_client):
    client, db = auth_client
    session = AuthSession(
        id=uuid.uuid4(),
        user_id=db.user.id,
        refresh_jti="refresh-jti",
        token_family="family-2",
        issued_at=db.user.created_at,
        expires_at=db.user.created_at,
        revoked_at=None,
        replaced_by_jti=None,
        ip_address="127.0.0.1",
        user_agent="pytest",
    )
    db.add(session)
    access_token = create_access_token(db.user.id, session_id=session.id)
    client.cookies.set("access_token", access_token, path="/")
    response = await client.post("/auth/logout")
    assert response.status_code == 200
    assert db.auth_sessions[session.id].revoked_at is not None


@pytest.mark.asyncio
async def test_logout_all_revokes_all_sessions_and_requires_csrf(auth_client):
    client, db = auth_client
    first = AuthSession(
        id=uuid.uuid4(),
        user_id=db.user.id,
        refresh_jti="first-jti",
        token_family="family-a",
        issued_at=db.user.created_at,
        expires_at=db.user.created_at,
        revoked_at=None,
        replaced_by_jti=None,
        ip_address="127.0.0.1",
        user_agent="pytest",
    )
    second = AuthSession(
        id=uuid.uuid4(),
        user_id=db.user.id,
        refresh_jti="second-jti",
        token_family="family-b",
        issued_at=db.user.created_at,
        expires_at=db.user.created_at,
        revoked_at=None,
        replaced_by_jti=None,
        ip_address="127.0.0.1",
        user_agent="pytest",
    )
    db.add(first)
    db.add(second)
    access_token = create_access_token(db.user.id, session_id=first.id)
    client.cookies.set("access_token", access_token, path="/")
    client.cookies.set("csrf_token", "csrf-123", path="/")

    forbidden = await client.post("/auth/logout-all")
    assert forbidden.status_code == 403

    response = await client.post("/auth/logout-all", headers={"X-CSRF-Token": "csrf-123"})
    assert response.status_code == 200
    assert db.auth_sessions[first.id].revoked_at is not None
    assert db.auth_sessions[second.id].revoked_at is not None
