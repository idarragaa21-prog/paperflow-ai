from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.services.clinical_consults_service import (
    create_clinical_consult,
    get_consult,
    list_consults,
    serialize_consult,
)
from app.services.permissions import require_project_access

router = APIRouter(prefix="/clinical", tags=["clinical-consults"])


class ClinicalConsultCreateRequest(BaseModel):
    question: str = Field(min_length=3)
    mode: str = Field(default="standard", pattern="^(brief|standard|deep)$")
    project_id: UUID | None = None
    pico: dict | None = None
    use_project_library: bool = True
    use_pubmed: bool = True


@router.post("/consults")
async def create_consult(
    payload: ClinicalConsultCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if payload.project_id:
        await require_project_access(db, project_id=payload.project_id, user=user, required_role="viewer")

    try:
        consult = await create_clinical_consult(
            db,
            user_id=user.id,
            project_id=payload.project_id,
            question=payload.question,
            mode=payload.mode,
            pico_json=payload.pico,
            use_project_library=payload.use_project_library,
            use_pubmed=payload.use_pubmed,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return serialize_consult(consult)


@router.get("/consults")
async def get_consults(
    project_id: UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if project_id:
        await require_project_access(db, project_id=project_id, user=user, required_role="viewer")
    consults = await list_consults(db, user_id=user.id, project_id=project_id)
    return [serialize_consult(item) for item in consults]


@router.get("/consults/{consult_id}")
async def get_consult_by_id(
    consult_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    consult = await get_consult(db, consult_id=consult_id)
    if consult is None:
        raise HTTPException(status_code=404, detail="Clinical consult not found")
    if consult.project_id:
        await require_project_access(db, project_id=consult.project_id, user=user, required_role="viewer")
    elif consult.user_id != user.id:
        raise HTTPException(status_code=404, detail="Clinical consult not found")
    return serialize_consult(consult)
