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

    async def delete(self, obj):
        self._objs.pop((obj.__class__.__name__, str(obj.id)), None)


@pytest.mark.asyncio
async def test_clinical_query_creates_job_and_sheet(monkeypatch, tmp_path):
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

    import app.api.clinical as clinical_api

    monkeypatch.setattr(clinical_api, "get_job_queue", lambda: q)

    app.dependency_overrides[deps.get_db] = get_db_override
    app.dependency_overrides[deps.get_current_user] = fake_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.cookies.set("csrf_token", "abc")
        ac.cookies.set("access_token", create_access_token(user_id))

        r = await ac.post(
            "/clinical/query",
            json={"topic": "Tendinopatía rotuliana", "project_id": None, "search_online": True, "use_project_papers": False},
            headers={"X-CSRF-Token": "abc"},
        )
        assert r.status_code == 200
        body = r.json()
        assert "job_id" in body
        assert "sheet_id" in body
        assert len(q.enqueued) == 1

        sid = body["sheet_id"]
        r2 = await ac.get(f"/clinical/{sid}", headers={"X-CSRF-Token": "abc"})
        assert r2.status_code == 200
        assert r2.json()["id"] == sid

    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_clinical_download_uses_cached_export(monkeypatch, tmp_path):
    from app.api import deps
    from app.models.clinical import ClinicalSheet

    user_id = "00000000-0000-0000-0000-000000000000"
    db = FakeSession(user_id)

    async def get_db_override():
        yield db

    class U:
        id = uuid.UUID(user_id)
        is_active = True

    async def fake_user(request=None, db=None):
        return U()

    # Patch storage base_dir
    from app.core.storage import storage_manager

    monkeypatch.setattr(storage_manager, "base_dir", tmp_path)

    # Create a fake export file
    rel = "clinical_exports/x.pdf"
    abs_path = tmp_path / rel
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_bytes(b"%PDF-1.4\n%%EOF")

    s = ClinicalSheet(
        user_id=uuid.UUID(user_id),
        project_id=None,
        topic="X",
        input_params={},
        content_markdown="## Resumen ejecutivo\nFuentes: (No encontrado / evidencia insuficiente)",
        references_json=None,
        sources_used={"exports": {"pdf": rel}},
        version=1,
        is_current=True,
        llm_model=None,
        llm_usage=None,
    )
    db.add(s)

    app.dependency_overrides[deps.get_db] = get_db_override
    app.dependency_overrides[deps.get_current_user] = fake_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.cookies.set("csrf_token", "abc")
        ac.cookies.set("access_token", create_access_token(user_id))

        r = await ac.get(f"/clinical/{s.id}/download?format=pdf", headers={"X-CSRF-Token": "abc"})
        assert r.status_code == 200

    app.dependency_overrides = {}
