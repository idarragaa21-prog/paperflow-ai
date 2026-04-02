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
    from app.workers.tasks import PresentationJobParams, generate_presentation_job

    job_queue = get_job_queue()
    job_params = PresentationJobParams(
        job_db_id=str(job_db_id),
        project_id=str(params.project_id),
        topic=params.topic,
        duration=params.duration_minutes,
        audience=params.audience,
        paper_ids=[str(pid) for pid in params.paper_ids],
        num_slides=int(params.num_slides),
    )
    job = job_queue.enqueue(
        generate_presentation_job,
        args=(job_params,),
        job_timeout="10m",
    )
    return job.id
