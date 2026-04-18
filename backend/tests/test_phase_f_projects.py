from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


class FakeProject:
    def __init__(self, user_id: str, title: str):
        self.id = uuid.uuid4()
        self.user_id = uuid.UUID(user_id)
        self.title = title
        self.description = None
        self.clinical_area = None
        self.archived = False
        self.created_at = None


class FakeScalar:
    def __init__(self, items):
        self._items = items

    def all(self):
        return self._items


class FakeResult:
    def __init__(self, items):
        self._items = items

    def scalars(self):
        return FakeScalar(self._items)

    def all(self):
        return list(self._items)


class FakeSession:
    def __init__(self, user_id: str):
        self.user_id = uuid.UUID(user_id)
        self.projects: list[FakeProject] = []

    def add(self, obj):
        # obj is a real Project model; mimic by copying fields we assert on
        p = FakeProject(str(obj.user_id), obj.title)
        p.description = obj.description
        p.clinical_area = obj.clinical_area
        p.archived = obj.archived
        self.projects.append(p)
        obj.id = p.id
        obj.created_at = None

    async def commit(self):
        return None

    async def refresh(self, obj):
        return None

    async def execute(self, stmt):
        sql = str(stmt)
        if "JOIN project_memberships" in sql and "FROM projects" in sql:
            return FakeResult([(p, None) for p in self.projects if p.user_id == self.user_id])

        # Support union_all used for optimizing dashboard queries
        if "UNION ALL" in sql or "UNION" in sql:
            return FakeResult([
                ("papers", 10),
                ("notes", 5),
                ("meta_studies_current", 2),
                ("references", 8),
            ])

        return FakeResult([p for p in self.projects if p.user_id == self.user_id])

    async def get(self, model, obj_id):
        return None


@pytest.mark.asyncio
async def test_create_and_list_projects(monkeypatch):
    from app.api import deps

    user_id = "00000000-0000-0000-0000-000000000000"
    db = FakeSession(user_id)

    async def get_db_override():
        yield db

    class U:
        id = uuid.UUID(user_id)
        is_active = True

    async def fake_user(request=None, db=None):
        return U()

    app.dependency_overrides[deps.get_db] = get_db_override
    app.dependency_overrides[deps.get_current_user] = fake_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.cookies.set("csrf_token", "abc")
        ac.cookies.set("access_token", "x")

        r1 = await ac.post(
            "/projects",
            json={"title": "Orto", "description": None, "clinical_area": None},
            headers={"X-CSRF-Token": "abc"},
        )
        assert r1.status_code == 200

        r2 = await ac.get("/projects")
        assert r2.status_code == 200
        items = r2.json()
        assert len(items) == 1
        assert items[0]["title"] == "Orto"

    app.dependency_overrides = {}
