from datetime import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from redis.exceptions import RedisError
from rq.job import Job as RQJob
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.redis_conn import get_redis, redis_available
from app.middleware.rate_limit import limiter
from app.models.job import Job
from app.models.user import User
from app.services.jobs import retry_job_record

router = APIRouter(prefix="/jobs", tags=["jobs"])


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

    # Mark as failed/cancelled (stable semantics)
    job.status = "failed"
    job.error_message = "Cancelled by user"
    job.completed_at = job.completed_at or datetime.utcnow()
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

    # En development Redis puede estar apagado → 503
    if not redis_available():
        raise HTTPException(status_code=503, detail="Redis no disponible; polling de jobs deshabilitado")

    rq_job_id = (job.result or {}).get("rq_job_id")
    if not rq_job_id:
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

    try:
        redis = get_redis()
        try:
            rq_job = RQJob.fetch(rq_job_id, connection=redis)
        except Exception:
            job.status = "failed"
            job.error_message = "RQ job no encontrado en Redis"
            job.completed_at = job.completed_at or datetime.utcnow()
            await db.commit()
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

        await db.commit()
    except RedisError:
        raise HTTPException(status_code=503, detail="Redis error")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error consultando job: {e}")

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
