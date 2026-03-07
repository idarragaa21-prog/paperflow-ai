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

    async def get(self, model, obj_id):
        # get_current_user loads User; endpoint loads Project
        name = getattr(model, "__name__", "")
        if name == "User":
            return self._user
        if name == "Project":
            return self._project
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

    async def fake_search_and_fetch(query: str, max_results: int = 20):
        raise AssertionError("pubmed_client should not be called on cache hit")

    from app.api import deps
    from app.core.security import create_access_token

    user_id = "00000000-0000-0000-0000-000000000000"
    project_id = "00000000-0000-0000-0000-000000000000"

    monkeypatch.setattr("app.services.cache.cache.get", fake_get)
    monkeypatch.setattr("app.services.pubmed.pubmed_client.search_and_fetch", fake_search_and_fetch)

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
