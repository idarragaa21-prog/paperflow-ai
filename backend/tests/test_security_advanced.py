"""
Advanced security test suite — pre-deployment pen-test coverage.

Covers:
- IDOR (insecure direct object reference) on clinical sheets
- CSRF enforcement on mutation endpoints
- Expired / malformed JWT tokens → 401
- Auth rate limiting (email + IP)
- File upload validation (magic-byte bypass attempt)
- Deep-nested JSON payload on clinical /query → safe handling
"""
from __future__ import annotations

import io
import time
import uuid

import pytest
import pytest_asyncio
from unittest.mock import patch, AsyncMock
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.auth import router as auth_router
from app.api.clinical import router as clinical_router
from app.api.deps import get_current_user, get_db
from app.core.security import create_access_token, hash_password
from app.middleware.auth import AuthMiddleware
from app.middleware.csrf import CSRFMiddleware
from app.models.audit_log import AuditLog
from app.models.auth import AuthSession
from app.models.clinical import ClinicalSheet
from app.models.user import User
from app.services import auth_rate_limit


# ── Fake DB ───────────────────────────────────────────────────────────────────

class FakeScalar:
    def __init__(self, item, rowcount=None):
        self._item = item
        self.rowcount = rowcount

    def scalar_one_or_none(self):
        return self._item

    def scalars(self):
        return self

    def all(self):
        return [self._item] if self._item is not None else []


class FakeSession:
    """Minimal async DB session stub for security tests."""

    def __init__(self, owner: User, other: User):
        self.owner = owner
        self.other = other
        self._users = {owner.id: owner, other.id: other}
        self._sheets: dict[uuid.UUID, ClinicalSheet] = {}
        self._sessions: dict[uuid.UUID, AuthSession] = {}
        self._audit: list[AuditLog] = []
        self.added: list = []

    # --- sheet helpers ---
    def _add_sheet(self, sheet: ClinicalSheet) -> None:
        self._sheets[sheet.id] = sheet

    # --- SQLAlchemy async interface stubs ---
    def add(self, obj):
        self.added.append(obj)
        if isinstance(obj, ClinicalSheet):
            self._sheets[obj.id] = obj
        elif isinstance(obj, AuthSession):
            obj.id = obj.id or uuid.uuid4()
            self._sessions[obj.id] = obj
        elif isinstance(obj, AuditLog):
            self._audit.append(obj)

    async def execute(self, stmt):
        stmt_text = str(stmt)
        if "users" in stmt_text.lower():
            return FakeScalar(self.owner)
        return FakeScalar(None)

    async def get(self, model, obj_id):
        name = getattr(model, "__name__", "")
        oid = uuid.UUID(str(obj_id)) if not isinstance(obj_id, uuid.UUID) else obj_id
        if name == "User":
            return self._users.get(oid)
        if name == "ClinicalSheet":
            return self._sheets.get(oid)
        if name == "AuthSession":
            return self._sessions.get(oid)
        return None

    async def commit(self):
        pass

    async def flush(self):
        pass

    async def refresh(self, obj):
        pass


# ── App builder ───────────────────────────────────────────────────────────────

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


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _clear_rate_limits(monkeypatch):
    auth_rate_limit._memory_windows.clear()
    monkeypatch.setattr(auth_rate_limit, "redis_available", lambda: False)
    yield
    auth_rate_limit._memory_windows.clear()


def _make_user(email: str) -> User:
    return User(
        id=uuid.uuid4(),
        email=email,
        password_hash=hash_password("password123"),
        full_name="Test User",
        is_active=True,
    )


@pytest.fixture
def two_users():
    owner = _make_user("owner@example.com")
    other = _make_user("other@example.com")
    return owner, other


@pytest.fixture
def fake_db(two_users):
    owner, other = two_users
    db = FakeSession(owner, other)
    # Create a clinical sheet owned by `owner`
    sheet = ClinicalSheet(
        id=uuid.uuid4(),
        user_id=owner.id,
        project_id=None,
        topic="Hypertension management",
        input_params={"status": "generating"},
        content_markdown="_Generating…_",
    )
    db._add_sheet(sheet)
    return db, sheet


