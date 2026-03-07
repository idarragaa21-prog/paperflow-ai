from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from redis.exceptions import RedisError
from rq import Queue, Retry
from rq.job import Job as RQJob
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.metrics import job_failures_total, job_retries_total
from app.core.redis_conn import get_redis, redis_available
from app.models.job import Job

QUEUE_BY_JOB_TYPE = {
    "process_pdf": "documents",
    "batch_download_papers": "documents",
    "summarize_paper": "documents",
    "project_export_zip": "documents",
    "meta_extract_batch": "documents",
    "meta_extract_paper": "documents",
    "meta_export_excel": "documents",
    "books_index": "documents",
    "books_scan_folder": "documents",
    "analysis_run": "analysis",
    "generate_presentation": "presentations",
    "clinical_query": "presentations",
}

DEFAULT_RETRY = Retry(max=3, interval=[60, 300, 1800])


def queue_name_for_job_type(job_type: str) -> str:
    return QUEUE_BY_JOB_TYPE.get(job_type, "documents")


def get_job_queue(queue_name: str = "documents") -> Queue:
    if not redis_available():
        raise RedisError("Redis no disponible")
    return Queue(queue_name, connection=get_redis())


def enqueue_with_retry(
    queue_name: str,
    func,
    *,
    args: tuple[Any, ...],
    job_timeout: str,
) -> str:
    job_queue = get_job_queue(queue_name)
    job = job_queue.enqueue(func, args=args, job_timeout=job_timeout, retry=DEFAULT_RETRY)
    return job.id


def enqueue_process_pdf(job_db_id: UUID, paper_id: UUID) -> str:
    from app.workers.tasks import process_pdf_job

    return enqueue_with_retry("documents", process_pdf_job, args=(str(job_db_id), str(paper_id)), job_timeout="5m")


def enqueue_presentation(
    job_db_id: UUID,
    project_id: UUID,
    topic: str,
    duration: int,
    audience: str,
    paper_ids: list[UUID],
    num_slides: int,
) -> str:
    from app.workers.tasks import generate_presentation_job

    return enqueue_with_retry(
        "presentations",
        generate_presentation_job,
        args=(str(job_db_id), str(project_id), topic, duration, audience, [str(pid) for pid in paper_ids], int(num_slides)),
        job_timeout="10m",
    )


def _job_callable_and_args(job: Job):
    params = job.input_params or {}
    job_id = str(job.id)
    job_type = job.job_type

    if job_type == "process_pdf":
        from app.workers.tasks import process_pdf_job

        return process_pdf_job, (job_id, params["paper_id"])
    if job_type == "batch_download_papers":
        from app.workers.tasks import batch_download_papers_job

        return batch_download_papers_job, (job_id, params["project_id"], params.get("papers", []))
    if job_type == "summarize_paper":
        from app.workers.tasks import summarize_paper_job

        return summarize_paper_job, (job_id, params["paper_id"], params.get("custom_instructions"))
    if job_type == "project_export_zip":
        from app.workers.tasks import export_project_zip_job

        return export_project_zip_job, (job_id, params["project_id"])
    if job_type == "generate_presentation":
        from app.workers.tasks import generate_presentation_job

        return generate_presentation_job, (
            job_id,
            params["project_id"],
            params["topic"],
            params["duration_minutes"],
            params["audience"],
            params.get("paper_ids", []),
            params.get("num_slides", 0),
        )
    if job_type == "meta_extract_batch":
        from app.workers.tasks import meta_extract_batch_job

        return meta_extract_batch_job, (job_id, params["batch_id"])
    if job_type == "meta_extract_paper":
        from app.workers.tasks import meta_extract_paper_job

        return meta_extract_paper_job, (job_id, params["batch_id"], params["item_id"], params["paper_id"])
    if job_type == "meta_export_excel":
        from app.workers.tasks import meta_export_excel_job

        return meta_export_excel_job, (job_id, params["project_id"], params.get("batch_id", ""))
    if job_type == "clinical_query":
        from app.workers.tasks import clinical_query_job

        return clinical_query_job, (job_id, params["sheet_id"])
    if job_type == "books_index":
        from app.workers.tasks import books_index_job

        return books_index_job, (job_id, params["book_id"])
    if job_type == "books_scan_folder":
        from app.workers.books_scan_folder_job import books_scan_folder_job

        return books_scan_folder_job, (job_id,)
    if job_type == "analysis_run":
        from app.workers.tasks import analysis_run_job

        return analysis_run_job, (job_id, params["analysis_run_id"])
    raise ValueError(f"Unsupported retry for job_type={job_type}")


def retry_job_record(job: Job) -> str:
    func, args = _job_callable_and_args(job)
    queue_name = job.queue_name or queue_name_for_job_type(job.job_type)
    job.attempt = int(job.attempt or 0) + 1
    job.status = "queued"
    job.error_message = None
    job.completed_at = None
    job.next_retry_at = None
    rq_job_id = enqueue_with_retry(queue_name, func, args=args, job_timeout="60m")
    job.result = {**(job.result or {}), "rq_job_id": rq_job_id}
    job.queue_name = queue_name
    job_retries_total.labels(queue=queue_name).inc()
    return rq_job_id


async def reconcile_stale_jobs(db: AsyncSession) -> int:
    if not redis_available():
        return 0

    q = await db.execute(select(Job).where(Job.status.in_(["queued", "started", "progress", "retry_pending"])))
    items = q.scalars().all()
    reconciled = 0
    redis = get_redis()
    for item in items:
        rq_job_id = (item.result or {}).get("rq_job_id")
        if not rq_job_id:
            if item.status != "failed":
                item.status = "failed"
                item.error_message = "RQ job missing"
                item.completed_at = item.completed_at or datetime.now(timezone.utc)
                job_failures_total.labels(queue=item.queue_name or queue_name_for_job_type(item.job_type)).inc()
                reconciled += 1
            continue
        try:
            RQJob.fetch(rq_job_id, connection=redis)
        except Exception:
            item.status = "retry_pending" if int(item.attempt or 0) < 3 else "failed"
            item.error_message = "RQ job not found during reconciliation"
            item.next_retry_at = datetime.now(timezone.utc) if item.status == "retry_pending" else None
            if item.status == "failed":
                item.completed_at = item.completed_at or datetime.now(timezone.utc)
                job_failures_total.labels(queue=item.queue_name or queue_name_for_job_type(item.job_type)).inc()
            reconciled += 1
    if reconciled:
        await db.commit()
    return reconciled
