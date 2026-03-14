from __future__ import annotations

import uuid
from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.meta import router as meta_router
from app.services.meta_extractor.export_service import create_meta_export


class _FakeScalar:
    def __init__(self, items):
        self._items = items

    def all(self):
        return self._items

    def first(self):
        return self._items[0] if self._items else None


class _FakeExecuteResult:
    def __init__(self, items):
        self._items = items

    def scalars(self):
        return _FakeScalar(self._items)

    def all(self):
        return self._items


class _MetaSession:
    def __init__(self, *, batches=None):
        self.batches = batches or []
        self.added = []

    async def execute(self, stmt):
        stmt_text = str(stmt)
        if "meta_extraction_batches" in stmt_text:
            return _FakeExecuteResult(self.batches)
        return _FakeExecuteResult([])

    async def get(self, model, obj_id):
        name = getattr(model, "__name__", "")
        if name == "MetaExport":
            return None
        for batch in self.batches:
            if getattr(batch, "id", None) == obj_id:
                return batch
        return None

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        return None

    async def refresh(self, obj):
        return None


def _meta_app(db: _MetaSession, *, user_id: uuid.UUID) -> FastAPI:
    from app.api import deps

    app = FastAPI()
    app.include_router(meta_router)

    async def get_db_override():
        yield db

    class U:
        id = user_id
        is_active = True

    async def fake_user(request=None, db=None):
        del request, db
        return U()

    app.dependency_overrides[deps.get_db] = get_db_override
    app.dependency_overrides[deps.get_current_user] = fake_user
    return app


@pytest.mark.asyncio
async def test_meta_batches_list_uses_project_rbac(monkeypatch):
    user_id = uuid.uuid4()
    project_id = uuid.uuid4()
    batch = SimpleNamespace(id=uuid.uuid4(), title="Batch", status="created", created_at=datetime.utcnow(), project_id=project_id)
    db = _MetaSession(batches=[batch])
    app = _meta_app(db, user_id=user_id)

    async def allow_access(db, *, project_id, user, required_role="viewer"):
        del db, user, required_role
        return SimpleNamespace(id=project_id, user_id=uuid.uuid4()), SimpleNamespace(role="reviewer")

    monkeypatch.setattr("app.api.meta.require_project_access", allow_access)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.cookies.set("csrf_token", "abc")
        ac.cookies.set("access_token", "x")
        response = await ac.get(f"/meta/batches?project_id={project_id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == str(batch.id)


@pytest.mark.asyncio
async def test_meta_export_endpoint_allows_editor(monkeypatch):
    user_id = uuid.uuid4()
    project_id = uuid.uuid4()
    db = _MetaSession()
    app = _meta_app(db, user_id=user_id)

    async def allow_access(db, *, project_id, user, required_role="viewer"):
        del db, user
        assert required_role == "editor"
        return SimpleNamespace(id=project_id, user_id=uuid.uuid4()), SimpleNamespace(role="editor")

    class _FakeQueue:
        def enqueue(self, *args, **kwargs):
            del args, kwargs
            return SimpleNamespace(id="rq-meta-export")

    monkeypatch.setattr("app.api.meta.require_project_access", allow_access)
    monkeypatch.setattr("app.api.meta.get_job_queue", lambda name="documents": _FakeQueue())

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.cookies.set("csrf_token", "abc")
        ac.cookies.set("access_token", "x")
        response = await ac.post("/meta/export", json={"project_id": str(project_id)}, headers={"X-CSRF-Token": "abc"})
        assert response.status_code == 200
        assert response.json()["job_id"]


class _ExportSession:
    async def execute(self, stmt):
        return _FakeExecuteResult([])

    def add(self, obj):
        del obj

    async def commit(self):
        return None

    async def refresh(self, obj):
        return None


@pytest.mark.asyncio
async def test_create_meta_export_requires_extracted_studies():
    db = _ExportSession()
    with pytest.raises(ValueError, match="No extracted studies available for export"):
        await create_meta_export(db=db, project_id=uuid.uuid4(), batch_id=None)
