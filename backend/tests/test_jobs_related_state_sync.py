from __future__ import annotations

import uuid
from datetime import datetime

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.jobs import router as jobs_router


class FakeJob:
    def __init__(self, user_id: str, job_type: str, status: str, *, input_params=None, result=None):
        self.id = uuid.uuid4()
        self.user_id = uuid.UUID(user_id)
        self.job_type = job_type
        self.status = status
        self.queue_name = "analysis" if job_type == "analysis_run" else "documents"
        self.attempt = 0
        self.next_retry_at = None
        self.progress_percent = 0
        self.result = result or {}
        self.input_params = input_params or {}
        self.error_message = None
        self.created_at = datetime.utcnow()
        self.started_at = None
        self.completed_at = None


class FakeRun:
    def __init__(self, run_id: uuid.UUID):
        self.id = run_id
        self.status = "running"
        self.warnings = []
        self.result_summary = None


class FakeMetaItem:
    def __init__(self, item_id: uuid.UUID):
        self.id = item_id
        self.status = "failed"
        self.error_message = "old error"


class FakeMetaBatch:
    def __init__(self, batch_id: uuid.UUID):
        self.id = batch_id
        self.status = "processing"


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
    def __init__(self, jobs, runs=None, items=None, batches=None):
        self.jobs = {job.id: job for job in jobs}
        self.runs = runs or {}
        self.items = items or {}
        self.batches = batches or {}

    async def execute(self, stmt):
        return FakeResult(list(self.jobs.values()))

    async def get(self, model, obj_id):
        name = getattr(model, "__name__", "")
        if name == "Job":
            return self.jobs.get(obj_id)
        if name == "AnalysisRun":
            return self.runs.get(obj_id)
        if name == "MetaExtractionItem":
            return self.items.get(obj_id)
        if name == "MetaExtractionBatch":
            return self.batches.get(obj_id)
        return None

    async def commit(self):
        return None


def _test_app(db: FakeSession, *, user_id: str) -> FastAPI:
    from app.api import deps

    app = FastAPI()
    app.include_router(jobs_router)

    async def get_db_override():
        yield db

    class U:
        id = uuid.UUID(user_id)
        is_active = True

    async def fake_user(request=None, db=None):
        del request, db
        return U()

    app.dependency_overrides[deps.get_db] = get_db_override
    app.dependency_overrides[deps.get_current_user] = fake_user
    return app


@pytest.mark.asyncio
async def test_cancel_analysis_job_marks_run_cancelled(monkeypatch):
    user_id = "00000000-0000-0000-0000-000000000000"
    run_id = uuid.uuid4()
    job = FakeJob(user_id, "analysis_run", "started", input_params={"analysis_run_id": str(run_id)})
    run = FakeRun(run_id)
    db = FakeSession([job], runs={run_id: run})
    app = _test_app(db, user_id=user_id)

    monkeypatch.setattr("app.api.jobs.redis_available", lambda: False)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.cookies.set("csrf_token", "abc")
        ac.cookies.set("access_token", "x")
        response = await ac.post(f"/jobs/{job.id}/cancel", headers={"X-CSRF-Token": "abc"})
        assert response.status_code == 200

    assert run.status == "cancelled"
    assert "Cancelled by user" in run.warnings


@pytest.mark.asyncio
async def test_retry_analysis_job_requeues_run(monkeypatch):
    user_id = "00000000-0000-0000-0000-000000000000"
    run_id = uuid.uuid4()
    job = FakeJob(user_id, "analysis_run", "failed", input_params={"analysis_run_id": str(run_id)})
    run = FakeRun(run_id)
    run.status = "failed"
    db = FakeSession([job], runs={run_id: run})
    app = _test_app(db, user_id=user_id)

    monkeypatch.setattr("app.api.jobs.redis_available", lambda: True)
    monkeypatch.setattr("app.api.jobs.retry_job_record", lambda current_job: "rq-analysis-retry")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.cookies.set("csrf_token", "abc")
        ac.cookies.set("access_token", "x")
        response = await ac.post(f"/jobs/{job.id}/retry", headers={"X-CSRF-Token": "abc"})
        assert response.status_code == 200

    assert run.status == "queued"


@pytest.mark.asyncio
async def test_retry_meta_item_job_requeues_item(monkeypatch):
    user_id = "00000000-0000-0000-0000-000000000000"
    item_id = uuid.uuid4()
    job = FakeJob(
        user_id,
        "meta_extract_paper",
        "failed",
        input_params={"item_id": str(item_id), "batch_id": str(uuid.uuid4()), "paper_id": str(uuid.uuid4())},
    )
    item = FakeMetaItem(item_id)
    db = FakeSession([job], items={item_id: item})
    app = _test_app(db, user_id=user_id)

    monkeypatch.setattr("app.api.jobs.redis_available", lambda: True)
    monkeypatch.setattr("app.api.jobs.retry_job_record", lambda current_job: "rq-meta-retry")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.cookies.set("csrf_token", "abc")
        ac.cookies.set("access_token", "x")
        response = await ac.post(f"/jobs/{job.id}/retry", headers={"X-CSRF-Token": "abc"})
        assert response.status_code == 200

    assert item.status == "queued"
    assert item.error_message is None


@pytest.mark.asyncio
async def test_get_job_returns_persisted_active_state_when_redis_is_down(monkeypatch):
    user_id = "00000000-0000-0000-0000-000000000000"
    job = FakeJob(user_id, "analysis_run", "started")
    job.progress_percent = 45
    db = FakeSession([job])
    app = _test_app(db, user_id=user_id)

    monkeypatch.setattr("app.api.jobs.redis_available", lambda: False)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.cookies.set("csrf_token", "abc")
        ac.cookies.set("access_token", "x")
        response = await ac.get(f"/jobs/{job.id}", headers={"X-CSRF-Token": "abc"})
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "started"
        assert payload["progress_percent"] == 45


@pytest.mark.asyncio
async def test_missing_rq_record_marks_analysis_run_failed(monkeypatch):
    user_id = "00000000-0000-0000-0000-000000000000"
    run_id = uuid.uuid4()
    job = FakeJob(user_id, "analysis_run", "started", input_params={"analysis_run_id": str(run_id)}, result={"rq_job_id": "rq-missing"})
    run = FakeRun(run_id)
    db = FakeSession([job], runs={run_id: run})
    app = _test_app(db, user_id=user_id)

    monkeypatch.setattr("app.api.jobs.redis_available", lambda: True)
    monkeypatch.setattr("app.api.jobs.get_redis", lambda: object())

    class MissingRQJob:
        @staticmethod
        def fetch(job_id, connection=None):
            del job_id, connection
            raise RuntimeError("missing")

    monkeypatch.setattr("app.api.jobs.RQJob", MissingRQJob)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.cookies.set("csrf_token", "abc")
        ac.cookies.set("access_token", "x")
        response = await ac.get(f"/jobs/{job.id}", headers={"X-CSRF-Token": "abc"})
        assert response.status_code == 200

    assert run.status == "failed"
    assert "RQ job no encontrado en Redis" in run.warnings
