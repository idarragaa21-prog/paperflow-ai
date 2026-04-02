from datetime import datetime, timezone
import secrets
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
from app.models.membership import PROJECT_MEMBER_ROLES, PROJECT_INVITATION_STATUSES, ProjectInvitation, ProjectMembership
from app.models.project import Project
from app.models.user import User
from app.schemas.membership import (
    ProjectInvitationAcceptResponse,
    ProjectInvitationLookupResponse,
    ProjectInvitationResponse,
    ProjectInviteResultResponse,
    ProjectMemberInviteRequest,
    ProjectMemberResponse,
    ProjectMemberUpdateRequest,
)
from app.schemas.projects import ProjectCreate, ProjectResponse, ProjectUpdate
from app.services.email import build_project_invitation_url, send_project_invitation_email
from app.core.logger import logger
from app.services.jobs import get_job_queue
from app.services.permissions import list_accessible_projects, require_project_access

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


def _normalize_membership_role(role: str | None) -> str:
    return role if role in PROJECT_MEMBER_ROLES else "viewer"


def _member_response(*, project_id: UUID, user: User, role: str, membership: ProjectMembership | None = None) -> ProjectMemberResponse:
    return ProjectMemberResponse(
        id=getattr(membership, "id", None),
        project_id=project_id,
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=_normalize_membership_role(role),  # type: ignore[arg-type]
        created_at=getattr(membership, "created_at", None),
    )


def _invitation_status(invitation: ProjectInvitation) -> str:
    if invitation.revoked_at is not None:
        return "revoked"
    if invitation.accepted_at is not None:
        return "accepted"
    return "pending"


def _invitation_response(invitation: ProjectInvitation) -> ProjectInvitationResponse:
    status = _invitation_status(invitation)
    if status not in PROJECT_INVITATION_STATUSES:
        status = "pending"
    return ProjectInvitationResponse(
        id=invitation.id,
        project_id=invitation.project_id,
        email=invitation.email,
        role=_normalize_membership_role(invitation.role),  # type: ignore[arg-type]
        token=invitation.token,
        accept_path=f"/project-invitations/{invitation.token}",
        status=status,  # type: ignore[arg-type]
        created_at=invitation.created_at,
        accepted_at=invitation.accepted_at,
        revoked_at=invitation.revoked_at,
    )


async def _list_project_members(db: AsyncSession, *, project: Project) -> list[ProjectMemberResponse]:
    rows = await db.execute(
        select(ProjectMembership, User)
        .join(User, User.id == ProjectMembership.user_id)
        .where(ProjectMembership.project_id == project.id)
        .order_by(ProjectMembership.created_at.asc())
    )

    members_by_user: dict[UUID, ProjectMemberResponse] = {}
    owner_user = await db.get(User, project.user_id)
    if owner_user is not None:
        members_by_user[owner_user.id] = _member_response(project_id=project.id, user=owner_user, role="owner")

    for membership, member_user in rows.all():
        effective_role = "owner" if member_user.id == project.user_id else _normalize_membership_role(membership.role)
        existing = members_by_user.get(member_user.id)
        if existing is None or existing.role != "owner":
            members_by_user[member_user.id] = _member_response(
                project_id=project.id,
                user=member_user,
                role=effective_role,
                membership=membership,
            )

    ordered = sorted(
        members_by_user.values(),
        key=lambda item: (
            0 if item.role == "owner" else 1 if item.role == "editor" else 2,
            (item.full_name or item.email).lower(),
        ),
    )
    return ordered


async def _get_membership_for_user(
    db: AsyncSession,
    *,
    project_id: UUID,
    user_id: UUID,
) -> ProjectMembership | None:
    result = await db.execute(
        select(ProjectMembership)
        .where(ProjectMembership.project_id == project_id)
        .where(ProjectMembership.user_id == user_id)
    )
    return result.scalars().first()


async def _get_pending_invitation_for_email(
    db: AsyncSession,
    *,
    project_id: UUID,
    email: str,
) -> ProjectInvitation | None:
    result = await db.execute(
        select(ProjectInvitation)
        .where(ProjectInvitation.project_id == project_id)
        .where(ProjectInvitation.email == email)
        .where(ProjectInvitation.revoked_at.is_(None))
        .where(ProjectInvitation.accepted_at.is_(None))
        .order_by(ProjectInvitation.created_at.desc())
    )
    return result.scalars().first()


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
        updated_at=datetime.now(timezone.utc),
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
    items = await list_accessible_projects(db, user=user)
    return [_project_response(project) for project, _ in items]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project, _ = await require_project_access(db, project_id=project_id, user=user, required_role="viewer")
    return _project_response(project)


