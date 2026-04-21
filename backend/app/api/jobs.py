from datetime import datetime, timezone
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from redis.exceptions import RedisError
from rq.job import Job as RQJob
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from dataclasses import dataclass

from app.core.redis_conn import get_redis, redis_available
from app.middleware.rate_limit import limiter
from app.models.job import Job
from app.core.logger import logger
from app.models.user import User

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _serialize_job(job: Job) -> dict:
    return {
        "id": str(job.id),
        "job_type": job.job_type,
        "status": job.status,
        "progress_percent": job.progress_percent or 0,
        "created_at": job.created_at.isoformat() if getattr(job, "created_at", None) else None,
        "started_at": job.started_at.isoformat() if getattr(job, "started_at", None) else None,
        "completed_at": job.completed_at.isoformat() if getattr(job, "completed_at", None) else None,
        "error": job.error_message,
        "result": job.result,
    }


def _parse_uuid(value: str | None) -> uuid.UUID | None:
    if not value:
        return None
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None


def _merge_warning(existing: list[str] | None, message: str | None) -> list[str]:
    warnings = list(existing or [])
    if message and message not in warnings:
        warnings.append(message)
    return warnings


async def _sync_related_state(
    db: AsyncSession,
    *,
    job: Job,
    target_status: str,
    warning: str | None = None,
) -> None:
    input_params = dict(job.input_params or {})

    if job.job_type == "meta_extract_paper":
        from app.models.meta_extractor import MetaExtractionItem

        item_id = _parse_uuid(input_params.get("item_id"))
        if not item_id:
            return
        item = await db.get(MetaExtractionItem, item_id)
        if not item:
            return
        item.status = "queued" if target_status in {"queued", "started", "progress"} else target_status
        item.error_message = None if target_status == "queued" else warning


def retry_job_record(current_job: Job) -> str:
    rq_job_id = (current_job.result or {}).get("rq_job_id")
    if not rq_job_id:
        raise ValueError("RQ job id missing")

    redis = get_redis()
    rq_job = RQJob.fetch(rq_job_id, connection=redis)

    try:
        retried = rq_job.retry()
    except TypeError:
        retried = rq_job.retry(queue=None)

    if isinstance(retried, str):
        return retried
    if hasattr(retried, "id"):
        return str(retried.id)
    return str(rq_job_id)


@dataclass
class JobFilters:
    status: str | None = None
    job_type: str | None = None
    limit: int = 50
    offset: int = 0


@router.get("")
@limiter.limit("60/minute")
async def list_jobs(
    request: Request,
    filters: JobFilters = Depends(),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    limit = max(1, min(200, int(filters.limit)))
    offset = max(0, int(filters.offset))

    # DB query first
    from sqlalchemy import select

    stmt = select(Job).where(Job.user_id == user.id)
    if filters.status:
        stmt = stmt.where(Job.status == filters.status)
    if filters.job_type:
        stmt = stmt.where(Job.job_type == filters.job_type)
    stmt = stmt.order_by(Job.created_at.desc()).limit(limit).offset(offset)

    q = await db.execute(stmt)
    items = [j for j in q.scalars().all() if j.user_id == user.id]

    return [
        _serialize_job(j)
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
            except Exception as e:
                logger.warning("Failed to cancel RQ job {}, attempting delete: {}", rq_job_id, e)
                # fallback: delete from queue if possible
                try:
                    rq_job.delete(remove_from_queue=True)
                except Exception as e2:
                    logger.warning("Failed to delete RQ job {} from queue: {}", rq_job_id, e2)
        except Exception as e:
            logger.warning("Failed to fetch RQ job {} for cancellation: {}", rq_job_id, e)

    job.status = "cancelled"
    job.error_message = "Cancelled by user"
    job.completed_at = job.completed_at or datetime.now(timezone.utc)
    await _sync_related_state(db, job=job, target_status="cancelled", warning="Cancelled by user")
    await db.commit()

    return {"ok": True, "id": str(job.id), "status": job.status}


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

    if not redis_available():
        return _serialize_job(job)

    rq_job_id = (job.result or {}).get("rq_job_id")
    if not rq_job_id:
        return _serialize_job(job)

    try:
        redis = get_redis()
        try:
            rq_job = RQJob.fetch(rq_job_id, connection=redis)
        except Exception as e:
            logger.warning("RQ job {} not found in Redis: {}", rq_job_id, e)
            job.status = "failed"
            job.error_message = "RQ job no encontrado en Redis"
            job.completed_at = job.completed_at or datetime.now(timezone.utc)
            await _sync_related_state(db, job=job, target_status="failed", warning="RQ job no encontrado en Redis")
            await db.commit()
            return _serialize_job(job)

        status = _map_rq_status(rq_job.get_status())
        meta_progress = rq_job.meta.get("progress_percent") if isinstance(rq_job.meta, dict) else None

        if meta_progress is not None:
            job.progress_percent = int(meta_progress)
        if status in ("started", "progress") and job.started_at is None:
            job.started_at = datetime.now(timezone.utc)
        if status in ("completed", "failed") and job.completed_at is None:
            job.completed_at = datetime.now(timezone.utc)

        job.status = status

        if status == "completed":
            job.progress_percent = 100
            job.result = {**(job.result or {}), "rq_result": rq_job.result}
        elif status == "failed":
            job.error_message = str(rq_job.exc_info or "Job failed")
            await _sync_related_state(db, job=job, target_status="failed", warning=job.error_message)

        await db.commit()
    except RedisError:
        return _serialize_job(job)
    except Exception as e:
        logger.exception("Error consultando job: {}", e)
        raise HTTPException(status_code=500, detail="Error interno consultando job")

    return _serialize_job(job)


@router.post("/{job_id}/retry")
@limiter.limit("10/minute")
async def retry_job(
    request: Request,
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    job = await db.get(Job, job_id)
    if not job or job.user_id != user.id:
        raise HTTPException(status_code=404, detail="Job no encontrado")

    if str(job.status or "").lower() not in {"failed", "cancelled"}:
        raise HTTPException(status_code=409, detail="Solo se pueden reintentar jobs fallidos o cancelados")

    if not redis_available():
        raise HTTPException(status_code=503, detail="Redis no disponible")

    try:
        new_rq_job_id = retry_job_record(job)
    except RedisError as exc:
        raise HTTPException(status_code=503, detail="Redis error") from exc
    except Exception as exc:
        logger.exception("No se pudo reintentar el job: {}", exc)
        raise HTTPException(status_code=500, detail="Error interno al reintentar el job") from exc

    job.status = "queued"
    job.progress_percent = 0
    job.error_message = None
    job.started_at = None
    job.completed_at = None
    job.result = {**(job.result or {}), "rq_job_id": new_rq_job_id}
    await _sync_related_state(db, job=job, target_status="queued")
    await db.commit()

    return {"ok": True, "id": str(job.id), "status": job.status, "rq_job_id": new_rq_job_id}
