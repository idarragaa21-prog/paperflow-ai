from __future__ import annotations

from datetime import datetime, timedelta, timezone
import uuid
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from jose import jwt as jose_jwt

from app.api.auth import router as auth_router
from app.api.clinical import router as clinical_router
from app.api.deps import get_current_user, get_db
from app.config import settings
from app.core.security import create_access_token, hash_password
from app.middleware.auth import AuthMiddleware
from app.middleware.csrf import CSRFMiddleware
from app.models.audit_log import AuditLog
from app.models.auth import AuthSession
from app.models.user import User
from app.services import auth_rate_limit


class FakeScalar:
    def __init__(self, item, rowcount: int | None = None):
        self._item = item
        self.rowcount = rowcount

    def scalar_one_or_none(self):
        return self._item

    def scalars(self):
        return self

    def all(self):
        return [self._item] if self._item is not None else []


class FakeSession:
    def __init__(self, owner: User, other: User):
        self.owner = owner
        self.other = other
        self._users = {owner.id: owner, other.id: other}
        self._sessions: dict[uuid.UUID, AuthSession] = {}
        self._audit: list[AuditLog] = []

    def add(self, obj):
        if isinstance(obj, AuthSession):
            obj.id = obj.id or uuid.uuid4()
            self._sessions[obj.id] = obj
        elif isinstance(obj, AuditLog):
            self._audit.append(obj)

    async def execute(self, stmt):
        stmt_text = str(stmt).lower()
        if "users" in stmt_text:
            return FakeScalar(self.owner)
        return FakeScalar(None)

    async def get(self, model, obj_id):
        name = getattr(model, "__name__", "")
        parsed_id = uuid.UUID(str(obj_id)) if not isinstance(obj_id, uuid.UUID) else obj_id
        if name == "User":
            return self._users.get(parsed_id)
        if name == "AuthSession":
            return self._sessions.get(parsed_id)
        return None

    async def commit(self):
        pass

    async def flush(self):
        pass

    async def refresh(self, _obj):
        pass


class FakeConsult:
    def __init__(self, *, consult_id: uuid.UUID, user_id: uuid.UUID, project_id: uuid.UUID | None = None):
        self.id = consult_id
        self.user_id = user_id
        self.project_id = project_id


def _make_user(email: str) -> User:
    return User(
        id=uuid.uuid4(),
        email=email,
        password_hash=hash_password("password123"),
        full_name="Test User",
        is_active=True,
    )


def _build_app(db: FakeSession, acting_user: User) -> FastAPI:
    app = FastAPI()
    app.add_middleware(AuthMiddleware)
    app.add_middleware(CSRFMiddleware)
    app.include_router(auth_router)
    app.include_router(clinical_router)

    async def _db():
        yield db

    async def _user():
        return acting_user

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_user] = _user
    return app


@pytest.fixture(autouse=True)
def _clear_rate_limits(monkeypatch):
    auth_rate_limit._memory_windows.clear()
    monkeypatch.setattr(auth_rate_limit, "redis_available", lambda: False)
    yield
    auth_rate_limit._memory_windows.clear()


@pytest.fixture
def two_users():
    owner = _make_user("owner@example.com")
    other = _make_user("other@example.com")
    return owner, other


@pytest.fixture
def fake_db(two_users):
    owner, other = two_users
    return FakeSession(owner, other)


@pytest_asyncio.fixture
async def owner_client(fake_db: FakeSession, two_users):
    owner, _ = two_users
    app = _build_app(fake_db, owner)
    token = create_access_token(owner.id)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        client.cookies.set("access_token", token, path="/")
        client.cookies.set("csrf_token", "valid-csrf", path="/")
        yield client, app, fake_db, owner


@pytest_asyncio.fixture
async def other_client(fake_db: FakeSession, two_users):
    _, other = two_users
    app = _build_app(fake_db, other)
    token = create_access_token(other.id)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        client.cookies.set("access_token", token, path="/")
        client.cookies.set("csrf_token", "valid-csrf", path="/")
        yield client, app, fake_db, other


@pytest_asyncio.fixture
async def auth_only_client(fake_db: FakeSession, two_users):
    owner, _ = two_users
    app = FastAPI()
    app.add_middleware(AuthMiddleware)
    app.add_middleware(CSRFMiddleware)
    app.include_router(auth_router)

    async def _db():
        yield fake_db

    app.dependency_overrides[get_db] = _db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, app, fake_db, owner


def _patch_consult_serialization(monkeypatch, consult: FakeConsult):
    monkeypatch.setattr("app.api.clinical.get_consult", AsyncMock(return_value=consult))
    monkeypatch.setattr(
        "app.api.clinical.serialize_consult",
        lambda item: {"id": str(item.id), "user_id": str(item.user_id), "project_id": str(item.project_id) if item.project_id else None},
    )


