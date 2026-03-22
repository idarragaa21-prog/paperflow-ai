from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.project import Project
from app.services.deep_research import generate_deep_research_report

router = APIRouter(prefix="/research", tags=["deep-research"])


class DeepResearchRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=500)
    max_papers: int = Field(default=15, ge=3, le=50)
    source_mode: str = Field(default="pubmed")   # "pubmed" | "project"
    project_id: str | None = Field(default=None)


@router.post("/deep")
async def create_deep_research(
    payload: DeepResearchRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Generate a deep research report.

    source_mode="pubmed"   → fresh PubMed search (default).
    source_mode="project"  → use papers already in the project library.
                             project_id is required in this mode.
    """
    # Validate project ownership when using project source
    if payload.source_mode == "project":
        if not payload.project_id:
            raise HTTPException(status_code=400, detail="project_id requerido cuando source_mode='project'")
        from uuid import UUID
        try:
            proj_uuid = UUID(payload.project_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="project_id inválido")
        project = await db.get(Project, proj_uuid)
        if not project or project.user_id != user.id:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    report = await generate_deep_research_report(
        query=payload.query,
        max_papers=payload.max_papers,
        source_mode=payload.source_mode,
        project_id=payload.project_id,
        db=db if payload.source_mode == "project" else None,
    )

    if report.get("status") == "error":
        raise HTTPException(status_code=422, detail=report.get("error", "Report generation failed"))

    return report
