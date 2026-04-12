from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.services.meta_runs_service import (
    get_derived_dataset,
    get_meta_run,
    list_meta_runs,
    run_meta_analysis,
    serialize_meta_run,
)
from app.services.permissions import require_project_access

router = APIRouter(prefix="/meta/runs", tags=["meta-runs"])


class MetaRunCreateRequest(BaseModel):
    project_id: UUID
    derived_dataset_id: UUID
    preset: str
    title: str | None = None
    input_params: dict | None = None


@router.post("")
async def create_meta_run(
    payload: MetaRunCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await require_project_access(db, project_id=payload.project_id, user=user, required_role="editor")
    dataset = await get_derived_dataset(db, dataset_id=payload.derived_dataset_id)
    if dataset is None or dataset.project_id != payload.project_id:
        raise HTTPException(status_code=404, detail="Derived dataset not found")
    try:
        run = await run_meta_analysis(
            db,
            project_id=payload.project_id,
            dataset=dataset,
            preset=payload.preset,
            title=payload.title,
            input_params=payload.input_params,
            user_id=user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return serialize_meta_run(run)


@router.get("")
async def get_meta_runs(
    project_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await require_project_access(db, project_id=project_id, user=user, required_role="viewer")
    runs = await list_meta_runs(db, project_id=project_id)
    return [serialize_meta_run(item) for item in runs]


@router.get("/{run_id}")
async def get_meta_run_by_id(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    run = await get_meta_run(db, run_id=run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Meta run not found")
    await require_project_access(db, project_id=run.project_id, user=user, required_role="viewer")
    return serialize_meta_run(run)


@router.get("/{run_id}/artifacts")
async def get_meta_run_artifacts(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    run = await get_meta_run(db, run_id=run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Meta run not found")
    await require_project_access(db, project_id=run.project_id, user=user, required_role="viewer")
    payload = serialize_meta_run(run)
    return payload["artifacts"]
