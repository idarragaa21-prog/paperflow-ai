"""Integration tests for HTTP routers using FastAPI TestClient.

These tests verify the actual HTTP layer — auth, middleware, and endpoint contracts —
which were previously uncovered (only service-level units had tests).

Strategy:
- Use httpx.AsyncClient with ASGITransport to hit the real app
- Override get_db dependency to use an in-memory SQLite for speed
- Override get_current_user where needed to bypass cookie auth
- Mock heavy external services (Qdrant, Grobid) to stay fast
"""
from __future__ import annotations

import asyncio
import os
import tempfile
import uuid
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.main import app
from app.api.deps import get_db, get_current_user
from app.database import Base
from app.models.user import User
from app.core.security import hash_password

# ── File-based SQLite for tests (survives across connections/event loops) ─────
# We use a temp file so that tables created in setup_db persist for all tests.

_db_file = tempfile.mktemp(suffix=".db")
TEST_DATABASE_URL = f"sqlite+aiosqlite:///{_db_file}"

_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
_session_maker = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


def _sync_init_db() -> None:
    """Create all tables synchronously using a dedicated event loop."""
    import app.models  # noqa: F401 — registers all models

    async def _create():
        async with _engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_create())
    finally:
        loop.close()


async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with _session_maker() as session:
        yield session


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    """Create tables once per module, clean up the DB file afterward."""
    _sync_init_db()
    yield
    # Cleanup
    try:
        os.unlink(_db_file)
    except OSError:
        pass


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with _session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a fresh user for each test."""
    user = User(
        id=uuid.uuid4(),
        email=f"test-{uuid.uuid4().hex[:8]}@example.com",
        full_name="Test User",
        password_hash=hash_password("testpass123"),
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """TestClient with DB override and no external service calls.

    Includes a CSRF token so POST/PUT/DELETE requests reach the auth layer
    (returning 401) rather than being blocked by CSRF middleware (returning 403).
    """
    _csrf_token = "test-csrf-token-for-integration-tests"
    app.dependency_overrides[get_db] = _override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        cookies={"csrf_token": _csrf_token},
        headers={"X-CSRF-Token": _csrf_token},
    ) as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def authed_client(test_user: User) -> AsyncGenerator[AsyncClient, None]:
    """TestClient pre-authenticated as test_user (bypasses cookie/JWT and CSRF)."""
    from app.middleware.csrf import CSRFMiddleware

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = lambda: test_user
    _csrf_token = "test-csrf-token-for-integration-tests"
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        cookies={"csrf_token": _csrf_token},
        headers={"X-CSRF-Token": _csrf_token},
    ) as c:
        yield c
    app.dependency_overrides.clear()


# ── /health ───────────────────────────────────────────────────────────────────

class TestHealth:
    async def test_health_returns_200(self, client: AsyncClient):
        r = await client.get("/health")
        assert r.status_code == 200

    async def test_health_has_app_key(self, client: AsyncClient):
        data = (await client.get("/health")).json()
        assert "app" in data
        assert data["app"]["name"] == "PaperFlow AI"

    async def test_health_degraded_features_present(self, client: AsyncClient):
        data = (await client.get("/health")).json()
        assert "degraded_features" in data


# ── /auth/login ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestAuthLogin:
    async def test_login_success_sets_cookies(self, client: AsyncClient, test_user: User):
        r = await client.post("/auth/login", json={"email": test_user.email, "password": "testpass123"})
        assert r.status_code == 200
        assert "access_token" in r.cookies

    async def test_login_wrong_password_returns_401(self, client: AsyncClient, test_user: User):
        r = await client.post("/auth/login", json={"email": test_user.email, "password": "wrongpassword"})
        assert r.status_code == 401

    async def test_login_unknown_email_returns_401(self, client: AsyncClient):
        r = await client.post("/auth/login", json={"email": "nobody@example.com", "password": "anypassword"})
        assert r.status_code == 401

    async def test_login_missing_fields_returns_422(self, client: AsyncClient):
        r = await client.post("/auth/login", json={"email": "only@email.com"})
        assert r.status_code == 422


# ── /auth/me ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestAuthMe:
    async def test_me_requires_auth(self, client: AsyncClient):
        r = await client.get("/auth/me")
        assert r.status_code == 401

    async def test_me_returns_user(self, authed_client: AsyncClient, test_user: User):
        r = await authed_client.get("/auth/me")
        assert r.status_code == 200
        assert r.json()["email"] == test_user.email


# ── /auth/logout ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestAuthLogout:
    async def test_logout_clears_cookies(self, authed_client: AsyncClient):
        r = await authed_client.post("/auth/logout")
        assert r.status_code == 200
        # Cookie cleared = set with empty value or max_age=0
        cookie_header = r.headers.get("set-cookie", "")
        assert "access_token" in cookie_header


# ── /projects ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestProjects:
    async def test_projects_requires_auth(self, client: AsyncClient):
        r = await client.get("/projects")
        assert r.status_code == 401

    async def test_projects_list_empty_for_new_user(self, authed_client: AsyncClient):
        r = await authed_client.get("/projects")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    async def test_create_project(self, authed_client: AsyncClient):
        r = await authed_client.post("/projects", json={"title": "My Test Project"})
        assert r.status_code in (200, 201)
        data = r.json()
        assert data["title"] == "My Test Project"

    async def test_project_appears_in_list(self, authed_client: AsyncClient):
        await authed_client.post("/projects", json={"title": "Visible Project"})
        r = await authed_client.get("/projects")
        titles = [p["title"] for p in r.json()]
        assert "Visible Project" in titles


# ── /papers — auth guard ──────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestPapersAuthGuard:
    async def test_papers_list_requires_auth(self, client: AsyncClient):
        fake_project_id = str(uuid.uuid4())
        r = await client.get(f"/papers/projects/{fake_project_id}")
        assert r.status_code == 401

    async def test_papers_download_requires_auth(self, client: AsyncClient):
        r = await client.post("/papers/download", json={"title": "test", "project_id": str(uuid.uuid4())})
        assert r.status_code == 401


# ── /search — cache hit ───────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestSearchCacheHit:
    async def test_search_requires_auth(self, client: AsyncClient):
        r = await client.post("/search/federated", json={"project_id": str(uuid.uuid4()), "query": "fractura"})
        assert r.status_code == 401

    async def test_search_project_not_found_returns_404(self, authed_client: AsyncClient):
        """Search against a project that belongs to a different user → 404."""
        r = await authed_client.post(
            "/search/federated",
            json={"project_id": str(uuid.uuid4()), "query": "test query here", "max_results": 5},
        )
        # 404 because project doesn't belong to this user
        assert r.status_code == 404

    async def test_search_returns_cached_flag(self, authed_client: AsyncClient):
        """When cache returns a hit the response marks cached=True.

        We mock the cache to return a pre-built payload so the test
        never hits external APIs.
        """
        project_r = await authed_client.post("/projects", json={"title": "Search Cache Test"})
        if project_r.status_code not in (200, 201):
            pytest.skip("Could not create project")
        project_id = project_r.json()["id"]

        cached_payload = {
            "query": "hip fracture",
            "source": "federated",
            "count": 1,
            "results": [{"title": "Cached Paper", "source": "pubmed", "is_open_access": False}],
            "cached": True,
        }

        with patch("app.api.search.cache") as mock_cache:
            mock_cache.generate_search_key = lambda *a, **kw: "test-key"
            mock_cache.get = AsyncMock(return_value=cached_payload)

            r = await authed_client.post(
                "/search/federated",
                json={"project_id": project_id, "query": "hip fracture", "max_results": 5},
            )

        assert r.status_code == 200
        assert r.json()["cached"] is True
