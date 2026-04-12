from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db
from app.core.storage import storage_manager
from app.models.meta_run import MetaRun, MetaRunArtifact
from app.models.user import User
from app.services.permissions import require_project_access

router = APIRouter(prefix="/artifacts", tags=["artifacts"])


@router.get("/{artifact_id}/download")
async def download_artifact(
    artifact_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    artifact_stmt = (
        select(MetaRunArtifact)
        .where(MetaRunArtifact.id == artifact_id)
        .options(selectinload(MetaRunArtifact.meta_run))
    )
    artifact = (await db.execute(artifact_stmt)).scalars().first()
    if artifact:
        run: MetaRun = artifact.meta_run
        await require_project_access(db, project_id=run.project_id, user=user, required_role="viewer")
        try:
            payload = storage_manager.read_bytes(artifact.file_path)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Artifact file missing from storage") from exc
        return Response(
            payload,
            media_type=artifact.mime_type or "application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{artifact.filename}"'},
        )

    raise HTTPException(status_code=404, detail="Artifact not found")
