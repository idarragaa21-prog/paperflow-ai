from datetime import datetime
from pathlib import Path
import time
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.metrics import library_query_duration_seconds
from app.core.storage import storage_manager
from app.middleware.rate_limit import limiter
from app.models.job import Job
from app.models.membership import ProjectMembership
from app.models.project import Project
from app.models.user import User
from app.schemas.projects import (
    ProjectCreate,
    ProjectMembershipCreate,
    ProjectMembershipPatch,
    ProjectMembershipResponse,
    ProjectResponse,
    ProjectUpdate,
)
from app.services.audit import log_audit
from app.services.jobs import get_job_queue
from app.services.pagination import apply_desc_cursor, encode_cursor
from app.services.permissions import list_accessible_projects, require_project_access

router = APIRouter(prefix="/projects", tags=["projects"])


def _safe_abs_path(relative_path: str) -> Path:
    full_path = (storage_manager.base_dir / relative_path).resolve()
    try:
        full_path.relative_to(storage_manager.base_dir)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid file path") from exc
    return full_path


def _project_response(project: Project, *, role: str | None = None) -> ProjectResponse:
    return ProjectResponse(
        id=project.id,
        title=project.title,
        description=project.description,
        clinical_area=project.clinical_area,
        runtime_mode=getattr(project, "runtime_mode", "local_only") or "local_only",
        archived=project.archived,
        role=role,
    )


def _membership_response(item: ProjectMembership) -> ProjectMembershipResponse:
    return ProjectMembershipResponse(id=item.id, project_id=item.project_id, user_id=item.user_id, role=item.role)


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
    db.add(ProjectMembership(project=project, user_id=user.id, role="owner"))
    await db.commit()
    await db.refresh(project)
    await log_audit(
        db,
        user=user,
        action="create",
        entity_type="project",
        entity_id=project.id,
        details={"role": "owner"},
        request=request,
    )
    return _project_response(project, role="owner")


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    items = await list_accessible_projects(db, user=user)
    return [_project_response(project, role=role) for project, role in items]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project, membership = await require_project_access(db, project_id=project_id, user=user, required_role="viewer")
    return _project_response(project, role=membership.role)


