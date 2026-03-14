from datetime import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from redis.exceptions import RedisError
from rq.job import Job as RQJob
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.redis_conn import get_redis, redis_available
from app.middleware.rate_limit import limiter
from app.models.analytics import AnalysisRun
from app.models.job import Job
from app.models.meta_extractor import MetaExtractionBatch, MetaExtractionItem
from app.models.user import User
from app.services.jobs import retry_job_record

router = APIRouter(prefix="/jobs", tags=["jobs"])

TERMINAL_JOB_STATUSES = {"completed", "failed", "cancelled"}
ANALYSIS_RUN_TERMINAL_STATUSES = {"completed", "failed", "cancelled"}


def _serialize_job(job: Job) -> dict:
    return {
        "id": str(job.id),
        "status": job.status,
        "progress_percent": job.progress_percent or 0,
        "queue_name": job.queue_name,
        "attempt": job.attempt,
        "next_retry_at": job.next_retry_at.isoformat() if job.next_retry_at else None,
        "result": job.result,
        "error": job.error_message,
    }


def _job_related_uuid(job: Job, *keys: str) -> uuid.UUID | None:
    params = getattr(job, "input_params", None) or {}
    result = getattr(job, "result", None) or {}
    for key in keys:
        raw_value = params.get(key, result.get(key))
        if not raw_value:
            continue
        try:
            return uuid.UUID(str(raw_value))
        except (TypeError, ValueError):
            continue
    return None


async def _sync_analysis_run_for_job(
    db: AsyncSession,
    *,
    job: Job,
    status: str,
    message: str | None = None,
) -> None:
    if job.job_type != "analysis_run":
        return
    run_id = _job_related_uuid(job, "analysis_run_id")
    if run_id is None:
        return
    run = await db.get(AnalysisRun, run_id)
    if run is None:
        return

    if status == "queued":
        run.status = "queued"
        return
    if status in {"started", "progress"}:
        if run.status not in ANALYSIS_RUN_TERMINAL_STATUSES:
            run.status = "running"
        return
    if status == "retry_pending":
        if run.status not in ANALYSIS_RUN_TERMINAL_STATUSES:
            run.status = "retry_pending"
        return
    if status == "failed":
        if run.status == "completed":
            return
        run.status = "failed"
    elif status == "cancelled":
        if run.status == "completed":
            return
        run.status = "cancelled"
    else:
        return

    if message:
        warnings = list(run.warnings or [])
        if message not in warnings:
            warnings.append(message)
        run.warnings = warnings
        if run.result_summary is None:
            run.result_summary = {"error": message}


async def _sync_meta_item_for_job(
    db: AsyncSession,
    *,
    job: Job,
    status: str,
    message: str | None = None,
) -> None:
    if job.job_type != "meta_extract_paper":
        return
    item_id = _job_related_uuid(job, "item_id")
    if item_id is None:
        return
    item = await db.get(MetaExtractionItem, item_id)
    if item is None:
        return

    if status == "queued":
        item.status = "queued"
        item.error_message = None
        return
    if status in {"started", "progress"}:
        if item.status != "completed":
            item.status = "started"
        return
    if status == "failed":
        if item.status != "completed":
            item.status = "failed"
            item.error_message = message or item.error_message
        return
    if status == "cancelled":
        if item.status != "completed":
            item.status = "failed"
            item.error_message = message or "Cancelled by user"


async def _sync_meta_batch_for_job(
    db: AsyncSession,
    *,
    job: Job,
    status: str,
) -> None:
    if job.job_type != "meta_extract_batch":
        return
    batch_id = _job_related_uuid(job, "batch_id")
    if batch_id is None:
        return
    batch = await db.get(MetaExtractionBatch, batch_id)
    if batch is None or batch.status == "completed":
        return
    if status == "queued":
        batch.status = "created"
    elif status in {"started", "progress"}:
        batch.status = "processing"
    elif status in {"failed", "cancelled"}:
        batch.status = "failed"


async def _sync_related_records(
    db: AsyncSession,
    *,
    job: Job,
    status: str,
    message: str | None = None,
) -> None:
    await _sync_analysis_run_for_job(db, job=job, status=status, message=message)
    await _sync_meta_item_for_job(db, job=job, status=status, message=message)
    await _sync_meta_batch_for_job(db, job=job, status=status)


