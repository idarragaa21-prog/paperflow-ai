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


class FailingFakeQueue(FakeQueue):
    def enqueue(self, fn, args=None, job_timeout=None):
        raise Exception("Job queue unavailable")


class FailingDBSession(FakeSession):
    async def execute(self, stmt):
        raise Exception("Database query failed")


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


@pytest.mark.asyncio
async def test_index_book_enqueue_fails(monkeypatch):
    from app.api import deps
    import app.api.books as books_api
    from app.core.storage import storage_manager

    user_id = "00000000-0000-0000-0000-000000000000"
    db = FakeSession(user_id)

    async def get_db_override():
        yield db

    class U:
        id = uuid.UUID(user_id)
        is_active = True

    async def fake_user(request=None, db=None):
        return U()

    q = FailingFakeQueue()

    monkeypatch.setattr(books_api, "get_job_queue", lambda: q)
    monkeypatch.setattr(storage_manager, "validate_pdf", lambda content: True)
    monkeypatch.setattr(storage_manager, "_sanitize_filename", lambda fn: "dummy.pdf")
    # Stub writing to the file system
    monkeypatch.setattr("app.core.storage.StorageManager._sanitize_path", lambda self, path: type("DummyPath", (), {"write_bytes": lambda self, b: None})())

    app.dependency_overrides[deps.get_db] = get_db_override
    app.dependency_overrides[deps.get_current_user] = fake_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.cookies.set("csrf_token", "abc")
        ac.cookies.set("access_token", create_access_token(user_id))

        files = {"file": ("dummy.pdf", b"dummy content", "application/pdf")}
        r = await ac.post("/books/index", headers={"X-CSRF-Token": "abc"}, files=files)

        # Line 73 of books.py handles enqueue error and raises 503
        assert r.status_code == 503
        assert "Job queue unavailable" in r.json()["detail"]

    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_list_books_db_failure():
    from app.api import deps

    user_id = "00000000-0000-0000-0000-000000000000"
    db = FailingDBSession(user_id)

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
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ac.cookies.set("csrf_token", "abc")
            ac.cookies.set("access_token", create_access_token(user_id))

            r = await ac.get("/books", headers={"X-CSRF-Token": "abc"})
            assert r.status_code == 500
            assert "Failed to fetch books" in r.json()["detail"]
    finally:
        app.dependency_overrides.clear()
