from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.storage import storage_manager
from app.middleware.rate_limit import limiter
from app.models.job import Job
from app.models.paper import Paper
from app.models.project import Project
from app.models.user import User
from app.models.meta_extractor import (
    ExtractedEffectSize,
    ExtractedRiskOfBias,
    ExtractedStudy,
    MetaExtractionBatch,
    MetaExtractionItem,
)
from app.services.jobs import get_job_queue
from app.models.meta_export import MetaExport
from app.schemas.meta import BatchEffectPatchRequest, MetaExportListRow, MetaExportRequest
from app.core.logger import logger
from app.services.permissions import require_project_access

router = APIRouter(prefix="/meta", tags=["meta"])


def _infer_export_format(filename: str) -> str:
    lower_name = filename.lower()
    if lower_name.endswith(".xlsx"):
        return "xlsx"
    if lower_name.endswith(".zip"):
        return "csv_bundle"
    return Path(lower_name).suffix.lstrip(".") or "unknown"


@dataclass
class BatchCreateParams:
    project_id: UUID = Form(...)
    title: str | None = Form(default=None)
    files: list[UploadFile] = File(...)


def _export_media_type(filename: str) -> str:
    export_format = _infer_export_format(filename)
    if export_format == "xlsx":
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    if export_format == "csv_bundle":
        return "application/zip"
    return "application/octet-stream"


async def _require_project_role(
    db: AsyncSession,
    project_id: UUID,
    user: User,
    *,
    required_role: str = "viewer",
) -> Project:
    project, _ = await require_project_access(db, project_id=project_id, user=user, required_role=required_role)
    return project


