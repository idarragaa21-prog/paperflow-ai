# (no future annotations - avoids forward-ref issues)

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.storage import storage_manager
from app.middleware.rate_limit import limiter
from app.models.clinical import ClinicalSheet
from app.models.job import Job
from app.models.project import Project
from app.models.user import User
from app.services.jobs import get_job_queue

router = APIRouter(prefix="/clinical", tags=["clinical"])


def _safe_abs_path(relative_path: str):
    from pathlib import Path

    full_path = (storage_manager.base_dir / relative_path).resolve()
    try:
        full_path.relative_to(storage_manager.base_dir)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid file path")
    return full_path


@router.post("/generate")
@limiter.limit("3/minute")
async def generate_sheet(
    request: Request,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Back-compat alias for /clinical/query
    return await query_clinical(request=request, payload=payload, db=db, user=user)


@router.post("/query")
@limiter.limit("3/minute")
async def query_clinical(
    request: Request,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    topic = str(payload.get("topic") or "").strip()
    if not topic:
        raise HTTPException(status_code=400, detail="topic requerido")

    project_id = payload.get("project_id")
    project_uuid: UUID | None = UUID(str(project_id)) if project_id else None
    if project_uuid:
        proj = await db.get(Project, project_uuid)
        if not proj or proj.user_id != user.id:
            raise HTTPException(status_code=404, detail="Project not found")

    # Create ClinicalSheet record (placeholder)
    root_id = UUID(payload.get("root_id")) if payload.get("root_id") else None
    import uuid as _uuid

    root_id = root_id or _uuid.uuid4()

    sheet = ClinicalSheet(
        id=_uuid.uuid4(),
        project_id=project_uuid,
        user_id=user.id,
        topic=topic,
        input_params={**payload, "status": "generating"},
        content_markdown="_Generating…_",
        references_json=None,
        sources_used=None,
        version=1,
        is_current=True,
        llm_model=None,
        llm_usage=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    # Store root_id in input_params until we add dedicated column (safe for now)
    sheet.input_params = {**(sheet.input_params or {}), "root_id": str(root_id)}

    db.add(sheet)
    await db.commit()
    await db.refresh(sheet)

    job_record = Job(
        user_id=user.id,
        job_type="clinical_query",
        status="queued",
        input_params={"sheet_id": str(sheet.id)},
        result={"sheet_id": str(sheet.id)},
        progress_percent=0,
    )
    db.add(job_record)
    await db.commit()
    await db.refresh(job_record)

    try:
        from app.workers.tasks import clinical_query_job

        q = get_job_queue()
        rq_job = q.enqueue(clinical_query_job, args=(str(job_record.id), str(sheet.id)), job_timeout="60m")
    except Exception:
        job_record.status = "failed"
        job_record.error_message = "Job queue unavailable. Redis is required."
        await db.commit()
        raise HTTPException(status_code=503, detail="Job queue unavailable. Redis is required.")

    job_record.result = {"rq_job_id": rq_job.id, "sheet_id": str(sheet.id)}
    await db.commit()

    return {"job_id": str(job_record.id), "sheet_id": str(sheet.id)}


@router.get("/sheets")
async def list_sheets(
    project_id: UUID | None = None,
    topic: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(ClinicalSheet).where(ClinicalSheet.user_id == user.id).where(ClinicalSheet.is_current == True)  # noqa
    if project_id:
        stmt = stmt.where(ClinicalSheet.project_id == project_id)
    if topic:
        stmt = stmt.where(ClinicalSheet.topic.ilike(f"%{topic}%"))

    q = await db.execute(stmt.order_by(ClinicalSheet.updated_at.desc()))
    rows = q.scalars().all()
    return [
        {
            "id": str(s.id),
            "project_id": str(s.project_id) if s.project_id else None,
            "topic": s.topic,
            "version": s.version,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        }
        for s in rows
    ]


async def _sheet_to_dict(s: ClinicalSheet) -> dict:
    return {
        "id": str(s.id),
        "project_id": str(s.project_id) if s.project_id else None,
        "topic": s.topic,
        "version": s.version,
        "is_current": s.is_current,
        "content_markdown": s.content_markdown,
        "content_json": s.content_json,
        "format_version": s.format_version,
        "references_json": s.references_json,
        "sources_used": s.sources_used,
        "llm_model": s.llm_model,
        "llm_usage": s.llm_usage,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    }


@router.get("/sheets/{sheet_id}")
async def get_sheet(
    sheet_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    s = await db.get(ClinicalSheet, sheet_id)
    if not s or s.user_id != user.id:
        raise HTTPException(status_code=404, detail="Sheet not found")

    return await _sheet_to_dict(s)


@router.get("/sheets/{sheet_id}/versions")
async def list_sheet_versions(
    sheet_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    s = await db.get(ClinicalSheet, sheet_id)
    if not s or s.user_id != user.id:
        raise HTTPException(status_code=404, detail="Sheet not found")

    root_id = None
    try:
        root_id = (s.input_params or {}).get("root_id")
    except Exception:
        root_id = None

    if root_id:
        stmt = select(ClinicalSheet).where(ClinicalSheet.user_id == user.id).where(ClinicalSheet.input_params["root_id"].astext == str(root_id))
    else:
        stmt = select(ClinicalSheet).where(ClinicalSheet.user_id == user.id).where(ClinicalSheet.topic == s.topic)

    q = await db.execute(stmt.order_by(ClinicalSheet.version.desc()))
    rows = q.scalars().all()
    return [
        {
            "id": str(r.id),
            "version": r.version,
            "is_current": r.is_current,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.post("/sheets/{sheet_id}/update")
@limiter.limit("3/minute")
async def update_sheet(
    request: Request,
    sheet_id: UUID,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    s = await db.get(ClinicalSheet, sheet_id)
    if not s or s.user_id != user.id:
        raise HTTPException(status_code=404, detail="Sheet not found")

    # mark current false
    s.is_current = False
    s.updated_at = datetime.utcnow()

    # create new version
    import uuid as _uuid

    root_id = (s.input_params or {}).get("root_id") or str(s.id)

    new_sheet = ClinicalSheet(
        id=_uuid.uuid4(),
        project_id=s.project_id,
        user_id=user.id,
        topic=str(payload.get("topic") or s.topic),
        input_params={**(s.input_params or {}), **payload, "status": "generating", "root_id": str(root_id)},
        content_markdown="_Generating…_",
        references_json=None,
        sources_used=None,
        version=int(s.version) + 1,
        is_current=True,
        llm_model=None,
        llm_usage=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(new_sheet)
    await db.commit()
    await db.refresh(new_sheet)

    job_record = Job(
        user_id=user.id,
        job_type="clinical_query",
        status="queued",
        input_params={"sheet_id": str(new_sheet.id), "previous_sheet_id": str(s.id)},
        result={"sheet_id": str(new_sheet.id)},
        progress_percent=0,
    )
    db.add(job_record)
    await db.commit()
    await db.refresh(job_record)

    try:
        from app.workers.tasks import clinical_query_job

        q = get_job_queue()
        rq_job = q.enqueue(clinical_query_job, args=(str(job_record.id), str(new_sheet.id)), job_timeout="60m")
    except Exception:
        job_record.status = "failed"
        job_record.error_message = "Job queue unavailable. Redis is required."
        await db.commit()
        raise HTTPException(status_code=503, detail="Job queue unavailable. Redis is required.")

    job_record.result = {"rq_job_id": rq_job.id, "sheet_id": str(new_sheet.id)}
    await db.commit()

    return {"job_id": str(job_record.id), "sheet_id": str(new_sheet.id)}


@router.delete("/sheets/{sheet_id}")
@limiter.limit("10/minute")
async def delete_sheet(
    request: Request,
    sheet_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    s = await db.get(ClinicalSheet, sheet_id)
    if not s or s.user_id != user.id:
        raise HTTPException(status_code=404, detail="Sheet not found")

    # delete all versions with same root_id (best-effort)
    root_id = (s.input_params or {}).get("root_id") or str(s.id)
    stmt = select(ClinicalSheet).where(ClinicalSheet.user_id == user.id).where(ClinicalSheet.input_params["root_id"].astext == str(root_id))
    q = await db.execute(stmt)
    rows = q.scalars().all()
    for r in rows:
        await db.delete(r)
    await db.commit()
    return {"ok": True}


@router.get("/sheets/{sheet_id}/export/docx")
async def export_docx(
    sheet_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    s = await db.get(ClinicalSheet, sheet_id)
    if not s or s.user_id != user.id:
        raise HTTPException(status_code=404, detail="Sheet not found")

    # Serve cached export if available
    exp = (s.sources_used or {}).get("exports") if isinstance(s.sources_used, dict) else None
    rel = exp.get("docx") if isinstance(exp, dict) else None
    if rel:
        abs_path = _safe_abs_path(str(rel))
        if abs_path.exists():
            return FileResponse(
                abs_path,
                filename=f"clinical_{sheet_id}_v{s.version}.docx",
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )

    # Generate and persist
    from app.services.clinical.exporters import export_docx

    rel_path = export_docx(user_id=user.id, sheet_id=s.id, version=s.version, topic=s.topic, content_markdown=s.content_markdown)
    su = dict(s.sources_used or {})
    su["exports"] = {**(su.get("exports") or {}), "docx": rel_path}
    s.sources_used = su
    await db.commit()

    abs_path = _safe_abs_path(rel_path)
    return FileResponse(
        abs_path,
        filename=f"clinical_{sheet_id}_v{s.version}.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@router.get("/{sheet_id}")
async def get_sheet_alias(
    sheet_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    s = await db.get(ClinicalSheet, sheet_id)
    if not s or s.user_id != user.id:
        raise HTTPException(status_code=404, detail="Sheet not found")
    return await _sheet_to_dict(s)


@router.get("/{sheet_id}/download")
async def download_sheet(
    sheet_id: UUID,
    format: str = "pdf",
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    s = await db.get(ClinicalSheet, sheet_id)
    if not s or s.user_id != user.id:
        raise HTTPException(status_code=404, detail="Sheet not found")

    fmt = (format or "pdf").lower().strip()
    if fmt not in ("pdf", "docx"):
        raise HTTPException(status_code=400, detail="format must be pdf or docx")

    # Try cached export
    exp = (s.sources_used or {}).get("exports") if isinstance(s.sources_used, dict) else None
    rel = exp.get(fmt) if isinstance(exp, dict) else None

    if not rel:
        # Generate and persist
        from app.services.clinical.exporters import export_docx as _docx, export_pdf as _pdf

        if fmt == "docx":
            rel = _docx(user_id=user.id, sheet_id=s.id, version=s.version, topic=s.topic, content_markdown=s.content_markdown)
        else:
            rel = _pdf(user_id=user.id, sheet_id=s.id, version=s.version, topic=s.topic, content_markdown=s.content_markdown)

        su = dict(s.sources_used or {})
        su["exports"] = {**(su.get("exports") or {}), fmt: rel}
        s.sources_used = su
        await db.commit()

    abs_path = _safe_abs_path(str(rel))
    if not abs_path.exists():
        raise HTTPException(status_code=404, detail="Export file not found")

    if fmt == "docx":
        return FileResponse(
            abs_path,
            filename=f"clinical_{sheet_id}_v{s.version}.docx",
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    return FileResponse(abs_path, filename=f"clinical_{sheet_id}_v{s.version}.pdf", media_type="application/pdf")


@router.get("/sheets/{sheet_id}/export/pdf")
async def export_pdf(
    sheet_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    s = await db.get(ClinicalSheet, sheet_id)
    if not s or s.user_id != user.id:
        raise HTTPException(status_code=404, detail="Sheet not found")

    # Serve cached export if available
    exp = (s.sources_used or {}).get("exports") if isinstance(s.sources_used, dict) else None
    rel = exp.get("pdf") if isinstance(exp, dict) else None
    if rel:
        abs_path = _safe_abs_path(str(rel))
        if abs_path.exists():
            return FileResponse(abs_path, filename=f"clinical_{sheet_id}_v{s.version}.pdf", media_type="application/pdf")

    from app.services.clinical.exporters import export_pdf

    rel_path = export_pdf(user_id=user.id, sheet_id=s.id, version=s.version, topic=s.topic, content_markdown=s.content_markdown)
    su = dict(s.sources_used or {})
    su["exports"] = {**(su.get("exports") or {}), "pdf": rel_path}
    s.sources_used = su
    await db.commit()

    abs_path = _safe_abs_path(rel_path)
    return FileResponse(abs_path, filename=f"clinical_{sheet_id}_v{s.version}.pdf", media_type="application/pdf")
