from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.workers import job_tracker


class _FakeDB:
    def __init__(self, job):
        self.job = job
        self.commits = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, model, obj_id):
        del model, obj_id
        return self.job

    async def commit(self):
        self.commits += 1


@pytest.mark.asyncio
async def test_cancelled_job_is_not_overwritten_by_started(monkeypatch):
    job = SimpleNamespace(
        id=uuid4(),
        status="cancelled",
        started_at=None,
        progress_percent=0,
        queue_name="documents",
        job_type="process_pdf",
        attempt=1,
    )
    fake_db = _FakeDB(job)

    monkeypatch.setattr(job_tracker, "async_session_maker", lambda: fake_db)
    monkeypatch.setattr(job_tracker, "get_current_job", lambda: None)

    await job_tracker.job_mark_started(job.id)

    assert job.status == "cancelled"
    assert fake_db.commits == 0


@pytest.mark.asyncio
async def test_cancelled_job_is_not_overwritten_by_progress_or_completion(monkeypatch):
    job = SimpleNamespace(
        id=uuid4(),
        status="cancelled",
        started_at=datetime.utcnow(),
        progress_percent=10,
        queue_name="documents",
        job_type="process_pdf",
        attempt=1,
        result={},
        completed_at=None,
    )
    fake_db = _FakeDB(job)

    monkeypatch.setattr(job_tracker, "async_session_maker", lambda: fake_db)
    monkeypatch.setattr(job_tracker, "get_current_job", lambda: None)

    await job_tracker.job_set_progress(job.id, 80, status="progress", result_patch={"step": "late"})
    await job_tracker.job_mark_completed(job.id, result={"done": True})

    assert job.status == "cancelled"
    assert job.progress_percent == 10
    assert job.result == {}
    assert job.completed_at is None


@pytest.mark.asyncio
async def test_completed_job_is_not_reopened_as_failed(monkeypatch):
    job = SimpleNamespace(
        id=uuid4(),
        status="completed",
        started_at=datetime.utcnow(),
        progress_percent=100,
        queue_name="documents",
        job_type="process_pdf",
        attempt=1,
        error_message=None,
        completed_at=datetime.utcnow(),
    )
    fake_db = _FakeDB(job)

    monkeypatch.setattr(job_tracker, "async_session_maker", lambda: fake_db)
    monkeypatch.setattr(job_tracker, "get_current_job", lambda: None)

    await job_tracker.job_mark_failed(job.id, "late worker failure")

    assert job.status == "completed"
    assert job.error_message is None
    assert fake_db.commits == 0
