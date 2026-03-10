from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


class FakeUser:
    def __init__(self, user_id: str):
        self.id = user_id
        self.is_active = True


class FakeProject:
    def __init__(self, project_id: str, user_id: str):
        self.id = project_id
        self.user_id = user_id


class FakeSession:
    def __init__(self, user: FakeUser, project: FakeProject):
        self._user = user
        self._project = project
        self.added = []

    async def get(self, model, obj_id):
        # get_current_user loads User; endpoint loads Project
        name = getattr(model, "__name__", "")
        if name == "User":
            return self._user
        if name == "Project":
            return self._project
        return None

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        return None

    async def commit(self):
        return None


@pytest.mark.asyncio
async def test_search_endpoint_cache_hit(monkeypatch):
    cached = {
        "count": 1,
        "results": [
            {
                "pmid": "1",
                "pmcid": None,
                "doi": None,
                "title": "Cached",
                "authors": ["A"],
                "journal": None,
                "pub_year": 2020,
                "abstract": None,
                "is_open_access": False,
                "oa_url": None,
            }
        ],
        "query_translation": None,
        "cached": False,
    }

    async def fake_get(key: str):
        return cached

    async def fake_search_and_fetch(query: str, max_results: int = 20, filters=None):
        raise AssertionError("pubmed_client should not be called on cache hit")

    from app.api import deps
    from app.core.security import create_access_token

    user_id = "00000000-0000-0000-0000-000000000000"
    project_id = "00000000-0000-0000-0000-000000000000"

    monkeypatch.setattr("app.services.cache.cache.get", fake_get)
    monkeypatch.setattr("app.services.pubmed.pubmed_client.search_and_fetch", fake_search_and_fetch)
    async def fake_access(db, project_id, user, required_role="viewer"):
        return FakeProject(project_id, user.id), type("Membership", (), {"role": required_role})()
    monkeypatch.setattr("app.api.search.require_project_access", fake_access)

    # Provide a fake DB session (User + Project)
    async def get_db_override():
        yield FakeSession(FakeUser(user_id), FakeProject(project_id, user_id))

    app.dependency_overrides[deps.get_db] = get_db_override

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.cookies.set("csrf_token", "abc")
        ac.cookies.set("access_token", create_access_token(user_id))
        resp = await ac.post(
            "/search/pubmed",
            json={"project_id": project_id, "query": "hip", "max_results": 5},
            headers={"X-CSRF-Token": "abc"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 200
    body = resp.json()
    assert body["cached"] is True
    assert body["count"] == 1


@pytest.mark.asyncio
async def test_federated_search_reports_partial_success_and_persists_results_per_search(monkeypatch):
    from app.api import deps
    from app.core.security import create_access_token

    user_id = "00000000-0000-0000-0000-000000000000"
    project_id = "11111111-1111-1111-1111-111111111111"
    db = FakeSession(FakeUser(user_id), FakeProject(project_id, user_id))
    federated_payload = {
        "count": 2,
        "results": [
            {
                "pmid": "100",
                "pmcid": None,
                "doi": "10.1000/alpha",
                "title": "Alpha trial",
                "authors": ["A"],
                "journal": "J1",
                "pub_year": 2021,
                "abstract": "Alpha abstract",
                "source": "pubmed",
                "language": "en",
                "is_open_access": True,
                "oa_url": "https://example.org/a.pdf",
            },
            {
                "pmid": None,
                "pmcid": None,
                "doi": "10.1000/beta",
                "title": "Beta review",
                "authors": ["B"],
                "journal": "J2",
                "pub_year": 2022,
                "abstract": "Beta abstract",
                "source": "doaj",
                "language": "en",
                "is_open_access": False,
                "oa_url": None,
            },
        ],
        "query_translation": "alpha beta",
        "cached": False,
        "sources": ["pubmed", "europepmc", "doaj"],
        "partial_success": True,
        "provider_status": {"pubmed": "ok", "europepmc": "error", "doaj": "ok"},
        "warnings": ["Europe PMC no respondió"],
    }

    async def get_db_override():
        yield db

    async def fake_access(db_session, project_id, user, required_role="viewer"):
        return FakeProject(project_id, user.id), type("Membership", (), {"role": required_role})()

    async def fake_cache_get(key: str):
        return None

    async def fake_cache_set(key: str, value, ttl: int = 3600):
        return None

    async def fake_federated_search(query: str, *, max_results: int, filters=None):
        assert max_results == 10
        return federated_payload

    app.dependency_overrides[deps.get_db] = get_db_override
    monkeypatch.setattr("app.api.search.require_project_access", fake_access)
    monkeypatch.setattr("app.api.search.federated_search", fake_federated_search)
    monkeypatch.setattr("app.services.cache.cache.get", fake_cache_get)
    monkeypatch.setattr("app.services.cache.cache.set", fake_cache_set)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.cookies.set("csrf_token", "abc")
        ac.cookies.set("access_token", create_access_token(user_id))
        first = await ac.post(
            "/search/federated",
            json={"project_id": project_id, "query": "alpha beta", "max_results": 10},
            headers={"X-CSRF-Token": "abc"},
        )
        second = await ac.post(
            "/search/federated",
            json={"project_id": project_id, "query": "alpha beta", "max_results": 10},
            headers={"X-CSRF-Token": "abc"},
        )

    app.dependency_overrides = {}

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["partial_success"] is True
    assert first.json()["provider_status"]["europepmc"] == "error"
    assert "Europe PMC no respondió" in first.json()["warnings"]

    search_result_objects = [obj for obj in db.added if obj.__class__.__name__ == "SearchResult"]
    # Two searches should each persist their own two results.
    assert len(search_result_objects) == 4
