from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.writing import WritingSection
from app.services.permissions import require_project_access
from app.services.writing_documents_service import (
    create_document,
    generate_section,
    get_document,
    list_documents,
    resolve_document_citations,
    serialize_document,
    update_section_content,
)

router = APIRouter(prefix="/writing", tags=["writing"])


class WritingDocumentCreateRequest(BaseModel):
    project_id: UUID
    title: str = Field(min_length=2, max_length=255)
    mode: str = Field(default="narrative")


class WritingSectionPatchRequest(BaseModel):
    heading: str | None = None
    content_markdown: str | None = None


@router.post("/documents")
async def create_writing_document(
    payload: WritingDocumentCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await require_project_access(db, project_id=payload.project_id, user=user, required_role="editor")
    try:
        doc = await create_document(
            db,
            project_id=payload.project_id,
            user_id=user.id,
            title=payload.title,
            mode=payload.mode,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return serialize_document(doc)


@router.get("/documents")
async def get_writing_documents(
    project_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await require_project_access(db, project_id=project_id, user=user, required_role="viewer")
    docs = await list_documents(db, project_id=project_id)
    return [serialize_document(item) for item in docs]


@router.get("/documents/{document_id}")
async def get_writing_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    doc = await get_document(db, document_id=document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Writing document not found")
    await require_project_access(db, project_id=doc.project_id, user=user, required_role="viewer")
    return serialize_document(doc)


@router.post("/documents/{document_id}/sections/{section_key}")
async def generate_writing_section(
    document_id: UUID,
    section_key: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    doc = await get_document(db, document_id=document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Writing document not found")
    await require_project_access(db, project_id=doc.project_id, user=user, required_role="editor")

    section_stmt = select(WritingSection).where(WritingSection.document_id == doc.id).where(WritingSection.section_key == section_key)
    section = (await db.execute(section_stmt)).scalars().first()
    if section is None:
        raise HTTPException(status_code=404, detail="Writing section not found")

    await generate_section(db, document=doc, section=section)
    refreshed = await get_document(db, document_id=doc.id)
    return serialize_document(refreshed)


@router.patch("/documents/{document_id}/sections/{section_key}")
async def patch_writing_section(
    document_id: UUID,
    section_key: str,
    payload: WritingSectionPatchRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    doc = await get_document(db, document_id=document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Writing document not found")
    await require_project_access(db, project_id=doc.project_id, user=user, required_role="editor")

    section_stmt = select(WritingSection).where(WritingSection.document_id == doc.id).where(WritingSection.section_key == section_key)
    section = (await db.execute(section_stmt)).scalars().first()
    if section is None:
        raise HTTPException(status_code=404, detail="Writing section not found")

    await update_section_content(
        db,
        document=doc,
        section=section,
        content_markdown=payload.content_markdown,
        heading=payload.heading,
    )
    refreshed = await get_document(db, document_id=doc.id)
    return serialize_document(refreshed)


@router.post("/documents/{document_id}/citations/resolve")
async def resolve_writing_citations(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    doc = await get_document(db, document_id=document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Writing document not found")
    await require_project_access(db, project_id=doc.project_id, user=user, required_role="viewer")
    return await resolve_document_citations(db, document=doc)