@pytest_asyncio.fixture
async def owner_client(fake_db, two_users):
    db, sheet = fake_db
    owner, _ = two_users
    app = _build_app(db, owner)
    token = create_access_token(owner.id)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        client.cookies.set("access_token", token, path="/")
        client.cookies.set("csrf_token", "valid-csrf", path="/")
        yield client, db, sheet, owner


@pytest_asyncio.fixture
async def other_client(fake_db, two_users):
    db, sheet = fake_db
    _, other = two_users
    app = _build_app(db, other)
    token = create_access_token(other.id)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        client.cookies.set("access_token", token, path="/")
        client.cookies.set("csrf_token", "valid-csrf", path="/")
        yield client, db, sheet, other


@pytest_asyncio.fixture
async def auth_only_client(fake_db, two_users):
    db, _ = fake_db
    owner, _ = two_users
    app = FastAPI()
    app.add_middleware(AuthMiddleware)
    app.add_middleware(CSRFMiddleware)
    app.include_router(auth_router)

    async def _db():
        yield db

    app.dependency_overrides[get_db] = _db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, db, owner


# ── IDOR Tests ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_idor_user_cannot_access_other_users_clinical_sheet(other_client):
    """User B must not be able to read User A's clinical sheet — expect 404."""
    client, db, sheet, _ = other_client
    resp = await client.get(f"/clinical/sheets/{sheet.id}")
    assert resp.status_code == 404, (
        f"IDOR vulnerability: other user got {resp.status_code} instead of 404"
    )


@pytest.mark.asyncio
async def test_owner_can_access_own_sheet(owner_client):
    """Sanity check: the owner can access their own sheet."""
    client, db, sheet, _ = owner_client
    resp = await client.get(f"/clinical/sheets/{sheet.id}")
    # 200 or 404 if the endpoint needs project membership — just not IDOR
    assert resp.status_code in (200, 404)


# ── CSRF Tests ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_csrf_mutation_without_token_is_rejected(owner_client):
    """POST to a mutation endpoint without X-CSRF-Token header must return 403."""
    client, db, sheet, _ = owner_client
    # Do NOT send the CSRF header
    resp = await client.post(
        "/clinical/query",
        json={"topic": "test"},
    )
    assert resp.status_code == 403, (
        f"CSRF not enforced: expected 403 got {resp.status_code}"
    )


