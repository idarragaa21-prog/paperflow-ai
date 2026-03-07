from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token
from app.main import app


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
    def __init__(self, user_id: str):
        self.user_id = uuid.UUID(user_id)
        self._objs = {}

    def add(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()
        self._objs[(obj.__class__.__name__, str(obj.id))] = obj

    async def commit(self):
        return None

    async def refresh(self, obj):
        return None

    async def get(self, model, obj_id):
        key = (getattr(model, "__name__", str(model)), str(obj_id))
        return self._objs.get(key)

    async def execute(self, stmt):
        raise AssertionError("execute not used")


@pytest.mark.asyncio
async def test_books_scan_folder_enqueues_job(monkeypatch):
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

    q = FakeQueue()

    import app.api.books as books_api

    monkeypatch.setattr(books_api, "get_job_queue", lambda: q)

    app.dependency_overrides[deps.get_db] = get_db_override
    app.dependency_overrides[deps.get_current_user] = fake_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.cookies.set("csrf_token", "abc")
        ac.cookies.set("access_token", create_access_token(user_id))

        r = await ac.post("/books/scan-folder", headers={"X-CSRF-Token": "abc"})
        assert r.status_code == 200
        assert "job_id" in r.json()
        assert len(q.enqueued) == 1

    app.dependency_overrides = {}
