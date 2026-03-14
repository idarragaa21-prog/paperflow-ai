from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db
from app.models.job import Job
from app.models.analytics import AnalysisRun, Dataset
from app.models.user import User
from app.schemas.analysis import AnalysisRunCreate, AnalysisRunResponse, DatasetCreate, DatasetResponse
from app.services.audit import log_audit
from app.services.jobs import enqueue_with_retry
from app.services.permissions import require_project_access
from app.services.analysis_service import create_analysis_run_record, create_dataset, export_analysis_run

router = APIRouter(tags=["analysis"])


def _dataset_to_response(dataset: Dataset) -> DatasetResponse:
    return DatasetResponse(
        id=dataset.id,
        project_id=dataset.project_id,
        title=dataset.title,
        description=dataset.description,
        source_type=dataset.source_type,
        row_count=dataset.row_count,
        column_count=dataset.column_count,
        columns=[
            {
                "name": column.name,
                "data_type": column.data_type,
                "position": column.position,
                "is_nullable": column.is_nullable,
                "summary_json": column.summary_json,
            }
            for column in dataset.columns
        ],
    )


def _analysis_to_response(run: AnalysisRun) -> AnalysisRunResponse:
    return AnalysisRunResponse(
        id=run.id,
        project_id=run.project_id,
        dataset_id=run.dataset_id,
        title=run.title,
        analysis_type=run.analysis_type,
        status=run.status,
        input_params=run.input_params,
        runtime_metadata=run.runtime_metadata,
        script_text=run.script_text,
        warnings=run.warnings or [],
        result_summary=run.result_summary,
        engine_version=run.engine_version,
        artifact_manifest=(run.runtime_metadata or {}).get("artifact_manifest", []),
        artifacts=[
            {
                "id": artifact.id,
                "artifact_type": artifact.artifact_type,
                "filename": artifact.filename,
                "file_path": artifact.file_path,
                "mime_type": artifact.mime_type,
                "metadata_json": artifact.metadata_json,
            }
            for artifact in run.artifacts
        ],
    )


@router.post("/datasets", response_model=DatasetResponse)
async def create_dataset_endpoint(
    payload: DatasetCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await require_project_access(db, project_id=payload.project_id, user=user, required_role="editor")
    try:
        dataset = await create_dataset(
            db,
            project_id=payload.project_id,
            title=payload.title,
            description=payload.description,
            rows=payload.rows,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _dataset_to_response(dataset)


@router.get("/datasets", response_model=list[DatasetResponse])
async def list_datasets(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await require_project_access(db, project_id=project_id, user=user, required_role="viewer")
    stmt = select(Dataset).where(Dataset.project_id == project_id).options(selectinload(Dataset.columns)).order_by(Dataset.created_at.desc())
    result = await db.execute(stmt)
    return [_dataset_to_response(item) for item in result.scalars().all()]


@router.post("/analysis-runs", response_model=AnalysisRunResponse)
async def create_analysis_run_endpoint(
    request: Request,
    payload: AnalysisRunCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await require_project_access(db, project_id=payload.project_id, user=user, required_role="editor")
    dataset = await db.get(Dataset, payload.dataset_id) if payload.dataset_id else None
    if payload.dataset_id and (dataset is None or dataset.project_id != payload.project_id):
        raise HTTPException(status_code=404, detail="Dataset not found")
    try:
        run = await create_analysis_run_record(
            db,
            project_id=payload.project_id,
            dataset=dataset,
            title=payload.title,
            analysis_type=payload.analysis_type,
            input_params=payload.input_params,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    job_record = Job(
        user_id=user.id,
        job_type="analysis_run",
        status="queued",
        input_params={"analysis_run_id": str(run.id)},
        result={"analysis_run_id": str(run.id)},
        progress_percent=0,
        queue_name="analysis",
    )
    db.add(job_record)
    await db.commit()
    await db.refresh(job_record)

    try:
        from app.workers.tasks import analysis_run_job

        rq_job_id = enqueue_with_retry("analysis", analysis_run_job, args=(str(job_record.id), str(run.id)), job_timeout="60m")
    except Exception as exc:
        job_record.status = "failed"
        job_record.error_message = f"Analysis queue unavailable: {exc}"
        run.status = "failed"
        run.warnings = [job_record.error_message]
        await db.commit()
        raise HTTPException(status_code=503, detail="Could not enqueue analysis run")

    job_record.result = {**(job_record.result or {}), "rq_job_id": rq_job_id}
    run.runtime_metadata = {**(run.runtime_metadata or {}), "job_id": str(job_record.id)}
    await db.commit()
    refreshed = await db.execute(select(AnalysisRun).where(AnalysisRun.id == run.id).options(selectinload(AnalysisRun.artifacts)))
    run = refreshed.scalars().first()
    await log_audit(
        db,
        user=user,
        action="create",
        entity_type="analysis_run",
        entity_id=run.id,
        details={"project_id": str(run.project_id), "analysis_type": run.analysis_type, "job_id": str(job_record.id)},
        request=request,
    )
    return _analysis_to_response(run)


@router.get("/analysis-runs", response_model=list[AnalysisRunResponse])
async def list_analysis_runs(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await require_project_access(db, project_id=project_id, user=user, required_role="viewer")
    stmt = (
        select(AnalysisRun)
        .where(AnalysisRun.project_id == project_id)
        .options(selectinload(AnalysisRun.artifacts))
        .order_by(AnalysisRun.created_at.desc())
    )
    result = await db.execute(stmt)
    return [_analysis_to_response(item) for item in result.scalars().all()]


@router.get("/analysis-runs/{run_id}", response_model=AnalysisRunResponse)
async def get_analysis_run(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(AnalysisRun).where(AnalysisRun.id == run_id).options(selectinload(AnalysisRun.artifacts))
    result = await db.execute(stmt)
    run = result.scalars().first()
    if run is None:
        raise HTTPException(status_code=404, detail="Analysis run not found")
    await require_project_access(db, project_id=run.project_id, user=user, required_role="viewer")
    return _analysis_to_response(run)


@router.get("/analysis-runs/{run_id}/artifacts")
async def get_analysis_run_artifacts(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(AnalysisRun).where(AnalysisRun.id == run_id).options(selectinload(AnalysisRun.artifacts))
    result = await db.execute(stmt)
    run = result.scalars().first()
    if run is None:
        raise HTTPException(status_code=404, detail="Analysis run not found")
    await require_project_access(db, project_id=run.project_id, user=user, required_role="viewer")
    return [
        {
            "id": str(artifact.id),
            "artifact_type": artifact.artifact_type,
            "filename": artifact.filename,
            "file_path": artifact.file_path,
            "mime_type": artifact.mime_type,
            "metadata_json": artifact.metadata_json,
        }
        for artifact in run.artifacts
    ]


@router.post("/analysis-runs/{run_id}/export")
async def export_analysis(
    run_id: UUID,
    format: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(AnalysisRun).where(AnalysisRun.id == run_id)
    result = await db.execute(stmt)
    run = result.scalars().first()
    if run is None:
        raise HTTPException(status_code=404, detail="Analysis run not found")
    await require_project_access(db, project_id=run.project_id, user=user, required_role="viewer")
    try:
        data, media_type, filename = await export_analysis_run(db, run=run, fmt=format)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return Response(
        data,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