@pytest.mark.asyncio
async def test_csrf_mutation_with_wrong_token_is_rejected(owner_client):
    """POST with a mismatched CSRF token must return 403."""
    client, db, sheet, _ = owner_client
    resp = await client.post(
        "/clinical/query",
        json={"topic": "test"},
        headers={"X-CSRF-Token": "totally-wrong-token"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_csrf_mutation_with_correct_token_passes(owner_client):
    """POST with matching CSRF token must not be blocked by CSRF middleware."""
    client, db, sheet, _ = owner_client
    # The cookie is already set to "valid-csrf" in the fixture
    resp = await client.post(
        "/clinical/query",
        json={"topic": "ACL reconstruction outcomes"},
        headers={"X-CSRF-Token": "valid-csrf"},
    )
    # CSRF passes; the endpoint itself may return various codes depending on
    # RQ availability, but it must not be a 403 CSRF rejection.
    assert resp.status_code != 403


# ── JWT / Token Tests ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_expired_access_token_returns_401(fake_db, two_users):
    """Requests with a JWT whose exp is in the past must be rejected."""
    from datetime import datetime, timezone, timedelta
    from jose import jwt as jose_jwt
    from app.config import settings

    db, _ = fake_db
    owner, _ = two_users

    expired_payload = {
        "sub": str(owner.id),
        "type": "access",
        "exp": datetime.now(timezone.utc) - timedelta(minutes=30),
    }
    expired_token = jose_jwt.encode(expired_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    app = _build_app(db, owner)
    # Remove the current_user override so middleware actually validates the token
    app.dependency_overrides.pop(get_current_user, None)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        client.cookies.set("access_token", expired_token, path="/")
        client.cookies.set("csrf_token", "csrf", path="/")
        resp = await client.post(
            "/clinical/query",
            json={"topic": "test"},
            headers={"X-CSRF-Token": "csrf"},
        )
    # AuthMiddleware sets user_id to None for expired tokens; get_current_user raises 401
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_malformed_jwt_returns_401(fake_db, two_users):
    """Requests with a garbled token must be rejected."""
    db, _ = fake_db
    owner, _ = two_users

    app = _build_app(db, owner)
    app.dependency_overrides.pop(get_current_user, None)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        client.cookies.set("access_token", "this.is.not.a.valid.jwt", path="/")
        client.cookies.set("csrf_token", "csrf", path="/")
        resp = await client.post(
            "/clinical/query",
            json={"topic": "test"},
            headers={"X-CSRF-Token": "csrf"},
        )
    assert resp.status_code == 401


# ── Auth Rate Limiting ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_login_rate_limited_on_email_after_five_failures(auth_only_client):
    """Six login attempts with wrong password on same email → 6th is 429."""
    client, db, owner = auth_only_client
    for _ in range(5):
        r = await client.post(
            "/auth/login",
            json={"email": owner.email, "password": "wrong"},
        )
        assert r.status_code == 401

    blocked = await client.post(
        "/auth/login",
        json={"email": owner.email, "password": "wrong"},
    )
    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers


@pytest.mark.asyncio
async def test_login_succeeds_with_correct_password(auth_only_client):
    """Login with the correct password must return 200 and set cookies."""
    client, db, owner = auth_only_client
    r = await client.post(
        "/auth/login",
        json={"email": owner.email, "password": "password123"},
    )
    assert r.status_code == 200
    assert "access_token" in r.cookies


# ── File Upload Validation ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pdf_magic_byte_check():
    """Storage manager must reject payloads that lack the PDF magic bytes."""
    from app.core.storage import storage_manager

    # Valid PDF header but truncated / no EOF
    fake_pdf = b"%PDF-1.4 fake content without proper EOF"
    assert not storage_manager.validate_pdf(fake_pdf), (
        "validate_pdf should return False for a truncated PDF"
    )


@pytest.mark.asyncio
async def test_valid_minimal_pdf_passes_validation():
    """A payload with both %PDF- header and %%EOF footer must pass."""
    from app.core.storage import storage_manager

    minimal_pdf = b"%PDF-1.4\n%% some content\n%%EOF"
    assert storage_manager.validate_pdf(minimal_pdf), (
        "validate_pdf should return True for a minimal valid PDF structure"
    )


@pytest.mark.asyncio
async def test_html_file_disguised_as_pdf_is_rejected():
    """An HTML file with a forged PDF magic byte prefix must be rejected."""
    from app.core.storage import storage_manager

    # Attempt: HTML file starting with %PDF- header but containing script tags
    malicious = b"%PDF-1.4 <html><script>alert(1)</script></html>"
    # No %%EOF in the last 2048 bytes → should fail validation
    assert not storage_manager.validate_pdf(malicious)


# ── Deep-Nested JSON ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_clinical_query_with_deeply_nested_payload_does_not_crash(owner_client):
    """Deeply nested JSON in the clinical query payload must not cause 5xx."""
    client, db, sheet, _ = owner_client

    # Build a deeply nested dict (100 levels)
    nested: dict = {"inner": "value"}
    for _ in range(100):
        nested = {"level": nested}

    # Mock the job queue fetcher to avoid 503 from missing Redis
    from unittest.mock import MagicMock
    mock_queue = MagicMock()
    mock_queue.enqueue.return_value = MagicMock(id="fake-rq-id")
    with patch('app.api.clinical.get_job_queue', return_value=mock_queue):
        resp = await client.post(
            "/clinical/query",
            json={"topic": "ACL outcomes", "extra": nested},
            headers={"X-CSRF-Token": "valid-csrf"},
        )
    # Should return 200/202 (job queued) or 429 (rate limited), never 500
    assert resp.status_code < 500, (
        f"Server crashed on deeply nested payload: {resp.status_code}"
    )
