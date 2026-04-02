from __future__ import annotations

from uuid import UUID

from redis.exceptions import RedisError
from rq import Queue

from app.core.redis_conn import get_redis, redis_available
from app.schemas.presentation import CreatePresentationRequest


def get_job_queue() -> Queue:
    if not redis_available():
        raise RedisError("Redis no disponible")
    return Queue("research_console", connection=get_redis())


def enqueue_process_pdf(job_db_id: UUID, paper_id: UUID) -> str:
    from app.workers.tasks import process_pdf_job

    job_queue = get_job_queue()
    job = job_queue.enqueue(
        process_pdf_job,
        args=(str(job_db_id), str(paper_id)),
        job_timeout="5m",
    )
    return job.id


def enqueue_presentation(
    job_db_id: UUID,
    params: CreatePresentationRequest,
) -> str:
    from app.workers.tasks import generate_presentation_job

    job_queue = get_job_queue()
    job = job_queue.enqueue(
        generate_presentation_job,
        args=(
            str(job_db_id),
            str(params.project_id),
            params.topic,
            params.duration_minutes,
            params.audience,
            [str(pid) for pid in params.paper_ids],
            int(params.num_slides),
        ),
        job_timeout="10m",
    )
    return job.id
