from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


class DummyRQJob:
    def __init__(self, jid: str):
        self.id = jid


class DummyQueue:
    def __init__(self):
        self.enqueued = []

    def enqueue(self, func, args=(), job_timeout=None):
        # record for assertions
        self.enqueued.append({"func": getattr(func, "__name__", str(func)), "args": args, "timeout": job_timeout})
        return DummyRQJob(jid=str(uuid.uuid4()))


class FakeSession:
    def __init__(self, user_id: uuid.UUID):
        self.user_id = user_id
        self._sheets = {}
        self._jobs = {}

    def add(self, obj):
        # ClinicalSheet / Job instances
        if getattr(obj, "__tablename__", None) == "clinical_sheets":
            self._sheets[obj.id] = obj
        if getattr(obj, "__tablename__", None) == "jobs":
            self._jobs[obj.id] = obj

    async def commit(self):
        return None

    async def refresh(self, obj):
        return None

    async def get(self, model, obj_id):
        # Only used by endpoints here
        name = getattr(model, "__tablename__", "")
        if name == "clinical_sheets":
            return self._sheets.get(obj_id)
        if name == "projects":
            return None
        return None

    async def execute(self, stmt):
        # Not needed for these tests
        raise AssertionError("execute() should not be called in this test")


@pytest.mark.asyncio
async def test_clinical_sheet_update_versioning(monkeypatch):
    from app.api import deps
    from app.api import clinical as clinical_api

    user_id = uuid.uuid4()

    # Build an initial sheet owned by the user
    from app.models.clinical import ClinicalSheet

    s1 = ClinicalSheet(
        id=uuid.uuid4(),
        project_id=None,
        user_id=user_id,
        topic="T",
        input_params={"root_id": "ROOT", "status": "completed"},
        content_markdown="X",
        references_json=None,
        sources_used=None,
        version=1,
        is_current=True,
        llm_model=None,
        llm_usage=None,
        created_at=None,
        updated_at=None,
    )

    db = FakeSession(user_id)
    db._sheets[s1.id] = s1

    async def get_db_override():
        yield db

    class U:
        id = user_id
        is_active = True

    async def fake_user(request=None, db=None):
        return U()

    q = DummyQueue()
    monkeypatch.setattr(clinical_api, "get_job_queue", lambda: q)

    app.dependency_overrides[deps.get_db] = get_db_override
    app.dependency_overrides[deps.get_current_user] = fake_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.cookies.set("csrf_token", "abc")
        ac.cookies.set("access_token", "x")
        r = await ac.post(
            f"/clinical/sheets/{s1.id}/update",
            json={"context": "x", "objective": "diagnostic"},
            headers={"X-CSRF-Token": "abc"},
        )
        assert r.status_code == 200

    # previous sheet no longer current
    assert db._sheets[s1.id].is_current is False

    # find new sheet
    new_sheets = [s for sid, s in db._sheets.items() if sid != s1.id]
    assert len(new_sheets) == 1
    s2 = new_sheets[0]
    assert s2.version == 2
    assert s2.is_current is True

    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_clinical_sheet_ownership(monkeypatch):
    from app.api import deps

    owner_id = uuid.uuid4()
    other_id = uuid.uuid4()

    from app.models.clinical import ClinicalSheet

    s1 = ClinicalSheet(
        id=uuid.uuid4(),
        project_id=None,
        user_id=owner_id,
        topic="T",
        input_params={"status": "completed"},
        content_markdown="X",
        references_json=None,
        sources_used=None,
        version=1,
        is_current=True,
        llm_model=None,
        llm_usage=None,
        created_at=None,
        updated_at=None,
    )

    db = FakeSession(owner_id)
    db._sheets[s1.id] = s1

    async def get_db_override():
        yield db

    class U:
        id = other_id
        is_active = True

    async def fake_user(request=None, db=None):
        return U()

    app.dependency_overrides[deps.get_db] = get_db_override
    app.dependency_overrides[deps.get_current_user] = fake_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.cookies.set("access_token", "x")
        r = await ac.get(f"/clinical/sheets/{s1.id}")
        assert r.status_code == 404

    app.dependency_overrides = {}
