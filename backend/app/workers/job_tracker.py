from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from rq import get_current_job

from app.database import async_session_maker
from app.services.jobs import queue_name_for_job_type
from app.core.metrics import job_failures_total
from app.models.job import Job


async def job_mark_started(job_id: UUID) -> None:
    async with async_session_maker() as db:
        job = await db.get(Job, job_id)
        if not job:
            return
        rq_job = get_current_job()
        job.status = "started"
        job.started_at = job.started_at or datetime.utcnow()
        job.progress_percent = job.progress_percent or 0
        job.queue_name = job.queue_name or (rq_job.origin if rq_job else queue_name_for_job_type(job.job_type))
        job.attempt = max(int(job.attempt or 0), 1)
        await db.commit()


async def job_set_progress(job_id: UUID, percent: int, status: str = "progress", result_patch: dict[str, Any] | None = None) -> None:
    percent = max(0, min(100, int(percent)))

    # Update RQ metadata (for polling without DB roundtrip)
    try:
        rq_job = get_current_job()
        if rq_job:
            rq_job.meta["progress_percent"] = percent
            rq_job.save_meta()
    except Exception:
        pass

    # Persist to DB
    async with async_session_maker() as db:
        job = await db.get(Job, job_id)
        if not job:
            return
        job.status = status
        job.progress_percent = percent
        job.started_at = job.started_at or datetime.utcnow()
        if result_patch:
            job.result = {**(job.result or {}), **result_patch}
        await db.commit()


async def job_mark_completed(job_id: UUID, result: dict[str, Any] | None = None) -> None:
    await job_set_progress(job_id, 100, status="completed", result_patch=result)
    async with async_session_maker() as db:
        job = await db.get(Job, job_id)
        if not job:
            return
        job.completed_at = job.completed_at or datetime.utcnow()
        await db.commit()


async def job_mark_failed(job_id: UUID, error_message: str) -> None:
    # Mark in RQ meta too
    try:
        rq_job = get_current_job()
        if rq_job:
            rq_job.meta["progress_percent"] = rq_job.meta.get("progress_percent", 0)
            rq_job.save_meta()
    except Exception:
        pass

    async with async_session_maker() as db:
        job = await db.get(Job, job_id)
        if not job:
            return
        job.status = "failed"
        job.error_message = error_message
        job.completed_at = job.completed_at or datetime.utcnow()
        job_failures_total.labels(queue=job.queue_name or queue_name_for_job_type(job.job_type)).inc()
        await db.commit()
