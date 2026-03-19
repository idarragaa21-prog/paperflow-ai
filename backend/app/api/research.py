from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.services.deep_research import generate_deep_research_report

router = APIRouter(prefix="/research", tags=["deep-research"])


class DeepResearchRequest(BaseModel):
    query: str = Field(..., min_length=5, max_length=500)
    max_papers: int = Field(default=15, ge=5, le=50)


@router.post("/deep")
async def create_deep_research(
    payload: DeepResearchRequest,
    user: User = Depends(get_current_user),
) -> dict:
    """Generate a deep research report from a query.

    Searches PubMed, analyzes top papers, and produces a structured
    multi-section report with citations.
    """
    report = await generate_deep_research_report(
        query=payload.query,
        max_papers=payload.max_papers,
    )

    if report.get("status") == "error":
        raise HTTPException(status_code=422, detail=report.get("error", "Report generation failed"))

    return report
