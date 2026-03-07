from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.storage import storage_manager
from app.middleware.rate_limit import limiter
from app.models.job import Job
from app.models.paper import Paper
from app.models.presentation import Presentation
from app.models.project import Project
from app.models.user import User
from app.schemas.presentation import CreatePresentationRequest
from app.services.jobs import enqueue_presentation

router = APIRouter(prefix="/presentations", tags=["presentations"])


def _safe_abs_path(relative_path: str) -> Path:
    full_path = (storage_manager.base_dir / relative_path).resolve()
    try:
        full_path.relative_to(storage_manager.base_dir)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid file path")
    return full_path


@router.post("/generate")
@limiter.limit("3/minute")
async def create_presentation(
    request: Request,
    payload: CreatePresentationRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = await db.get(Project, payload.project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    # Validar
    if not payload.paper_ids:
        raise HTTPException(status_code=400, detail="Debe seleccionar al menos 1 paper")
    if len(payload.paper_ids) > 10:
        raise HTTPException(status_code=400, detail="Máximo 10 papers")

    for pid in payload.paper_ids:
        paper = await db.get(Paper, pid)
        if not paper:
            raise HTTPException(status_code=404, detail=f"Paper {pid} no encontrado")
        if paper.project_id != payload.project_id:
            raise HTTPException(status_code=403, detail="Paper no pertenece al proyecto")

    # Crear registro Job (primero) para pasar job_id al worker
    job_record = Job(
        user_id=user.id,
        job_type="generate_presentation",
        status="queued",
        # Ensure JSONB serializable (UUID -> str)
        input_params=payload.model_dump(mode="json"),
        result={},
        progress_percent=0,
    )
    db.add(job_record)
    await db.commit()
    await db.refresh(job_record)

    # Encolar
    try:
        rq_job_id = enqueue_presentation(
            job_record.id,
            payload.project_id,
            payload.topic,
            payload.duration_minutes,
            payload.audience,
            payload.paper_ids,
            payload.num_slides,
        )
    except Exception:
        job_record.status = "failed"
        job_record.error_message = "No se pudo encolar job (Redis no disponible?)"
        await db.commit()
        raise HTTPException(status_code=503, detail="No se pudo encolar job")

    job_record.result = {"rq_job_id": rq_job_id}
    await db.commit()

    return {"job_id": str(job_record.id)}


@router.get("/{presentation_id}")
async def get_presentation(
    presentation_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    pres = await db.get(Presentation, presentation_id)
    if not pres:
        raise HTTPException(status_code=404, detail="Presentation not found")

    project = await db.get(Project, pres.project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Presentation not found")

    return {
        "id": str(pres.id),
        "project_id": str(pres.project_id),
        "title": pres.title,
        "topic": pres.topic,
        "duration_minutes": pres.duration_minutes,
        "audience": pres.audience,
        "filename": pres.filename,
        "file_path": pres.file_path,
        "outline": pres.outline,
        "references_used": pres.references_used,
        "llm_model": pres.llm_model,
        "llm_usage": pres.llm_usage,
        "created_at": pres.created_at,
    }


@router.get("/{presentation_id}/download")
async def download_presentation(
    presentation_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    pres = await db.get(Presentation, presentation_id)
    if not pres:
        raise HTTPException(status_code=404, detail="Presentation not found")

    project = await db.get(Project, pres.project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Presentation not found")

    if not pres.file_path or not pres.filename:
        raise HTTPException(status_code=404, detail="Presentation file missing")

    abs_path = _safe_abs_path(pres.file_path)
    if not abs_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        abs_path,
        filename=pres.filename,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )


@router.delete("/{presentation_id}")
async def delete_presentation(
    presentation_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    pres = await db.get(Presentation, presentation_id)
    if not pres:
        raise HTTPException(status_code=404, detail="Presentation not found")

    project = await db.get(Project, pres.project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Presentation not found")

    if pres.file_path:
        try:
            storage_manager.delete_file(pres.file_path)
        except Exception:
            pass

    await db.delete(pres)
    await db.commit()
    return {"ok": True}


@router.get("/projects/{project_id}/presentations")
async def list_presentations(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = await db.get(Project, project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    q = await db.execute(
        select(Presentation).where(Presentation.project_id == project_id).order_by(Presentation.created_at.desc())
    )
    items = q.scalars().all()
    return [
        {
            "id": str(p.id),
            "title": p.title,
            "topic": p.topic,
            "duration_minutes": p.duration_minutes,
            "audience": p.audience,
            "filename": p.filename,
            "created_at": p.created_at,
        }
        for p in items
    ]
