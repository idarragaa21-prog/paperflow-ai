from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.matrix import MatrixVersion
from app.models.user import User
from app.services.meta_runs_service import derive_dataset, list_derived_datasets, serialize_dataset
from app.services.permissions import require_project_access

router = APIRouter(prefix="/datasets", tags=["datasets"])


class DeriveDatasetRequest(BaseModel):
    project_id: UUID
    preset: str
    matrix_version_id: UUID | None = None
    title: str | None = None
    build_params: dict | None = None


@router.post("/derive")
async def derive_dataset_endpoint(
    payload: DeriveDatasetRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await require_project_access(db, project_id=payload.project_id, user=user, required_role="editor")

    matrix_version: MatrixVersion | None
    if payload.matrix_version_id:
        matrix_version = await db.get(MatrixVersion, payload.matrix_version_id)
        if matrix_version is None or matrix_version.project_id != payload.project_id:
            raise HTTPException(status_code=404, detail="Matrix version not found")
    else:
        stmt = (
            select(MatrixVersion)
            .where(MatrixVersion.project_id == payload.project_id)
            .where(MatrixVersion.is_current == True)  # noqa: E712
            .order_by(MatrixVersion.version_number.desc())
            .limit(1)
        )
        matrix_version = (await db.execute(stmt)).scalars().first()
        if matrix_version is None:
            raise HTTPException(status_code=404, detail="No current matrix version available")

    try:
        dataset = await derive_dataset(
            db,
            project_id=payload.project_id,
            matrix_version=matrix_version,
            preset=payload.preset,
            title=payload.title,
            build_params=payload.build_params,
            user_id=user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return serialize_dataset(dataset)


@router.get("/derived")
async def list_derived(
    project_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await require_project_access(db, project_id=project_id, user=user, required_role="viewer")
    datasets = await list_derived_datasets(db, project_id=project_id)
    return [serialize_dataset(item) for item in datasets]