@router.get("")
@limiter.limit("60/minute")
async def list_jobs(
    request: Request,
    status: str | None = None,
    job_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    limit = max(1, min(200, int(limit)))
    offset = max(0, int(offset))

    # DB query first
    from sqlalchemy import select

    stmt = select(Job).where(Job.user_id == user.id)
    if status:
        stmt = stmt.where(Job.status == status)
    if job_type:
        stmt = stmt.where(Job.job_type == job_type)
    stmt = stmt.order_by(Job.created_at.desc()).limit(limit).offset(offset)

    q = await db.execute(stmt)
    items = [j for j in q.scalars().all() if j.user_id == user.id]

    return [
        {
            "id": str(j.id),
            "job_type": j.job_type,
            "status": j.status,
            "progress_percent": j.progress_percent or 0,
            "queue_name": j.queue_name,
            "attempt": j.attempt,
            "next_retry_at": j.next_retry_at.isoformat() if j.next_retry_at else None,
            "created_at": j.created_at.isoformat() if j.created_at else None,
            "started_at": j.started_at.isoformat() if j.started_at else None,
            "completed_at": j.completed_at.isoformat() if j.completed_at else None,
            "error": j.error_message,
            "result": j.result,
        }
        for j in items
    ]


@router.post("/{job_id}/cancel")
@limiter.limit("10/minute")
async def cancel_job(
    request: Request,
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    job = await db.get(Job, job_id)
    if not job or job.user_id != user.id:
        raise HTTPException(status_code=404, detail="Job no encontrado")

    # Best-effort cancel in RQ
    rq_job_id = (job.result or {}).get("rq_job_id")
    if rq_job_id and redis_available():
        try:
            redis = get_redis()
            rq_job = RQJob.fetch(rq_job_id, connection=redis)
            try:
                rq_job.cancel()
            except Exception:
                # fallback: delete from queue if possible
                try:
                    rq_job.delete(remove_from_queue=True)
                except Exception:
                    pass
        except Exception:
            pass

    # Keep explicit cancellation semantics for the UI.
    job.status = "cancelled"
    job.error_message = "Cancelled by user"
    job.completed_at = job.completed_at or datetime.utcnow()
    await _sync_related_records(db, job=job, status="cancelled", message=job.error_message)
    await db.commit()

    return {"ok": True, "id": str(job.id), "status": job.status}


@router.post("/{job_id}/retry")
@limiter.limit("10/minute")
async def retry_job(
    request: Request,
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    del request
    if not redis_available():
        raise HTTPException(status_code=503, detail="Redis no disponible; retry deshabilitado")
    job = await db.get(Job, job_id)
    if not job or job.user_id != user.id:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    if job.status not in ("failed", "retry_pending"):
        raise HTTPException(status_code=400, detail="Solo se pueden reintentar jobs failed o retry_pending")
    rq_job_id = retry_job_record(job)
    await _sync_related_records(db, job=job, status="queued")
    await db.commit()
    return {"ok": True, "id": str(job.id), "status": job.status, "rq_job_id": rq_job_id}


def _map_rq_status(rq_status: str) -> str:
    # rq statuses: queued, started, deferred, finished, failed
    if rq_status in ("queued", "deferred"):
        return "queued"
    if rq_status == "started":
        return "started"
    if rq_status == "finished":
        return "completed"
    if rq_status == "failed":
        return "failed"
    return "progress"


@router.get("/{job_id}")
@limiter.limit("120/minute")
async def get_job(
    request: Request,
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    job = await db.get(Job, job_id)
    if not job or job.user_id != user.id:
        raise HTTPException(status_code=404, detail="Job no encontrado")

    if job.status in TERMINAL_JOB_STATUSES:
        return _serialize_job(job)

    # Solo los jobs activos dependen de Redis para polling.
    if not redis_available():
        return _serialize_job(job)

    rq_job_id = (job.result or {}).get("rq_job_id")
    if not rq_job_id:
        return _serialize_job(job)

    try:
        redis = get_redis()
        try:
            rq_job = RQJob.fetch(rq_job_id, connection=redis)
        except Exception:
            if job.status in TERMINAL_JOB_STATUSES:
                return _serialize_job(job)
            job.status = "failed"
            job.error_message = "RQ job no encontrado en Redis"
            job.completed_at = job.completed_at or datetime.utcnow()
            await _sync_related_records(db, job=job, status="failed", message=job.error_message)
            await db.commit()
            return _serialize_job(job)

        status = _map_rq_status(rq_job.get_status())
        meta_progress = rq_job.meta.get("progress_percent") if isinstance(rq_job.meta, dict) else None

        if meta_progress is not None:
            job.progress_percent = int(meta_progress)
        if status in ("started", "progress") and job.started_at is None:
            job.started_at = datetime.utcnow()
        if status in ("completed", "failed") and job.completed_at is None:
            job.completed_at = datetime.utcnow()

        job.status = status

        if status == "completed":
            job.progress_percent = 100
            job.result = {**(job.result or {}), "rq_result": rq_job.result}
        elif status == "failed":
            job.error_message = str(rq_job.exc_info or "Job failed")
        job.queue_name = job.queue_name or getattr(rq_job, "origin", None)
        await _sync_related_records(db, job=job, status=status, message=job.error_message)

        await db.commit()
    except RedisError:
        raise HTTPException(status_code=503, detail="Redis error")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error consultando job: {e}")

    return _serialize_job(job)
