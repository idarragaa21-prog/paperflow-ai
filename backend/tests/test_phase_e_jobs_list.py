from __future__ import annotations

import uuid
from datetime import datetime

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


class FakeJob:
    def __init__(self, user_id: str, job_type: str, status: str):
        self.id = uuid.uuid4()
        self.user_id = uuid.UUID(user_id)
        self.job_type = job_type
        self.status = status
        self.progress_percent = 0
        self.result = {}
        self.error_message = None
        self.created_at = datetime.utcnow()
        self.started_at = None
        self.completed_at = None


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


class FakeSession:
    def __init__(self, items):
        self.items = items

    async def execute(self, stmt):
        # Return all; endpoint filters already in stmt, but for test we keep simple.
        return FakeResult(self.items)

    async def get(self, model, obj_id):
        return None


@pytest.mark.asyncio
async def test_jobs_list_filters_by_user(monkeypatch):
    from app.api import deps

    user1 = "00000000-0000-0000-0000-000000000000"
    user2 = "11111111-1111-1111-1111-111111111111"

    jobs = [FakeJob(user1, "process_pdf", "queued"), FakeJob(user2, "process_pdf", "queued")]
    db = FakeSession(jobs)

    async def get_db_override():
        yield db

    class U:
        id = uuid.UUID(user1)
        is_active = True

    async def fake_user(request=None, db=None):
        return U()

    app.dependency_overrides[deps.get_db] = get_db_override
    app.dependency_overrides[deps.get_current_user] = fake_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.cookies.set("csrf_token", "abc")
        ac.cookies.set("access_token", "x")
        r = await ac.get("/jobs?limit=50&offset=0", headers={"X-CSRF-Token": "abc"})
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) == 1

    app.dependency_overrides = {}