@router.get("/{project_id}/members", response_model=list[ProjectMemberResponse])
async def list_project_members(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project, _ = await require_project_access(db, project_id=project_id, user=user, required_role="viewer")
    return await _list_project_members(db, project=project)


@router.get("/{project_id}/invitations", response_model=list[ProjectInvitationResponse])
async def list_project_invitations(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project, _ = await require_project_access(db, project_id=project_id, user=user, required_role="owner")
    result = await db.execute(
        select(ProjectInvitation)
        .where(ProjectInvitation.project_id == project.id)
        .where(ProjectInvitation.revoked_at.is_(None))
        .where(ProjectInvitation.accepted_at.is_(None))
        .order_by(ProjectInvitation.created_at.desc())
    )
    return [_invitation_response(item) for item in result.scalars().all()]


@router.post("/{project_id}/members", response_model=ProjectInviteResultResponse)
@limiter.limit("20/minute")
async def invite_project_member(
    request: Request,
    project_id: UUID,
    payload: ProjectMemberInviteRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project, _ = await require_project_access(db, project_id=project_id, user=user, required_role="owner")

    email = payload.email.strip().lower()
    if "@" not in email:
        raise HTTPException(status_code=422, detail="Email inválido")

    result = await db.execute(select(User).where(User.email == email))
    invited_user = result.scalar_one_or_none()
    if invited_user is not None:
        role = "owner" if invited_user.id == project.user_id else payload.role
        membership = await _get_membership_for_user(db, project_id=project.id, user_id=invited_user.id)
        if membership is None:
            membership = ProjectMembership(project_id=project.id, user_id=invited_user.id, role=role)
            db.add(membership)
        else:
            membership.role = role

        await db.commit()
        await db.refresh(membership)

        return ProjectInviteResultResponse(
            kind="membership",
            member=_member_response(project_id=project.id, user=invited_user, role=role, membership=membership),
        )

    invitation = await _get_pending_invitation_for_email(db, project_id=project.id, email=email)
    if invitation is None:
        invitation = ProjectInvitation(
            project_id=project.id,
            invited_by_user_id=user.id,
            email=email,
            role=payload.role,
            token=secrets.token_urlsafe(24),
        )
        db.add(invitation)
    else:
        invitation.role = payload.role
        invitation.token = secrets.token_urlsafe(24)

    await db.commit()
    await db.refresh(invitation)

    delivery = send_project_invitation_email(
        invitation=invitation,
        project=project,
        invited_by=user,
    )
    invitation_url = build_project_invitation_url(invitation.token)

    return ProjectInviteResultResponse(
        kind="invitation",
        invitation=_invitation_response(invitation),
        invitation_url=invitation_url,
        delivery_status=delivery.status,  # type: ignore[arg-type]
        delivery_method=delivery.method,  # type: ignore[arg-type]
        delivery_detail=delivery.detail,
    )


@router.patch("/{project_id}/members/{member_user_id}", response_model=ProjectMemberResponse)
@limiter.limit("30/minute")
async def update_project_member(
    request: Request,
    project_id: UUID,
    member_user_id: UUID,
    payload: ProjectMemberUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project, _ = await require_project_access(db, project_id=project_id, user=user, required_role="owner")

    member_user = await db.get(User, member_user_id)
    if member_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if member_user.id == project.user_id:
        raise HTTPException(status_code=400, detail="Project owner role cannot be changed")

    membership = await _get_membership_for_user(db, project_id=project.id, user_id=member_user.id)
    if membership is None:
        raise HTTPException(status_code=404, detail="Membership not found")

    membership.role = payload.role
    await db.commit()
    await db.refresh(membership)

    return _member_response(project_id=project.id, user=member_user, role=membership.role, membership=membership)


@router.delete("/{project_id}/members/{member_user_id}")
@limiter.limit("20/minute")
async def delete_project_member(
    request: Request,
    project_id: UUID,
    member_user_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project, _ = await require_project_access(db, project_id=project_id, user=user, required_role="owner")

    if member_user_id == project.user_id:
        raise HTTPException(status_code=400, detail="Project owner cannot be removed")

    membership = await _get_membership_for_user(db, project_id=project.id, user_id=member_user_id)
    if membership is None:
        raise HTTPException(status_code=404, detail="Membership not found")

    await db.delete(membership)
    await db.commit()
    return {"ok": True}


@router.delete("/{project_id}/invitations/{invitation_id}")
@limiter.limit("20/minute")
async def delete_project_invitation(
    request: Request,
    project_id: UUID,
    invitation_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project, _ = await require_project_access(db, project_id=project_id, user=user, required_role="owner")
    invitation = await db.get(ProjectInvitation, invitation_id)
    if invitation is None or invitation.project_id != project.id:
        raise HTTPException(status_code=404, detail="Invitation not found")
    if invitation.accepted_at is not None:
        raise HTTPException(status_code=400, detail="Accepted invitations cannot be removed")
    invitation.revoked_at = datetime.now(timezone.utc)
    await db.commit()
    return {"ok": True}


@router.get("/invitations/{token}", response_model=ProjectInvitationLookupResponse)
async def get_project_invitation(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ProjectInvitation).where(ProjectInvitation.token == token).limit(1))
    invitation = result.scalar_one_or_none()
    if invitation is None:
        raise HTTPException(status_code=404, detail="Invitation not found")
    project = await db.get(Project, invitation.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Invitation project not found")
    return ProjectInvitationLookupResponse(
        id=invitation.id,
        project_id=project.id,
        project_title=project.title,
        email=invitation.email,
        role=_normalize_membership_role(invitation.role),  # type: ignore[arg-type]
        status=_invitation_status(invitation),  # type: ignore[arg-type]
        accept_path=f"/project-invitations/{invitation.token}",
        accepted_at=invitation.accepted_at,
        revoked_at=invitation.revoked_at,
    )


@router.post("/invitations/{token}/accept", response_model=ProjectInvitationAcceptResponse)
@limiter.limit("20/minute")
async def accept_project_invitation(
    request: Request,
    token: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(ProjectInvitation).where(ProjectInvitation.token == token).limit(1))
    invitation = result.scalar_one_or_none()
    if invitation is None or invitation.revoked_at is not None:
        raise HTTPException(status_code=404, detail="Invitation not found")
    if invitation.accepted_at is not None:
        raise HTTPException(status_code=409, detail="Invitation already accepted")
    if user.email.lower() != invitation.email.lower():
        raise HTTPException(status_code=403, detail="Invitation email does not match the signed-in user")

    project = await db.get(Project, invitation.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Invitation project not found")

    membership = await _get_membership_for_user(db, project_id=project.id, user_id=user.id)
    role = "owner" if project.user_id == user.id else invitation.role
    if membership is None:
        membership = ProjectMembership(project_id=project.id, user_id=user.id, role=role)
        db.add(membership)
    else:
        membership.role = role

    invitation.accepted_at = datetime.now(timezone.utc)
    invitation.accepted_by_user_id = user.id
    await db.commit()
    if getattr(membership, "id", None) is not None:
        await db.refresh(membership)

    return ProjectInvitationAcceptResponse(
        project_id=project.id,
        project_title=project.title,
        member=_member_response(project_id=project.id, user=user, role=role, membership=membership),
    )


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

    project.updated_at = datetime.now(timezone.utc)
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
    project.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return {"ok": True}


@router.get("/{project_id}/dashboard")
async def project_dashboard(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project, _ = await require_project_access(db, project_id=project_id, user=user, required_role="viewer")

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


class ProjectLibraryParams:
    def __init__(
        self,
        year: int | None = None,
        author: str | None = None,
        journal: str | None = None,
        open_access: bool | None = None,
        processing_status: str | None = None,
        favorite: bool | None = None,
        limit: int | None = None,
        offset: int = 0,
    ):
        self.year = year
        self.author = author
        self.journal = journal
        self.open_access = open_access
        self.processing_status = processing_status
        self.favorite = favorite
        self.limit = limit
        self.offset = offset


@router.get("/{project_id}/library")
async def project_library(
    project_id: UUID,
    params: ProjectLibraryParams = Depends(),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await require_project_access(db, project_id=project_id, user=user, required_role="viewer")

    from app.models.paper import Paper

    clauses = [Paper.project_id == project_id]
    if params.year is not None:
        clauses.append(Paper.publication_year == params.year)
    if params.journal:
        clauses.append(Paper.journal.ilike(f"%{params.journal.strip()}%"))
    if params.processing_status:
        clauses.append(Paper.processing_status == params.processing_status)
    if params.open_access is not None:
        clauses.append(Paper.is_open_access == params.open_access)
    if params.favorite is not None:
        clauses.append(Paper.favorite == params.favorite)
    if params.author:
        clauses.append(Paper.authors.ilike(f"%{params.author.strip()}%"))

    stmt = select(Paper).where(and_(*clauses)).order_by(Paper.created_at.desc()).offset(params.offset)
    if params.limit is not None:
        stmt = stmt.limit(params.limit)
    q = await db.execute(stmt)
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
            "file_size_kb": p.file_size_kb,
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
    except Exception as e:
        logger.error("Failed to enqueue export_project_zip job: {}", e)
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
