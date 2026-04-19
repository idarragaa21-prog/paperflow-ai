from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.reference_item import ReferenceItem
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
from app.services.writing_export import (
    CITATION_STYLES,
    build_docx,
    build_markdown,
    build_pdf,
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


def _safe_filename(name: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in (name or "document").strip())
    return safe[:80] or "document"


@router.get("/documents/{document_id}/export")
async def export_writing_document(
    document_id: UUID,
    format: str = Query("docx", pattern="^(md|markdown|docx|pdf)$"),
    citation_style: str = Query("apa"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    doc = await get_document(db, document_id=document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Writing document not found")
    await require_project_access(db, project_id=doc.project_id, user=user, required_role="viewer")

    style = (citation_style or "apa").lower()
    if style not in CITATION_STYLES:
        raise HTTPException(status_code=422, detail=f"citation_style must be one of {sorted(CITATION_STYLES)}")

    refs_q = await db.execute(
        select(ReferenceItem)
        .where(ReferenceItem.project_id == doc.project_id)
        .order_by(ReferenceItem.publication_year.desc().nullslast(), ReferenceItem.title.asc())
    )
    references = refs_q.scalars().all()

    base = _safe_filename(doc.title)

    fmt = format.lower()
    if fmt in ("md", "markdown"):
        body = build_markdown(doc, references=references, citation_style=style).encode("utf-8")
        return Response(
            content=body,
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{base}.md"'},
        )
    if fmt == "docx":
        try:
            blob = build_docx(doc, references=references, citation_style=style)
        except ImportError as exc:  # python-docx missing
            from app.core.logger import logger
            logger.exception("DOCX export unavailable")
            raise HTTPException(status_code=503, detail="DOCX export unavailable") from exc
        return Response(
            content=blob,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{base}.docx"'},
        )
    if fmt == "pdf":
        try:
            blob = build_pdf(doc, references=references, citation_style=style)
        except ImportError as exc:
            from app.core.logger import logger
            logger.exception("PDF export unavailable")
            raise HTTPException(status_code=503, detail="PDF export unavailable") from exc
        return Response(
            content=blob,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{base}.pdf"'},
        )
    raise HTTPException(status_code=422, detail=f"Unknown format: {format}")
