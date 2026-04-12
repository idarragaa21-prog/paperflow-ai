from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.services.matrix_service import (
    build_matrix_version,
    export_matrix_version,
    get_matrix_version,
    list_matrix_versions,
    serialize_matrix_version,
)
from app.services.permissions import require_project_access

router = APIRouter(prefix="/matrix", tags=["matrix"])


class MatrixBuildRequest(BaseModel):
    project_id: UUID


@router.post("/build")
async def build_matrix(
    payload: MatrixBuildRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await require_project_access(db, project_id=payload.project_id, user=user, required_role="editor")
    version = await build_matrix_version(db, project_id=payload.project_id, user_id=user.id)
    hydrated = await get_matrix_version(db, version_id=version.id)
    if hydrated is None:
        raise HTTPException(status_code=500, detail="Matrix version created but not found")
    return serialize_matrix_version(hydrated)


@router.get("/versions")
async def get_matrix_versions(
    project_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await require_project_access(db, project_id=project_id, user=user, required_role="viewer")
    versions = await list_matrix_versions(db, project_id=project_id)
    return [
        {
            "id": str(item.id),
            "project_id": str(item.project_id),
            "version_number": item.version_number,
            "status": item.status,
            "schema_version": item.schema_version,
            "is_current": item.is_current,
            "summary": item.summary_json or {},
            "validation_summary": item.validation_summary_json or {},
            "source_signature": item.source_signature,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "updated_at": item.updated_at.isoformat() if getattr(item, "updated_at", None) else None,
        }
        for item in versions
    ]


@router.get("/{version_id}")
async def get_matrix(
    version_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    version = await get_matrix_version(db, version_id=version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Matrix version not found")
    await require_project_access(db, project_id=version.project_id, user=user, required_role="viewer")
    return serialize_matrix_version(version)


@router.get("/{version_id}/export")
async def export_matrix(
    version_id: UUID,
    format: str = Query(..., pattern="^(xlsx|csv|json|xml)$"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    version = await get_matrix_version(db, version_id=version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Matrix version not found")
    await require_project_access(db, project_id=version.project_id, user=user, required_role="viewer")
    try:
        payload, media_type, filename = export_matrix_version(version, export_format=format)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return Response(
        payload,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