@pytest.mark.asyncio
async def test_idor_user_cannot_access_other_users_consult(other_client, two_users, monkeypatch):
    client, _app, _db, _other = other_client
    owner, _ = two_users
    consult = FakeConsult(consult_id=uuid.uuid4(), user_id=owner.id)
    _patch_consult_serialization(monkeypatch, consult)

    response = await client.get(f"/clinical/consults/{consult.id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_owner_can_access_own_consult(owner_client, monkeypatch):
    client, _app, _db, owner = owner_client
    consult = FakeConsult(consult_id=uuid.uuid4(), user_id=owner.id)
    _patch_consult_serialization(monkeypatch, consult)

    response = await client.get(f"/clinical/consults/{consult.id}")
    assert response.status_code == 200
    assert response.json()["id"] == str(consult.id)


@pytest.mark.asyncio
async def test_csrf_mutation_without_token_is_rejected(owner_client, monkeypatch):
    client, _app, _db, owner = owner_client
    consult = FakeConsult(consult_id=uuid.uuid4(), user_id=owner.id)
    monkeypatch.setattr("app.api.clinical.create_clinical_consult", AsyncMock(return_value=consult))
    monkeypatch.setattr("app.api.clinical.serialize_consult", lambda item: {"id": str(item.id)})

    response = await client.post(
        "/clinical/consults",
        json={"question": "Should aspirin be used in secondary prevention?", "mode": "brief"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_csrf_mutation_with_wrong_token_is_rejected(owner_client, monkeypatch):
    client, _app, _db, owner = owner_client
    consult = FakeConsult(consult_id=uuid.uuid4(), user_id=owner.id)
    monkeypatch.setattr("app.api.clinical.create_clinical_consult", AsyncMock(return_value=consult))
    monkeypatch.setattr("app.api.clinical.serialize_consult", lambda item: {"id": str(item.id)})

    response = await client.post(
        "/clinical/consults",
        json={"question": "Should statins be used post-MI?", "mode": "standard"},
        headers={"X-CSRF-Token": "bad-token"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_csrf_mutation_with_correct_token_passes(owner_client, monkeypatch):
    client, _app, _db, owner = owner_client
    consult = FakeConsult(consult_id=uuid.uuid4(), user_id=owner.id)
    monkeypatch.setattr("app.api.clinical.create_clinical_consult", AsyncMock(return_value=consult))
    monkeypatch.setattr("app.api.clinical.serialize_consult", lambda item: {"id": str(item.id)})

    response = await client.post(
        "/clinical/consults",
        json={"question": "What is the evidence for dual antiplatelet therapy duration?", "mode": "deep"},
        headers={"X-CSRF-Token": "valid-csrf"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_expired_access_token_returns_401(fake_db: FakeSession, two_users):
    owner, _ = two_users
    app = _build_app(fake_db, owner)
    app.dependency_overrides.pop(get_current_user, None)

    expired_payload = {
        "sub": str(owner.id),
        "type": "access",
        "exp": datetime.now(timezone.utc) - timedelta(minutes=30),
    }
    expired_token = jose_jwt.encode(expired_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        client.cookies.set("access_token", expired_token, path="/")
        client.cookies.set("csrf_token", "csrf", path="/")
        response = await client.post(
            "/clinical/consults",
            json={"question": "test question"},
            headers={"X-CSRF-Token": "csrf"},
        )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_malformed_jwt_returns_401(fake_db: FakeSession, two_users):
    owner, _ = two_users
    app = _build_app(fake_db, owner)
    app.dependency_overrides.pop(get_current_user, None)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        client.cookies.set("access_token", "not.a.valid.jwt", path="/")
        client.cookies.set("csrf_token", "csrf", path="/")
        response = await client.post(
            "/clinical/consults",
            json={"question": "test question"},
            headers={"X-CSRF-Token": "csrf"},
        )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_rate_limited_on_email_after_five_failures(auth_only_client):
    client, _app, _db, owner = auth_only_client

    for _ in range(5):
        attempt = await client.post("/auth/login", json={"email": owner.email, "password": "wrong"})
        assert attempt.status_code == 401

    blocked = await client.post("/auth/login", json={"email": owner.email, "password": "wrong"})
    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers


@pytest.mark.asyncio
async def test_login_succeeds_with_correct_password(auth_only_client):
    client, _app, _db, owner = auth_only_client
    response = await client.post("/auth/login", json={"email": owner.email, "password": "password123"})
    assert response.status_code == 200
    assert "access_token" in response.cookies


@pytest.mark.asyncio
async def test_clinical_consult_with_deeply_nested_pico_does_not_crash(owner_client, monkeypatch):
    client, _app, _db, owner = owner_client

    consult = FakeConsult(consult_id=uuid.uuid4(), user_id=owner.id)
    monkeypatch.setattr("app.api.clinical.create_clinical_consult", AsyncMock(return_value=consult))
    monkeypatch.setattr("app.api.clinical.serialize_consult", lambda item: {"id": str(item.id)})

    nested: dict = {"leaf": "value"}
    for _ in range(100):
        nested = {"level": nested}

    response = await client.post(
        "/clinical/consults",
        json={
            "question": "Should beta blockers be initiated after AMI?",
            "mode": "standard",
            "pico": nested,
        },
        headers={"X-CSRF-Token": "valid-csrf"},
    )
    assert response.status_code < 500