@router.post("/batches")
@limiter.limit("3/minute")
async def create_batch(
    request: Request,
    params: BatchCreateParams = Depends(),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _require_project_role(db, params.project_id, user, required_role="editor")

    batch = MetaExtractionBatch(user_id=user.id, project_id=params.project_id, title=params.title, status="created")
    db.add(batch)
    await db.commit()
    await db.refresh(batch)

    # Pre-calculate hashes and check validity to prevent N+1 query and memory issues
    file_hashes = []
    for f in params.files:
        content = await f.read()
        if not storage_manager.validate_pdf(content):
            raise HTTPException(status_code=400, detail=f"Archivo no es un PDF válido: {f.filename}")
        file_hashes.append(storage_manager._calculate_hash(content))
        await f.seek(0)

    # Fetch existing papers in a single query
    existing_papers = {}
    if file_hashes:
        existing_q = await db.execute(
            select(Paper).where(Paper.project_id == params.project_id).where(Paper.content_hash.in_(file_hashes))
        )
        existing_papers = {p.content_hash: p for p in existing_q.scalars().all()}

    # Save PDFs as Papers and create items
    created_items: list[str] = []
    for i, f in enumerate(params.files):
        content_hash = file_hashes[i]
        paper = existing_papers.get(content_hash)

        if not paper:
            content = await f.read()
            saved = await storage_manager.save_paper_bytes(data=content, project_id=params.project_id, suggested_filename=f.filename)
            paper = Paper(
                project_id=params.project_id,
                search_result_id=None,
                title=f.filename or "Paper",
                authors=None,
                doi=None,
                pmid=None,
                pmcid=None,
                filename=saved["filename"],
                file_path=saved["file_path"],
                file_size_kb=saved["size_kb"],
                content_hash=saved["content_hash"],
                downloaded_at=datetime.now(timezone.utc),
            )
            db.add(paper)
            await db.commit()
            await db.refresh(paper)
            existing_papers[content_hash] = paper  # Update dict for intra-batch duplicates

        item = MetaExtractionItem(batch_id=batch.id, paper_id=paper.id, status="queued")
        db.add(item)
        await db.commit()
        await db.refresh(item)
        created_items.append(str(item.id))

    # Enqueue batch job
    job_record = Job(
        user_id=user.id,
        job_type="meta_extract_batch",
        status="queued",
        input_params={"batch_id": str(batch.id)},
        result={},
        progress_percent=0,
    )
    db.add(job_record)
    await db.commit()
    await db.refresh(job_record)

    try:
        from app.workers.tasks_meta import meta_extract_batch_job

        q = get_job_queue()
        rq_job = q.enqueue(meta_extract_batch_job, args=(str(job_record.id), str(batch.id)), job_timeout="60m")
    except Exception as e:
        logger.error("Failed to enqueue meta_extract_batch job: {}", e)
        job_record.status = "failed"
        job_record.error_message = "El sistema de procesamiento no está disponible en este momento. Por favor, intenta de nuevo más tarde."
        await db.commit()
        raise HTTPException(status_code=503, detail="El sistema de procesamiento no está disponible en este momento. Por favor, intenta de nuevo más tarde.")

    job_record.result = {"rq_job_id": rq_job.id}
    await db.commit()

    return {"batch_id": str(batch.id), "job_id": str(job_record.id), "item_ids": created_items}


@router.get("/batches")
async def list_batches(
    project_id: UUID,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _require_project_role(db, project_id, user, required_role="viewer")
    q = await db.execute(
        select(MetaExtractionBatch)
        .where(MetaExtractionBatch.project_id == project_id)
        .order_by(MetaExtractionBatch.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    items = q.scalars().all()
    return [
        {"id": str(b.id), "title": b.title, "status": b.status, "created_at": b.created_at.isoformat()}
        for b in items
    ]


@router.get("/batches/{batch_id}/items")
async def list_batch_items(
    batch_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    batch = await db.get(MetaExtractionBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    await _require_project_role(db, batch.project_id, user, required_role="viewer")

    q = await db.execute(
        select(MetaExtractionItem, Paper)
        .join(Paper, Paper.id == MetaExtractionItem.paper_id)
        .where(MetaExtractionItem.batch_id == batch.id)
        .order_by(MetaExtractionItem.created_at.asc())
    )
    rows = q.all()
    return [
        {
            "id": str(it.id),
            "paper_id": str(it.paper_id),
            "paper_title": p.title,
            "paper_filename": p.filename,
            "status": it.status,
            "error_message": it.error_message,
            "result_summary": it.result_summary,
            "created_at": it.created_at.isoformat() if it.created_at else None,
            "updated_at": it.updated_at.isoformat() if it.updated_at else None,
        }
        for (it, p) in rows
    ]


@router.post("/items/{item_id}/retry")
@limiter.limit("10/minute")
async def retry_item(
    request: Request,
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    item = await db.get(MetaExtractionItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    batch = await db.get(MetaExtractionBatch, item.batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Item not found")
    await _require_project_role(db, batch.project_id, user, required_role="editor")

    # ensure paper belongs to project
    paper = await db.get(Paper, item.paper_id)
    if not paper or paper.project_id != batch.project_id:
        raise HTTPException(status_code=400, detail="Paper no pertenece al proyecto")

    # create job record
    job_record = Job(
        user_id=user.id,
        job_type="meta_extract_paper",
        status="queued",
        input_params={"batch_id": str(batch.id), "item_id": str(item.id), "paper_id": str(item.paper_id)},
        result={},
        progress_percent=0,
    )
    db.add(job_record)
    await db.commit()
    await db.refresh(job_record)

    try:
        from app.workers.tasks_meta import meta_extract_paper_job
        from app.core.redis_conn import redis_available

        if not redis_available():
            raise RuntimeError("Job queue unavailable. Redis is required.")

        q = get_job_queue()
        rq_job = q.enqueue(meta_extract_paper_job, args=(str(job_record.id), str(batch.id), str(item.id), str(item.paper_id)), job_timeout="30m")
    except Exception as e:
        logger.error("Failed to enqueue meta_extract_paper retry job for item {}: {}", item_id, e)
        job_record.status = "failed"
        job_record.error_message = "El sistema de procesamiento no está disponible en este momento. Por favor, intenta de nuevo más tarde."
        await db.commit()
        raise HTTPException(status_code=503, detail="El sistema de procesamiento no está disponible en este momento. Por favor, intenta de nuevo más tarde.")

    job_record.result = {"rq_job_id": rq_job.id}
    item.status = "queued"
    item.error_message = None

    # Move batch back to processing if user retries an item
    try:
        batch.status = "processing"
    except Exception as e:
        logger.warning("Failed to update batch status to processing: {}", e)

    await db.commit()

    return {"job_id": str(job_record.id)}


@router.delete("/batches/{batch_id}")
@limiter.limit("5/minute")
async def delete_batch(
    request: Request,
    batch_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    batch = await db.get(MetaExtractionBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    await _require_project_role(db, batch.project_id, user, required_role="editor")

    await db.delete(batch)
    await db.commit()
    return {"ok": True}


@router.post("/studies/{study_id}/re-extract")
@limiter.limit("5/minute")
async def reextract_study(
    request: Request,
    study_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    study = await db.get(ExtractedStudy, study_id)
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")

    project = await _require_project_role(db, study.project_id, user, required_role="editor")

    # create a synthetic item if not in a batch
    batch_id = study.batch_id
    if not batch_id:
        # create a one-off batch
        batch = MetaExtractionBatch(user_id=user.id, project_id=project.id, title=f"Re-extract {study_id}", status="created")
        db.add(batch)
        await db.commit()
        await db.refresh(batch)
        batch_id = batch.id

    item = MetaExtractionItem(batch_id=batch_id, paper_id=study.paper_id, status="queued")
    db.add(item)
    await db.commit()
    await db.refresh(item)

    # enqueue as a paper extract
    job_record = Job(
        user_id=user.id,
        job_type="meta_extract_paper",
        status="queued",
        input_params={"batch_id": str(batch_id), "item_id": str(item.id), "paper_id": str(item.paper_id)},
        result={},
        progress_percent=0,
    )
    db.add(job_record)
    await db.commit()
    await db.refresh(job_record)

    try:
        from app.workers.tasks_meta import meta_extract_paper_job
        from app.core.redis_conn import redis_available

        if not redis_available():
            raise RuntimeError("Job queue unavailable. Redis is required.")

        q = get_job_queue()
        rq_job = q.enqueue(meta_extract_paper_job, args=(str(job_record.id), str(batch_id), str(item.id), str(item.paper_id)), job_timeout="30m")
    except Exception as e:
        logger.error("Failed to enqueue meta_extract_paper re-extract job for study {}: {}", study_id, e)
        job_record.status = "failed"
        job_record.error_message = "El sistema de procesamiento no está disponible en este momento. Por favor, intenta de nuevo más tarde."
        await db.commit()
        raise HTTPException(status_code=503, detail="El sistema de procesamiento no está disponible en este momento. Por favor, intenta de nuevo más tarde.")

    job_record.result = {"rq_job_id": rq_job.id}
    await db.commit()

    return {"job_id": str(job_record.id)}


@router.get("/studies/{study_id}/versions")
async def list_study_versions(
    study_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    study = await db.get(ExtractedStudy, study_id)
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    await _require_project_role(db, study.project_id, user, required_role="viewer")

    q = await db.execute(
        select(ExtractedStudy).where(ExtractedStudy.paper_id == study.paper_id).order_by(ExtractedStudy.version.desc())
    )
    versions = q.scalars().all()
    return [
        {
            "id": str(s.id),
            "version": s.version,
            "is_current": s.is_current,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in versions
    ]


@router.get("/studies/{study_id}/effects")
async def list_effects(
    study_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    study = await db.get(ExtractedStudy, study_id)
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    await _require_project_role(db, study.project_id, user, required_role="viewer")

    q = await db.execute(select(ExtractedEffectSize).where(ExtractedEffectSize.extracted_study_id == study.id))
    eff = q.scalars().all()
    return [{"id": str(e.id), "outcome_name": e.outcome_name, "effect_measure": e.effect_measure} for e in eff]


@router.post("/studies/{study_id}/effects")
@limiter.limit("30/minute")
async def add_effect(
    request: Request,
    study_id: UUID,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    study = await db.get(ExtractedStudy, study_id)
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    await _require_project_role(db, study.project_id, user, required_role="editor")

    required = ["outcome_name", "arm_intervention", "arm_control"]
    for r in required:
        if not payload.get(r):
            raise HTTPException(status_code=400, detail=f"{r} requerido")

    eff = ExtractedEffectSize(
        extracted_study_id=study.id,
        outcome_name=str(payload.get("outcome_name")),
        timepoint=payload.get("timepoint"),
        arm_intervention=str(payload.get("arm_intervention")),
        arm_control=str(payload.get("arm_control")),
        effect_measure=str(payload.get("effect_measure") or "OR"),
        outcome_type=str(payload.get("outcome_type") or "binary"),
        outcome_unit=payload.get("outcome_unit"),
        comparator_type=payload.get("comparator_type"),
        effect_direction=payload.get("effect_direction"),
        a_events=payload.get("a_events"),
        b_non_events=payload.get("b_non_events"),
        c_events=payload.get("c_events"),
        d_non_events=payload.get("d_non_events"),
        events_total=payload.get("events_total"),
        total_n=payload.get("total_n"),
        or_value=payload.get("or_value"),
        log_or=payload.get("log_or"),
        se_log_or=payload.get("se_log_or"),
        effect_value=payload.get("effect_value"),
        effect_se=payload.get("effect_se"),
        weight=payload.get("weight"),
        ci_lower_95=payload.get("ci_lower_95"),
        ci_upper_95=payload.get("ci_upper_95"),
        adjusted_or=payload.get("adjusted_or"),
        adjusted_rr=payload.get("adjusted_rr"),
        adjusted_hr=payload.get("adjusted_hr"),
        n_intervention=payload.get("n_intervention"),
        n_control=payload.get("n_control"),
        mean_intervention=payload.get("mean_intervention"),
        sd_intervention=payload.get("sd_intervention"),
        mean_control=payload.get("mean_control"),
        sd_control=payload.get("sd_control"),
        median_intervention=payload.get("median_intervention"),
        iqr_intervention=payload.get("iqr_intervention"),
        median_control=payload.get("median_control"),
        iqr_control=payload.get("iqr_control"),
        followup_time=payload.get("followup_time"),
        followup_unit=payload.get("followup_unit"),
        person_time_intervention=payload.get("person_time_intervention"),
        person_time_control=payload.get("person_time_control"),
        tp=payload.get("tp"),
        fp=payload.get("fp"),
        fn=payload.get("fn"),
        tn=payload.get("tn"),
        sensitivity_value=payload.get("sensitivity_value"),
        specificity_value=payload.get("specificity_value"),
        subgroup_label=payload.get("subgroup_label"),
        subgroup_level=payload.get("subgroup_level"),
        subgroup_order=payload.get("subgroup_order"),
        sensitivity_flag=bool(payload.get("sensitivity_flag") or False),
        sensitivity_reason=payload.get("sensitivity_reason"),
        analysis_population=payload.get("analysis_population"),
        model_type=payload.get("model_type"),
        covariates_json=payload.get("covariates_json"),
        manually_edited=True,
        edited_at=datetime.now(timezone.utc),
        comments=payload.get("comments"),
    )
    db.add(eff)
    await db.commit()
    await db.refresh(eff)
    return {"id": str(eff.id)}


@router.delete("/studies/{study_id}/effects/{effect_id}")
@limiter.limit("30/minute")
async def delete_effect(
    request: Request,
    study_id: UUID,
    effect_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    study = await db.get(ExtractedStudy, study_id)
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    await _require_project_role(db, study.project_id, user, required_role="editor")

    eff = await db.get(ExtractedEffectSize, effect_id)
    if not eff or eff.extracted_study_id != study.id:
        raise HTTPException(status_code=404, detail="Effect not found")

    await db.delete(eff)
    await db.commit()
    return {"ok": True}


@router.get("/studies/{study_id}/rob")
async def list_rob(
    study_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    study = await db.get(ExtractedStudy, study_id)
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    await _require_project_role(db, study.project_id, user, required_role="viewer")

    q = await db.execute(select(ExtractedRiskOfBias).where(ExtractedRiskOfBias.extracted_study_id == study.id))
    rob = q.scalars().all()
    return [{"id": str(r.id), "tool": r.tool, "domain": r.domain, "judgement": r.judgement} for r in rob]


@router.post("/studies/{study_id}/rob")
@limiter.limit("30/minute")
async def add_rob(
    request: Request,
    study_id: UUID,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    study = await db.get(ExtractedStudy, study_id)
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    await _require_project_role(db, study.project_id, user, required_role="editor")

    if not payload.get("domain"):
        raise HTTPException(status_code=400, detail="domain requerido")

    rob = ExtractedRiskOfBias(
        extracted_study_id=study.id,
        tool=str(payload.get("tool") or "ROB2"),
        domain=str(payload.get("domain")),
        judgement=str(payload.get("judgement") or "unclear"),
        support_text=payload.get("support_text"),
        manually_edited=True,
        edited_at=datetime.now(timezone.utc),
    )
    db.add(rob)
    await db.commit()
    await db.refresh(rob)
    return {"id": str(rob.id)}


@router.get("/batches/{batch_id}")
async def get_batch(
    batch_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    batch = await db.get(MetaExtractionBatch, batch_id)
    if not batch or batch.user_id != user.id:
        raise HTTPException(status_code=404, detail="Batch not found")

    q = await db.execute(select(MetaExtractionItem).where(MetaExtractionItem.batch_id == batch.id))
    items = q.scalars().all()
    return {
        "id": str(batch.id),
        "project_id": str(batch.project_id),
        "title": batch.title,
        "status": batch.status,
        "created_at": batch.created_at.isoformat(),
        "items": [
            {
                "id": str(it.id),
                "paper_id": str(it.paper_id),
                "status": it.status,
                "error_message": it.error_message,
                "result_summary": it.result_summary,
            }
            for it in items
        ],
    }


@router.get("/studies")
async def list_studies(
    project_id: UUID,
    batch_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _require_project_role(db, project_id, user, required_role="viewer")

    from sqlalchemy import exists

    rob_auto = (
        exists(
            select(ExtractedRiskOfBias.id)
            .where(ExtractedRiskOfBias.extracted_study_id == ExtractedStudy.id)
            .where(ExtractedRiskOfBias.auto_generated == True)  # noqa
        ).label("rob_auto_generated")
    )

    stmt = (
        select(ExtractedStudy, Paper, rob_auto)
        .join(Paper, Paper.id == ExtractedStudy.paper_id)
        .where(ExtractedStudy.project_id == project_id)
        .where(ExtractedStudy.is_current == True)  # noqa
    )
    if batch_id:
        stmt = stmt.where(ExtractedStudy.batch_id == batch_id)
    stmt = stmt.order_by(ExtractedStudy.created_at.desc())

    q = await db.execute(stmt)
    rows = q.all()
    return [
        {
            "id": str(s.id),
            "paper_id": str(s.paper_id),
            "paper_title": p.title,
            "paper_filename": p.filename,
            "batch_id": str(s.batch_id) if s.batch_id else None,
            "version": s.version,
            "extraction_confidence": s.extraction_confidence,
            "rob_auto_generated": bool(rob_auto_generated),
            "created_at": s.created_at.isoformat(),
        }
        for (s, p, rob_auto_generated) in rows
    ]


@router.get("/studies/{study_id}")
async def get_study(
    study_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    study = await db.get(ExtractedStudy, study_id)
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    project = await _require_project_role(db, study.project_id, user, required_role="viewer")

    q1 = await db.execute(select(ExtractedEffectSize).where(ExtractedEffectSize.extracted_study_id == study.id))
    eff = q1.scalars().all()
    q2 = await db.execute(select(ExtractedRiskOfBias).where(ExtractedRiskOfBias.extracted_study_id == study.id))
    rob = q2.scalars().all()

    return {
        "id": str(study.id),
        "project_id": str(study.project_id),
        "paper_id": str(study.paper_id),
        "batch_id": str(study.batch_id) if study.batch_id else None,
        "version": study.version,
        "is_current": study.is_current,
        "study_json": study.study_json,
        "extraction_confidence": study.extraction_confidence,
        "effects": [
            {
                "id": str(e.id),
                "outcome_name": e.outcome_name,
                "timepoint": e.timepoint,
                "arm_intervention": e.arm_intervention,
                "arm_control": e.arm_control,
                "effect_measure": e.effect_measure,
                "outcome_type": e.outcome_type,
                "outcome_unit": e.outcome_unit,
                "comparator_type": e.comparator_type,
                "effect_direction": e.effect_direction,
                "a_events": e.a_events,
                "b_non_events": e.b_non_events,
                "c_events": e.c_events,
                "d_non_events": e.d_non_events,
                "events_total": e.events_total,
                "total_n": e.total_n,
                "or_value": e.or_value,
                "log_or": e.log_or,
                "se_log_or": e.se_log_or,
                "effect_value": e.effect_value,
                "effect_se": e.effect_se,
                "weight": e.weight,
                "ci_lower_95": e.ci_lower_95,
                "ci_upper_95": e.ci_upper_95,
                "adjusted_or": e.adjusted_or,
                "adjusted_rr": e.adjusted_rr,
                "adjusted_hr": e.adjusted_hr,
                "n_intervention": e.n_intervention,
                "n_control": e.n_control,
                "mean_intervention": e.mean_intervention,
                "sd_intervention": e.sd_intervention,
                "mean_control": e.mean_control,
                "sd_control": e.sd_control,
                "median_intervention": e.median_intervention,
                "iqr_intervention": e.iqr_intervention,
                "median_control": e.median_control,
                "iqr_control": e.iqr_control,
                "followup_time": e.followup_time,
                "followup_unit": e.followup_unit,
                "person_time_intervention": e.person_time_intervention,
                "person_time_control": e.person_time_control,
                "tp": e.tp,
                "fp": e.fp,
                "fn": e.fn,
                "tn": e.tn,
                "sensitivity_value": e.sensitivity_value,
                "specificity_value": e.specificity_value,
                "subgroup_label": e.subgroup_label,
                "subgroup_level": e.subgroup_level,
                "subgroup_order": e.subgroup_order,
                "sensitivity_flag": e.sensitivity_flag,
                "sensitivity_reason": e.sensitivity_reason,
                "analysis_population": e.analysis_population,
                "model_type": e.model_type,
                "covariates_json": e.covariates_json,
                "adjustment_variables": e.adjustment_variables,
                "is_adjusted": e.is_adjusted,
                "raw_extracted_value": e.raw_extracted_value,
                "source_type": e.source_type,
                "source_page": e.source_page,
                "source_locator": e.source_locator,
                "confidence": e.confidence,
                "comments": e.comments,
                "manually_edited": e.manually_edited,
                "edited_at": e.edited_at.isoformat() if e.edited_at else None,
            }
            for e in eff
        ],
        "risk_of_bias": [
            {
                "id": str(r.id),
                "tool": r.tool,
                "domain": r.domain,
                "judgement": r.judgement,
                "support_text": r.support_text,
                "manually_edited": r.manually_edited,
                "edited_at": r.edited_at.isoformat() if r.edited_at else None,
                "auto_generated": getattr(r, "auto_generated", False),
            }
            for r in rob
        ],
    }


@router.patch("/studies/{study_id}")
@limiter.limit("20/minute")
async def patch_study(
    request: Request,
    study_id: UUID,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    study = await db.get(ExtractedStudy, study_id)
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    await _require_project_role(db, study.project_id, user, required_role="editor")

    # Update only keys present (top-level) in study_json
    sj = dict(study.study_json or {})
    for k, v in payload.items():
        sj[k] = v
    study.study_json = sj
    study.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return {"ok": True}


@dataclass
class PatchEffectPathParams:
    study_id: UUID
    effect_id: UUID


@router.patch("/studies/{study_id}/effects/{effect_id}")
@limiter.limit("30/minute")
async def patch_effect(
    request: Request,
    payload: dict,
    path_params: PatchEffectPathParams = Depends(),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    study = await db.get(ExtractedStudy, path_params.study_id)
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    await _require_project_role(db, study.project_id, user, required_role="editor")

    eff = await db.get(ExtractedEffectSize, path_params.effect_id)
    if not eff or eff.extracted_study_id != study.id:
        raise HTTPException(status_code=404, detail="Effect not found")

    for k, v in payload.items():
        if hasattr(eff, k):
            setattr(eff, k, v)

    eff.manually_edited = True
    eff.edited_at = datetime.now(timezone.utc)
    await db.commit()

    return {"ok": True}


@router.patch("/studies/{study_id}/effects")
@limiter.limit("30/minute")
async def patch_effects_batch(
    request: Request,
    study_id: UUID,
    payload: BatchEffectPatchRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Batch PATCH for effect sizes.

    Used by EffectSizesGrid PRO to save many inline edits in one request.
    """

    study = await db.get(ExtractedStudy, study_id)
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    await _require_project_role(db, study.project_id, user, required_role="editor")

    updated = 0
    # Optimize N+1 query: fetch all affected effects in one query
    upd_ids = [upd.id for upd in payload.updates]
    if upd_ids:
        effs_q = await db.execute(
            select(ExtractedEffectSize).where(ExtractedEffectSize.id.in_(upd_ids))
        )
        effs_dict = {e.id: e for e in effs_q.scalars().all()}
    else:
        effs_dict = {}

    for upd in payload.updates:
        eff = effs_dict.get(upd.id)
        if not eff or eff.extracted_study_id != study.id:
            raise HTTPException(status_code=404, detail=f"Effect not found: {upd.id}")

        patch_dict = upd.patch.model_dump(exclude_unset=True)

        # Validate 2x2 counts
        for ck in (
            "a_events",
            "b_non_events",
            "c_events",
            "d_non_events",
            "events_total",
            "total_n",
            "n_intervention",
            "n_control",
            "tp",
            "fp",
            "fn",
            "tn",
        ):
            if ck in patch_dict and patch_dict[ck] is not None:
                try:
                    if int(patch_dict[ck]) < 0:
                        raise HTTPException(status_code=422, detail=f"{ck} no puede ser negativo")
                except ValueError:
                    raise HTTPException(status_code=422, detail=f"{ck} debe ser un entero")

        for k, v in patch_dict.items():
            if hasattr(eff, k):
                setattr(eff, k, v)

        eff.manually_edited = True
        eff.edited_at = datetime.now(timezone.utc)
        updated += 1

    await db.commit()

    return {"ok": True, "updated": updated}


@router.get("/exports", response_model=list[MetaExportListRow])
async def list_exports(
    project_id: UUID,
    batch_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _require_project_role(db, project_id, user, required_role="viewer")

    stmt = select(MetaExport).where(MetaExport.project_id == project_id)
    if batch_id:
        stmt = stmt.where(MetaExport.batch_id == batch_id)
    stmt = stmt.order_by(MetaExport.created_at.desc())

    q = await db.execute(stmt)
    exports = q.scalars().all()
    return [
        MetaExportListRow(
            id=e.id,
            project_id=e.project_id,
            batch_id=e.batch_id,
            filename=e.filename,
            format=_infer_export_format(e.filename),
            created_at=e.created_at,
        )
        for e in exports
    ]


@router.post("/export")
@limiter.limit("3/minute")
async def export_meta_dataset(
    request: Request,
    payload: MetaExportRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project_uuid = payload.project_id
    await _require_project_role(db, project_uuid, user, required_role="editor")

    batch_uuid = payload.batch_id
    export_format = payload.format

    job_record = Job(
        user_id=user.id,
        job_type=f"meta_export_{export_format}",
        status="queued",
        input_params={"project_id": str(project_uuid), "batch_id": str(batch_uuid) if batch_uuid else None, "format": export_format},
        result={},
        progress_percent=0,
    )
    db.add(job_record)
    await db.commit()
    await db.refresh(job_record)

    try:
        from app.workers.tasks_meta import meta_export_job

        q = get_job_queue()
        rq_job = q.enqueue(
            meta_export_job,
            args=(str(job_record.id), str(project_uuid), str(batch_uuid) if batch_uuid else "", export_format),
            job_timeout="20m",
        )
    except Exception as e:
        logger.error("Failed to enqueue meta_export job: {}", e)
        job_record.status = "failed"
        job_record.error_message = "El sistema de procesamiento no está disponible en este momento. Por favor, intenta de nuevo más tarde."
        await db.commit()
        raise HTTPException(status_code=503, detail="El sistema de procesamiento no está disponible en este momento. Por favor, intenta de nuevo más tarde.")

    job_record.result = {"rq_job_id": rq_job.id}
    await db.commit()

    return {"job_id": str(job_record.id)}


@router.get("/exports/{export_id}/download")
async def download_export(
    export_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    export = await db.get(MetaExport, export_id)
    if not export:
        raise HTTPException(status_code=404, detail="Export not found")

    await _require_project_role(db, export.project_id, user, required_role="viewer")

    abs_path = (storage_manager.base_dir / export.file_path).resolve()
    try:
        abs_path.relative_to(storage_manager.base_dir)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid file path")

    if not abs_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(abs_path, filename=export.filename, media_type=_export_media_type(export.filename))


@dataclass
class RobPathParams:
    study_id: UUID
    rob_id: UUID


@router.patch("/studies/{study_id}/rob/{rob_id}")
@limiter.limit("30/minute")
async def patch_rob(
    request: Request,
    payload: dict,
    path_params: RobPathParams = Depends(),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    study = await db.get(ExtractedStudy, path_params.study_id)
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    await _require_project_role(db, study.project_id, user, required_role="editor")

    rob = await db.get(ExtractedRiskOfBias, path_params.rob_id)
    if not rob or rob.extracted_study_id != study.id:
        raise HTTPException(status_code=404, detail="ROB not found")

    for k, v in payload.items():
        if hasattr(rob, k):
            setattr(rob, k, v)

    rob.manually_edited = True
    rob.edited_at = datetime.now(timezone.utc)
    await db.commit()

    return {"ok": True}
