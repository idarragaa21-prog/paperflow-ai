from datetime import datetime
from uuid import UUID

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.storage import storage_manager
from app.middleware.rate_limit import limiter
from app.models.job import Job
from app.models.project import Project
from app.models.user import User
from app.schemas.projects import ProjectCreate, ProjectResponse, ProjectUpdate
from app.services.jobs import get_job_queue

router = APIRouter(prefix="/projects", tags=["projects"])


def _safe_abs_path(relative_path: str) -> Path:
    full_path = (storage_manager.base_dir / relative_path).resolve()
    try:
        full_path.relative_to(storage_manager.base_dir)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid file path")
    return full_path


def _project_response(project: Project) -> ProjectResponse:
    return ProjectResponse(
        id=project.id,
        title=project.title,
        description=project.description,
        clinical_area=project.clinical_area,
        runtime_mode=getattr(project, "runtime_mode", "local_only") or "local_only",
        archived=project.archived,
    )


@router.post("", response_model=ProjectResponse)
@limiter.limit("10/minute")
async def create_project(
    request: Request,
    payload: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = Project(
        user_id=user.id,
        title=payload.title,
        description=payload.description,
        clinical_area=payload.clinical_area,
        runtime_mode=payload.runtime_mode,
        archived=False,
        updated_at=datetime.utcnow(),
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return _project_response(project)


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = await db.execute(select(Project).where(Project.user_id == user.id).order_by(Project.created_at.desc()))
    items = q.scalars().all()
    return [_project_response(p) for p in items]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = await db.get(Project, project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    return _project_response(project)


@router.patch("/{project_id}", response_model=ProjectResponse)
@limiter.limit("20/minute")
async def update_project(
    request: Request,
    project_id: UUID,
    payload: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = await db.get(Project, project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    if payload.title is not None:
        project.title = payload.title
    if payload.description is not None:
        project.description = payload.description
    if payload.clinical_area is not None:
        project.clinical_area = payload.clinical_area
    if payload.runtime_mode is not None:
        project.runtime_mode = payload.runtime_mode

    project.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(project)

    return _project_response(project)


@router.post("/{project_id}/archive")
@limiter.limit("10/minute")
async def archive_project(
    request: Request,
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = await db.get(Project, project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    project.archived = True
    project.updated_at = datetime.utcnow()
    await db.commit()

    return {"ok": True}


@router.get("/{project_id}/dashboard")
async def project_dashboard(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = await db.get(Project, project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    from sqlalchemy import func

    from app.models.meta_extractor import ExtractedStudy
    from app.models.note import Note
    from app.models.paper import Paper
    from app.models.presentation import Presentation
    from app.models.reference_item import ReferenceItem

    qp = await db.execute(select(func.count()).select_from(Paper).where(Paper.project_id == project_id))
    qn = await db.execute(select(func.count()).select_from(Note).where(Note.project_id == project_id))
    qpr = await db.execute(select(func.count()).select_from(Presentation).where(Presentation.project_id == project_id))
    qs = await db.execute(
        select(func.count()).select_from(ExtractedStudy).where(ExtractedStudy.project_id == project_id).where(ExtractedStudy.is_current == True)  # noqa
    )
    qr = await db.execute(select(func.count()).select_from(ReferenceItem).where(ReferenceItem.project_id == project_id))

    return {
        "project_id": str(project_id),
        "counts": {
            "papers": int(qp.scalar() or 0),
            "notes": int(qn.scalar() or 0),
            "presentations": int(qpr.scalar() or 0),
            "meta_studies_current": int(qs.scalar() or 0),
            "references": int(qr.scalar() or 0),
        },
    }


@router.get("/{project_id}/library")
async def project_library(
    project_id: UUID,
    year: int | None = None,
    author: str | None = None,
    journal: str | None = None,
    open_access: bool | None = None,
    processing_status: str | None = None,
    favorite: bool | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = await db.get(Project, project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    from app.models.paper import Paper

    clauses = [Paper.project_id == project_id]
    if year is not None:
        clauses.append(Paper.publication_year == year)
    if journal:
        clauses.append(Paper.journal.ilike(f"%{journal.strip()}%"))
    if processing_status:
        clauses.append(Paper.processing_status == processing_status)
    if open_access is not None:
        clauses.append(Paper.is_open_access == open_access)
    if favorite is not None:
        clauses.append(Paper.favorite == favorite)
    if author:
        clauses.append(Paper.authors.ilike(f"%{author.strip()}%"))

    q = await db.execute(select(Paper).where(and_(*clauses)).order_by(Paper.created_at.desc()))
    items = q.scalars().all()
    return [
        {
            "id": str(p.id),
            "title": p.title,
            "authors": p.authors,
            "journal": p.journal,
            "publication_year": p.publication_year,
            "doi": p.doi,
            "pmid": p.pmid,
            "filename": p.filename,
            "language": p.language,
            "source_provider": p.source_provider,
            "source_type": p.source_type,
            "is_open_access": p.is_open_access,
            "oa_url": p.oa_url,
            "favorite": p.favorite,
            "is_processed": p.is_processed,
            "processing_status": p.processing_status,
            "processing_warnings": p.processing_warnings or [],
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in items
    ]


@router.post("/{project_id}/export-zip")
@limiter.limit("3/minute")
async def export_project_zip(
    request: Request,
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = await db.get(Project, project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    job_record = Job(
        user_id=user.id,
        job_type="project_export_zip",
        status="queued",
        input_params={"project_id": str(project_id)},
        result={},
        progress_percent=0,
    )
    db.add(job_record)
    await db.commit()
    await db.refresh(job_record)

    try:
        from app.workers.tasks import export_project_zip_job

        q = get_job_queue()
        rq_job = q.enqueue(export_project_zip_job, args=(str(job_record.id), str(project_id)), job_timeout="30m")
    except Exception:
        job_record.status = "failed"
        job_record.error_message = "No se pudo encolar job (Redis no disponible?)"
        await db.commit()
        raise HTTPException(status_code=503, detail="No se pudo encolar job")

    job_record.result = {"rq_job_id": rq_job.id}
    await db.commit()

    return {"job_id": str(job_record.id)}


@router.get("/{project_id}/export-zip/{job_id}/download")
async def download_project_zip(
    project_id: UUID,
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = await db.get(Project, project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    job = await db.get(Job, job_id)
    if not job or job.user_id != user.id:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.job_type != "project_export_zip":
        raise HTTPException(status_code=400, detail="Job type mismatch")

    out = (job.result or {}).get("output")
    if not out:
        # fallback when polled and stored under rq_result
        out = ((job.result or {}).get("rq_result") or {}).get("output")

    zip_rel = (out or {}).get("zip_file_path")
    fname = (out or {}).get("filename") or "project_export.zip"

    if job.status != "completed" or not zip_rel:
        raise HTTPException(status_code=400, detail="Export not ready")

    abs_path = _safe_abs_path(zip_rel)
    if not abs_path.exists():
        raise HTTPException(status_code=404, detail="Export file not found")

    return FileResponse(str(abs_path), filename=fname)
