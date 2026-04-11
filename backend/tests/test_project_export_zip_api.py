from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token
from app.main import app


class FakeProject:
    def __init__(self, project_id: str, user_id: str):
        self.id = uuid.UUID(project_id)
        self.user_id = uuid.UUID(user_id)
        self.title = "X"
        self.description = None
        self.clinical_area = None
        self.archived = False
        self.created_at = None
        self.updated_at = None


class FakeRQJob:
    def __init__(self, id_: str):
        self.id = id_


class FakeQueue:
    def __init__(self):
        self.enqueued = []

    def enqueue(self, fn, args=None, job_timeout=None):
        self.enqueued.append({"fn": fn, "args": args or (), "job_timeout": job_timeout})
        return FakeRQJob("rq123")


class FakeSession:
    def __init__(self, *, user_id: str, project_id: str):
        self.user_id = uuid.UUID(user_id)
        self.project_id = uuid.UUID(project_id)
        self.added = []

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        return None

    async def refresh(self, obj):
        return None

    async def get(self, model, obj_id):
        # project lookup
        name = getattr(model, "__name__", "")
        if name == "Project":
            if uuid.UUID(str(obj_id)) != self.project_id:
                return None
            return FakeProject(str(self.project_id), str(self.user_id))

        # Job lookup (we won't need it here)
        return None

    async def execute(self, stmt):
        del stmt

        class _ScalarResult:
            def first(self):
                return None

            def all(self):
                return []

        class _Result:
            def scalars(self):
                return _ScalarResult()

            def all(self):
                return []

        return _Result()


@pytest.mark.asyncio
async def test_project_export_zip_enqueues_job(monkeypatch):
    from app.api import deps

    user_id = "00000000-0000-0000-0000-000000000000"
    project_id = "11111111-1111-1111-1111-111111111111"

    db = FakeSession(user_id=user_id, project_id=project_id)

    async def get_db_override():
        yield db

    class U:
        id = uuid.UUID(user_id)
        is_active = True

    async def fake_user(request=None, db=None):
        return U()

    q = FakeQueue()

    # patch queue getter used by endpoint
    import app.api.projects as projects_api

    monkeypatch.setattr(projects_api, "get_job_queue", lambda: q)

    app.dependency_overrides[deps.get_db] = get_db_override
    app.dependency_overrides[deps.get_current_user] = fake_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.cookies.set("csrf_token", "abc")
        ac.cookies.set("access_token", create_access_token(user_id))
        r = await ac.post(f"/projects/{project_id}/export-zip", headers={"X-CSRF-Token": "abc"})
        assert r.status_code == 200
        body = r.json()
        assert "job_id" in body
        assert len(q.enqueued) == 1

    app.dependency_overrides = {}
