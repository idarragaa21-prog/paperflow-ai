from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db
from app.models.draft import Draft, DraftSection, EvidenceTable
from app.models.user import User
from app.schemas.drafts import (
    DraftCreate,
    DraftPatch,
    DraftResponse,
    EvidenceTableResponse,
    GenerateDraftSectionRequest,
    ResolveDraftCitationsRequest,
)
from app.services.permissions import require_project_access
from app.services.writing_service import build_evidence_table, generate_section, resolve_section_citations

router = APIRouter(tags=["drafts"])


def _draft_to_response(draft: Draft) -> DraftResponse:
    return DraftResponse(
        id=draft.id,
        project_id=draft.project_id,
        title=draft.title,
        status=draft.status,
        version=draft.version,
        sections=[
            {
                "id": section.id,
                "heading": section.heading,
                "position": section.position,
                "content": section.content,
                "generated_with_model": section.generated_with_model,
                "confidence": section.confidence,
                "citations": [
                    {
                        "id": citation.id,
                        "marker": citation.marker,
                        "quoted_text": citation.quoted_text,
                        "locator": citation.locator,
                        "confidence": citation.confidence,
                        "reference_item_id": citation.reference_item_id,
                        "paper_citation_span_id": citation.paper_citation_span_id,
                    }
                    for citation in section.citations
                ],
            }
            for section in draft.sections
        ],
    )


@router.post("/drafts", response_model=DraftResponse)
async def create_draft(
    payload: DraftCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await require_project_access(db, project_id=payload.project_id, user=user, required_role="editor")
    draft = Draft(project_id=payload.project_id, title=payload.title, status="draft", version=1)
    db.add(draft)
    await db.commit()
    await db.refresh(draft)
    await db.refresh(draft, attribute_names=["sections"])
    return _draft_to_response(draft)


@router.get("/drafts", response_model=list[DraftResponse])
async def list_drafts(
    project_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await require_project_access(db, project_id=project_id, user=user, required_role="viewer")
    stmt = (
        select(Draft)
        .where(Draft.project_id == project_id)
        .options(selectinload(Draft.sections).selectinload(DraftSection.citations))
        .order_by(Draft.created_at.desc())
    )
    result = await db.execute(stmt)
    return [_draft_to_response(draft) for draft in result.scalars().all()]


@router.patch("/drafts/{draft_id}", response_model=DraftResponse)
async def patch_draft(
    draft_id: UUID,
    payload: DraftPatch,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = (
        select(Draft)
        .where(Draft.id == draft_id)
        .options(selectinload(Draft.sections).selectinload(DraftSection.citations))
    )
    result = await db.execute(stmt)
    draft = result.scalars().first()
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    await require_project_access(db, project_id=draft.project_id, user=user, required_role="editor")
    if payload.title is not None:
        draft.title = payload.title
    if payload.status is not None:
        draft.status = payload.status
    draft.version += 1
    await db.commit()
    await db.refresh(draft)
    return _draft_to_response(draft)


@router.post("/drafts/{draft_id}/generate-section", response_model=DraftResponse)
async def generate_draft_section(
    draft_id: UUID,
    payload: GenerateDraftSectionRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = (
        select(Draft)
        .where(Draft.id == draft_id)
        .options(selectinload(Draft.sections).selectinload(DraftSection.citations))
    )
    result = await db.execute(stmt)
    draft = result.scalars().first()
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    project, _membership = await require_project_access(db, project_id=draft.project_id, user=user, required_role="editor")
    await generate_section(
        db,
        draft=draft,
        heading=payload.heading,
        paper_ids=payload.paper_ids,
        extraction_record_ids=payload.extraction_record_ids,
        runtime_mode=project.runtime_mode,
    )
    refreshed = await db.execute(
        select(Draft).where(Draft.id == draft.id).options(selectinload(Draft.sections).selectinload(DraftSection.citations))
    )
    return _draft_to_response(refreshed.scalars().first())


@router.post("/drafts/{draft_id}/resolve-citations", response_model=DraftResponse)
async def resolve_draft_citations(
    draft_id: UUID,
    payload: ResolveDraftCitationsRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = (
        select(Draft)
        .where(Draft.id == draft_id)
        .options(selectinload(Draft.sections).selectinload(DraftSection.citations))
    )
    result = await db.execute(stmt)
    draft = result.scalars().first()
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    await require_project_access(db, project_id=draft.project_id, user=user, required_role="editor")
    target_section = next((section for section in draft.sections if payload.section_id is None or section.id == payload.section_id), None)
    if target_section is None:
        raise HTTPException(status_code=404, detail="Draft section not found")
    await resolve_section_citations(db, section=target_section)
    refreshed = await db.execute(
        select(Draft).where(Draft.id == draft.id).options(selectinload(Draft.sections).selectinload(DraftSection.citations))
    )
    return _draft_to_response(refreshed.scalars().first())


@router.get("/evidence/tables", response_model=list[EvidenceTableResponse])
async def list_evidence_tables(
    project_id: UUID = Query(...),
    build: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await require_project_access(db, project_id=project_id, user=user, required_role="editor" if build else "viewer")
    if build:
        await build_evidence_table(db, project_id=project_id)
    stmt = select(EvidenceTable).where(EvidenceTable.project_id == project_id).order_by(EvidenceTable.created_at.desc())
    result = await db.execute(stmt)
    return [
        EvidenceTableResponse(id=item.id, title=item.title, table_json=item.table_json, confidence=item.confidence)
        for item in result.scalars().all()
    ]
