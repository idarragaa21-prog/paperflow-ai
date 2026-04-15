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

import uuid
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import ARRAY
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID as PGUUID
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.main import app
from app.api.deps import get_db, get_current_user
from app.database import Base
from app.models.membership import ProjectMembership
from app.models.paper import Paper
from app.models.project import Project
from app.models.reference_item import ReferenceItem
from app.models.search import Search, SearchResult
from app.models.user import User
from app.core.security import hash_password

pytestmark = pytest.mark.asyncio


@compiles(PGUUID, "sqlite")
def _compile_uuid_sqlite(_type, _compiler, **_kw):
    return "TEXT"


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(_type, _compiler, **_kw):
    return "TEXT"


@compiles(INET, "sqlite")
def _compile_inet_sqlite(_type, _compiler, **_kw):
    return "TEXT"


@compiles(ARRAY, "sqlite")
def _compile_array_sqlite(_type, _compiler, **_kw):
    return "TEXT"

# ── In-memory SQLite engine for tests ────────────────────────────────────────

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
_session_maker = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


async def _init_db() -> None:
    async with _engine.begin() as conn:
        # Import all models so Base has them registered
        import app.models  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)


async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with _session_maker() as session:
        yield session


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="module", autouse=True)
async def setup_db():
    await _init_db()
    yield
    await _engine.dispose()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with _session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a fresh user for each test."""
    user = User(
        id=uuid.uuid4(),
        email=f"test-{uuid.uuid4().hex[:8]}@paperflow.example.com",
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
    """TestClient with DB override and no external service calls."""
    app.dependency_overrides[get_db] = _override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def authed_client(test_user: User) -> AsyncGenerator[AsyncClient, None]:
    """TestClient pre-authenticated as test_user (bypasses cookie/JWT)."""
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = lambda: test_user
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
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

    async def test_health_services_includes_llm_runtime(self, client: AsyncClient):
        data = (await client.get("/health/services")).json()
        assert "services" in data
        assert "llm_runtime" in data["services"]


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
        r = await client.post("/auth/login", json={"email": "nobody@test.com", "password": "any"})
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


@pytest.mark.asyncio
class TestSharedProjectAccess:
    async def test_viewer_can_access_references_datasets_writing_and_chat(self, db_session: AsyncSession):
        owner = User(
            id=uuid.uuid4(),
            email=f"owner-{uuid.uuid4().hex[:8]}@paperflow.example.com",
            full_name="Owner",
            password_hash=hash_password("pass12345"),
            is_active=True,
        )
        viewer = User(
            id=uuid.uuid4(),
            email=f"viewer-{uuid.uuid4().hex[:8]}@paperflow.example.com",
            full_name="Viewer",
            password_hash=hash_password("pass12345"),
            is_active=True,
        )
        project = Project(user_id=owner.id, title="Shared Workspace")
        db_session.add_all([owner, viewer, project])
        await db_session.flush()
        db_session.add(ProjectMembership(project_id=project.id, user_id=viewer.id, role="viewer"))
        paper = Paper(
            project_id=project.id,
            title="Shared paper",
            authors="Owner, Viewer",
            filename="shared.pdf",
            file_path="papers/shared.pdf",
            content_hash="hash-shared-paper",
            processing_status="ready",
            is_processed=True,
        )
        reference = ReferenceItem(project_id=project.id, title="Shared reference", source_format="manual")
        db_session.add_all([paper, reference])
        await db_session.commit()

        app.dependency_overrides[get_db] = _override_get_db
        app.dependency_overrides[get_current_user] = lambda: viewer
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            with (
                patch("app.api.chat.ask", new=AsyncMock(return_value={
                    "session_id": str(uuid.uuid4()),
                    "answer": "Grounded answer",
                    "claim_type": "supported",
                    "confidence": 0.9,
                    "grounded": True,
                    "citations": [],
                })),
                patch("app.api.chat.vector_index.index_paper", new=AsyncMock(return_value=None)),
            ):
                references_r = await client.get("/references", params={"project_id": str(project.id)})
                datasets_r = await client.get("/datasets/derived", params={"project_id": str(project.id)})
                writing_r = await client.get("/writing/documents", params={"project_id": str(project.id)})
                chat_r = await client.post(
                    f"/projects/{project.id}/chat",
                    json={"question": "What is the main finding?", "task_type": "chat", "max_citations": 4},
                )

        app.dependency_overrides.clear()

        assert references_r.status_code == 200
        assert datasets_r.status_code == 200
        assert writing_r.status_code == 200
        assert chat_r.status_code == 200

    async def test_viewer_can_run_and_reopen_project_search_history(self, db_session: AsyncSession):
        owner = User(
            id=uuid.uuid4(),
            email=f"owner-{uuid.uuid4().hex[:8]}@paperflow.example.com",
            full_name="Owner",
            password_hash=hash_password("pass12345"),
            is_active=True,
        )
        viewer = User(
            id=uuid.uuid4(),
            email=f"viewer-{uuid.uuid4().hex[:8]}@paperflow.example.com",
            full_name="Viewer",
            password_hash=hash_password("pass12345"),
            is_active=True,
        )
        project = Project(user_id=owner.id, title="Shared Search")
        db_session.add_all([owner, viewer, project])
        await db_session.flush()
        db_session.add(ProjectMembership(project_id=project.id, user_id=viewer.id, role="viewer"))
        seeded_search = Search(
            project_id=project.id,
            query="viewer reopen history",
            source="federated",
            results_count=1,
        )
        db_session.add(seeded_search)
        await db_session.flush()
        db_session.add(
            SearchResult(
                search_id=seeded_search.id,
                title="Seeded shared search result",
                source="pubmed",
                is_open_access=True,
                relevance_score=0.9,
            )
        )
        await db_session.commit()

        app.dependency_overrides[get_db] = _override_get_db
        app.dependency_overrides[get_current_user] = lambda: viewer
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            with patch(
                "app.api.search.federated_search",
                new=AsyncMock(
                    return_value={
                        "count": 1,
                        "cached": False,
                        "sources": ["pubmed"],
                        "results": [
                            {
                                "title": "Shared search result",
                                "source": "pubmed",
                                "is_open_access": True,
                                "relevance_score": 0.9,
                            }
                        ],
                    }
                ),
            ):
                search_r = await client.post(
                    "/search/federated",
                    json={"project_id": str(project.id), "query": "rotator cuff repair", "max_results": 5},
                )
                history_r = await client.get(f"/search/projects/{project.id}/searches")

                assert search_r.status_code == 200
                assert history_r.status_code == 200
                history = history_r.json()
                assert len(history) >= 1
                saved_search = next(item for item in history if item["query"] == "viewer reopen history")

                results_r = await client.get(f"/search/{saved_search['id']}/results")

        app.dependency_overrides.clear()

        assert results_r.status_code == 200
        assert results_r.json()[0]["title"] == "Seeded shared search result"

    async def test_viewer_cannot_mutate_editor_only_endpoints(self, db_session: AsyncSession):
        owner = User(
            id=uuid.uuid4(),
            email=f"owner-{uuid.uuid4().hex[:8]}@paperflow.example.com",
            full_name="Owner",
            password_hash=hash_password("pass12345"),
            is_active=True,
        )
        viewer = User(
            id=uuid.uuid4(),
            email=f"viewer-{uuid.uuid4().hex[:8]}@paperflow.example.com",
            full_name="Viewer",
            password_hash=hash_password("pass12345"),
            is_active=True,
        )
        project = Project(user_id=owner.id, title="Viewer locked")
        db_session.add_all([owner, viewer, project])
        await db_session.flush()
        db_session.add(ProjectMembership(project_id=project.id, user_id=viewer.id, role="viewer"))
        await db_session.commit()

        app.dependency_overrides[get_db] = _override_get_db
        app.dependency_overrides[get_current_user] = lambda: viewer
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            create_writing_r = await client.post(
                "/writing/documents",
                json={"project_id": str(project.id), "title": "Viewer draft", "mode": "meta_analysis"},
            )
            create_dataset_r = await client.post(
                "/datasets/derive",
                json={"project_id": str(project.id), "preset": "meta_binary_random", "title": "Viewer dataset"},
            )
            import_reference_r = await client.post(
                "/references/import",
                json={"project_id": str(project.id), "format": "bibtex", "content": "@article{viewer,title={Viewer Ref}}"},
            )

        app.dependency_overrides.clear()

        assert create_writing_r.status_code == 403
        assert create_dataset_r.status_code == 403
        assert import_reference_r.status_code == 403


@pytest.mark.asyncio
class TestProjectInvitations:
    async def test_owner_can_invite_unregistered_email_and_registration_accepts_invitation(self, db_session: AsyncSession):
        owner = User(
            id=uuid.uuid4(),
            email=f"owner-{uuid.uuid4().hex[:8]}@paperflow.example.com",
            full_name="Owner",
            password_hash=hash_password("pass12345"),
            is_active=True,
        )
        project = Project(user_id=owner.id, title="Shared by invite")
        db_session.add_all([owner, project])
        await db_session.commit()

        async def get_db_override():
            yield db_session

        app.dependency_overrides[get_db] = get_db_override
        app.dependency_overrides[get_current_user] = lambda: owner
        owner_transport = ASGITransport(app=app, client=("198.51.100.31", 5501))
        async with AsyncClient(transport=owner_transport, base_url="http://test") as owner_client:
            owner_client.cookies.set("access_token", "token")
            owner_client.cookies.set("csrf_token", "csrf-123")
            created = await owner_client.post(
                f"/projects/{project.id}/members",
                json={"email": "new-collaborator@example.com", "role": "viewer"},
                headers={"X-CSRF-Token": "csrf-123"},
            )
            invites = await owner_client.get(f"/projects/{project.id}/invitations")

        app.dependency_overrides.clear()

        assert created.status_code == 200
        assert created.json()["kind"] == "invitation"
        assert created.json()["delivery_status"] == "manual_required"
        assert created.json()["delivery_method"] == "manual_link"
        assert created.json()["invitation_url"].endswith(f"/project-invitations/{created.json()['invitation']['token']}")
        assert invites.status_code == 200
        assert invites.json()[0]["email"] == "new-collaborator@example.com"
        invitation_token = created.json()["invitation"]["token"]

        async def public_db_override():
            yield db_session

        from app.services import auth_rate_limit
        auth_rate_limit._memory_windows.clear()

        app.dependency_overrides[get_db] = public_db_override
        public_transport = ASGITransport(app=app, client=("198.51.100.32", 5502))
        async with AsyncClient(transport=public_transport, base_url="http://test") as public_client:
            lookup = await public_client.get(f"/projects/invitations/{invitation_token}")
            registered = await public_client.post(
                "/auth/register",
                json={
                    "email": "new-collaborator@example.com",
                    "password": "pass12345",
                    "full_name": "New Collaborator",
                    "invitation_token": invitation_token,
                },
            )

        app.dependency_overrides.clear()

        assert lookup.status_code == 200
        assert lookup.json()["status"] == "pending"
        assert registered.status_code == 200
        assert registered.json()["accepted_project_id"] == str(project.id)

        app.dependency_overrides[get_db] = get_db_override
        app.dependency_overrides[get_current_user] = lambda: owner
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as owner_client:
            members = await owner_client.get(f"/projects/{project.id}/members")
            invite_lookup = await owner_client.get(f"/projects/invitations/{invitation_token}")

        app.dependency_overrides.clear()

        assert members.status_code == 200
        emails = [item["email"] for item in members.json()]
        assert "new-collaborator@example.com" in emails
        assert invite_lookup.status_code == 200
        assert invite_lookup.json()["status"] == "accepted"


@pytest.mark.asyncio
class TestDeepResearchAccess:
    async def test_deep_research_invalid_project_id(self, authed_client: AsyncClient):
        response = await authed_client.post(
            "/research/deep",
            json={
                "query": "test query",
                "source_mode": "project",
                "project_id": "invalid-uuid-string"
            }
        )
        assert response.status_code == 400
        assert response.json() == {"detail": "Invalid input"}

    async def test_viewer_can_generate_project_mode_deep_research(self, db_session: AsyncSession):
        owner = User(
            id=uuid.uuid4(),
            email=f"owner-{uuid.uuid4().hex[:8]}@paperflow.example.com",
            full_name="Owner",
            password_hash=hash_password("pass12345"),
            is_active=True,
        )
        viewer = User(
            id=uuid.uuid4(),
            email=f"viewer-{uuid.uuid4().hex[:8]}@paperflow.example.com",
            full_name="Viewer",
            password_hash=hash_password("pass12345"),
            is_active=True,
        )
        project = Project(user_id=owner.id, title="Shared research")
        db_session.add_all([owner, viewer, project])
        await db_session.flush()
        db_session.add(ProjectMembership(project_id=project.id, user_id=viewer.id, role="viewer"))
        await db_session.commit()

        async def get_db_override():
            yield db_session

        app.dependency_overrides[get_db] = get_db_override
        app.dependency_overrides[get_current_user] = lambda: viewer
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            with patch(
                "app.api.research.generate_deep_research_report",
                new=AsyncMock(
                    return_value={
                        "status": "completed",
                        "query": "rotator cuff repair",
                        "sections": [],
                        "papers": [],
                        "papers_analyzed": 0,
                        "metadata": {"project_id": str(project.id), "source": "project_library"},
                    }
                ),
            ):
                response = await client.post(
                    "/research/deep",
                    json={
                        "query": "rotator cuff repair",
                        "source_mode": "project",
                        "project_id": str(project.id),
                    },
                )

        app.dependency_overrides.clear()

        assert response.status_code == 200
        assert response.json()["status"] == "completed"
        assert response.json()["metadata"]["project_id"] == str(project.id)