@router.patch("/{project_id}", response_model=ProjectResponse)
@limiter.limit("20/minute")
async def update_project(
    request: Request,
    project_id: UUID,
    payload: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project, membership = await require_project_access(db, project_id=project_id, user=user, required_role="editor")

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
    await log_audit(
        db,
        user=user,
        action="update",
        entity_type="project",
        entity_id=project.id,
        details={"role": membership.role},
        request=request,
    )
    return _project_response(project, role=membership.role)


@router.post("/{project_id}/archive")
@limiter.limit("10/minute")
async def archive_project(
    request: Request,
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project, membership = await require_project_access(db, project_id=project_id, user=user, required_role="owner")
    project.archived = True
    project.updated_at = datetime.utcnow()
    await db.commit()
    await log_audit(
        db,
        user=user,
        action="archive",
        entity_type="project",
        entity_id=project.id,
        details={"role": membership.role},
        request=request,
    )
    return {"ok": True}


@router.get("/{project_id}/members", response_model=list[ProjectMembershipResponse])
async def list_project_members(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await require_project_access(db, project_id=project_id, user=user, required_role="viewer")
    result = await db.execute(
        select(ProjectMembership).where(ProjectMembership.project_id == project_id).order_by(ProjectMembership.created_at.asc())
    )
    return [_membership_response(item) for item in result.scalars().all()]


@router.post("/{project_id}/members", response_model=ProjectMembershipResponse)
async def create_project_member(
    project_id: UUID,
    payload: ProjectMembershipCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await require_project_access(db, project_id=project_id, user=user, required_role="owner")
    existing = await db.execute(
        select(ProjectMembership)
        .where(ProjectMembership.project_id == project_id)
        .where(ProjectMembership.user_id == payload.user_id)
    )
    membership = existing.scalars().first()
    if membership:
        membership.role = payload.role
    else:
        membership = ProjectMembership(project_id=project_id, user_id=payload.user_id, role=payload.role)
        db.add(membership)
    await db.commit()
    await db.refresh(membership)
    await log_audit(
        db,
        user=user,
        action="create",
        entity_type="project_membership",
        entity_id=membership.id,
        details={"project_id": str(project_id), "user_id": str(payload.user_id), "role": payload.role},
        request=request,
    )
    return _membership_response(membership)


@router.patch("/{project_id}/members/{membership_id}", response_model=ProjectMembershipResponse)
async def patch_project_member(
    project_id: UUID,
    membership_id: UUID,
    payload: ProjectMembershipPatch,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await require_project_access(db, project_id=project_id, user=user, required_role="owner")
    membership = await db.get(ProjectMembership, membership_id)
    if not membership or membership.project_id != project_id:
        raise HTTPException(status_code=404, detail="Membership not found")
    membership.role = payload.role
    await db.commit()
    await db.refresh(membership)
    await log_audit(
        db,
        user=user,
        action="update",
        entity_type="project_membership",
        entity_id=membership.id,
        details={"project_id": str(project_id), "role": payload.role},
        request=request,
    )
    return _membership_response(membership)


@router.delete("/{project_id}/members/{membership_id}")
async def delete_project_member(
    project_id: UUID,
    membership_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await require_project_access(db, project_id=project_id, user=user, required_role="owner")
    membership = await db.get(ProjectMembership, membership_id)
    if not membership or membership.project_id != project_id:
        raise HTTPException(status_code=404, detail="Membership not found")
    if membership.role == "owner":
        owner_count_q = await db.execute(
            select(func.count())
            .select_from(ProjectMembership)
            .where(ProjectMembership.project_id == project_id)
            .where(ProjectMembership.role == "owner")
        )
        if int(owner_count_q.scalar() or 0) <= 1:
            raise HTTPException(status_code=400, detail="Cannot remove the last owner")
    await db.delete(membership)
    await db.commit()
    await log_audit(
        db,
        user=user,
        action="delete",
        entity_type="project_membership",
        entity_id=membership_id,
        details={"project_id": str(project_id)},
        request=request,
    )
    return {"ok": True}


@router.get("/{project_id}/dashboard")
async def project_dashboard(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await require_project_access(db, project_id=project_id, user=user, required_role="viewer")

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
    limit: int = 50,
    cursor: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await require_project_access(db, project_id=project_id, user=user, required_role="viewer")

    from app.models.paper import Paper

    limit = max(1, min(100, int(limit)))
    filters = [Paper.project_id == project_id]
    if year is not None:
        filters.append(Paper.publication_year == year)
    if journal:
        filters.append(Paper.journal.ilike(f"%{journal.strip()}%"))
    if processing_status:
        filters.append(Paper.processing_status == processing_status)
    if open_access is not None:
        filters.append(Paper.is_open_access == open_access)
    if favorite is not None:
        filters.append(Paper.favorite == favorite)
    if author:
        filters.append(Paper.authors.ilike(f"%{author.strip()}%"))

    cursor_clause = apply_desc_cursor(Paper, created_at=Paper.created_at, row_id=Paper.id, cursor=cursor)
    page_filters = list(filters)
    if cursor_clause is not None:
        page_filters.append(cursor_clause)

    started_at = time.perf_counter()
    total_q = await db.execute(select(func.count()).select_from(Paper).where(and_(*filters)))
    q = await db.execute(
        select(Paper)
        .where(and_(*page_filters))
        .order_by(Paper.created_at.desc(), Paper.id.desc())
        .limit(limit + 1)
    )
    library_query_duration_seconds.observe(time.perf_counter() - started_at)
    rows = q.scalars().all()
    has_more = len(rows) > limit
    items = rows[:limit]
    next_cursor = encode_cursor(created_at=items[-1].created_at, row_id=items[-1].id) if has_more and items else None

    return {
        "items": [
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
        ],
        "next_cursor": next_cursor,
        "has_more": has_more,
        "total_count": int(total_q.scalar() or 0),
    }


@router.post("/{project_id}/export-zip")
@limiter.limit("3/minute")
async def export_project_zip(
    request: Request,
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await require_project_access(db, project_id=project_id, user=user, required_role="owner")

    job_record = Job(
        user_id=user.id,
        job_type="project_export_zip",
        status="queued",
        input_params={"project_id": str(project_id)},
        result={},
        progress_percent=0,
        queue_name="documents",
    )
    db.add(job_record)
    await db.commit()
    await db.refresh(job_record)

    try:
        from app.workers.tasks import export_project_zip_job

        q = get_job_queue("documents")
        rq_job = q.enqueue(export_project_zip_job, args=(str(job_record.id), str(project_id)), job_timeout="30m")
    except Exception:
        job_record.status = "failed"
        job_record.error_message = "No se pudo encolar job (Redis no disponible?)"
        await db.commit()
        raise HTTPException(status_code=503, detail="No se pudo encolar job")

    job_record.result = {"rq_job_id": rq_job.id}
    await db.commit()
    await log_audit(
        db,
        user=user,
        action="export",
        entity_type="project",
        entity_id=project_id,
        details={"job_id": str(job_record.id)},
        request=request,
    )
    return {"job_id": str(job_record.id)}


@router.get("/{project_id}/export-zip/{job_id}/download")
async def download_project_zip(
    project_id: UUID,
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await require_project_access(db, project_id=project_id, user=user, required_role="owner")

    job = await db.get(Job, job_id)
    if not job or job.user_id != user.id:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.job_type != "project_export_zip":
        raise HTTPException(status_code=400, detail="Job type mismatch")

    out = (job.result or {}).get("output")
    if not out:
        out = ((job.result or {}).get("rq_result") or {}).get("output")

    zip_rel = (out or {}).get("zip_file_path")
    fname = (out or {}).get("filename") or "project_export.zip"
    if job.status != "completed" or not zip_rel:
        raise HTTPException(status_code=400, detail="Export not ready")

    abs_path = _safe_abs_path(zip_rel)
    if not abs_path.exists():
        raise HTTPException(status_code=404, detail="Export file not found")

    return FileResponse(str(abs_path), filename=fname)
