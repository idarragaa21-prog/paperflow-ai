from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.middleware.rate_limit import limiter
from app.models.paper import Paper
from app.models.reference_item import ReferenceItem
from app.models.user import User
from app.schemas.references import ReferenceItemResponse, ReferencesImportRequest, ReferencesImportResponse
from app.services.audit import log_audit
from app.services.pagination import apply_desc_cursor, encode_cursor
from app.services.permissions import require_project_access
from app.services.references_io import export_bibtex, export_ris, parse_bibtex_entries, parse_ris_entries

router = APIRouter(prefix="/references", tags=["references"])


def _to_response(item: ReferenceItem) -> ReferenceItemResponse:
    return ReferenceItemResponse(
        id=item.id,
        project_id=item.project_id,
        paper_id=item.paper_id,
        source_format=item.source_format,
        citation_key=item.citation_key,
        title=item.title,
        authors=item.authors or [],
        journal=item.journal,
        publication_year=item.publication_year,
        doi=item.doi,
        pmid=item.pmid,
        pmcid=item.pmcid,
        language=item.language,
    )

@router.post("/import", response_model=ReferencesImportResponse)
@limiter.limit("10/minute")
async def import_references(
    request: Request,
    payload: ReferencesImportRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await require_project_access(db, project_id=payload.project_id, user=user, required_role="editor")
    parser = parse_bibtex_entries if payload.format == "bibtex" else parse_ris_entries
    parsed = parser(payload.content)

    imported: list[ReferenceItem] = []
    skipped = 0
    for entry in parsed:
        dedup_q = await db.execute(
            select(ReferenceItem).where(
                and_(
                    ReferenceItem.project_id == payload.project_id,
                    or_(
                        and_(ReferenceItem.doi.is_not(None), ReferenceItem.doi == entry.get("doi")),
                        and_(ReferenceItem.pmid.is_not(None), ReferenceItem.pmid == entry.get("pmid")),
                        ReferenceItem.title == entry["title"],
                    ),
                )
            )
        )
        if dedup_q.scalars().first():
            skipped += 1
            continue
        item = ReferenceItem(project_id=payload.project_id, **entry)
        db.add(item)
        imported.append(item)
    await db.commit()
    for item in imported:
        await db.refresh(item)

    await log_audit(
        db,
        user=user,
        action="create",
        entity_type="reference_import",
        entity_id=payload.project_id,
        details={"format": payload.format, "imported": len(imported), "skipped": skipped},
        request=request,
    )
    return ReferencesImportResponse(imported=len(imported), skipped=skipped, items=[_to_response(item) for item in imported])


@router.get("")
async def list_references(
    project_id: UUID,
    limit: int = Query(default=50, ge=1, le=100),
    cursor: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await require_project_access(db, project_id=project_id, user=user, required_role="viewer")
    filters = [ReferenceItem.project_id == project_id]
    cursor_clause = apply_desc_cursor(ReferenceItem, created_at=ReferenceItem.created_at, row_id=ReferenceItem.id, cursor=cursor)
    page_filters = list(filters)
    if cursor_clause is not None:
        page_filters.append(cursor_clause)
    total_q = await db.execute(select(func.count()).select_from(ReferenceItem).where(and_(*filters)))
    q = await db.execute(
        select(ReferenceItem)
        .where(and_(*page_filters))
        .order_by(ReferenceItem.created_at.desc(), ReferenceItem.id.desc())
        .limit(limit + 1)
    )
    rows = q.scalars().all()
    has_more = len(rows) > limit
    items = rows[:limit]
    next_cursor = encode_cursor(created_at=items[-1].created_at, row_id=items[-1].id) if has_more and items else None
    return {
        "items": [_to_response(item).model_dump() for item in items],
        "next_cursor": next_cursor,
        "has_more": has_more,
        "total_count": int(total_q.scalar() or 0),
    }


@router.post("/sync-from-library")
@limiter.limit("10/minute")
async def sync_references_from_library(
    request: Request,
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await require_project_access(db, project_id=project_id, user=user, required_role="editor")
    created = 0
    batch_size = 100
    offset = 0
    while True:
        papers_q = await db.execute(
            select(Paper).where(Paper.project_id == project_id).order_by(Paper.created_at.desc(), Paper.id.desc()).limit(batch_size).offset(offset)
        )
        papers = papers_q.scalars().all()
        if not papers:
            break
        for paper in papers:
            ref_q = await db.execute(select(ReferenceItem).where(ReferenceItem.project_id == project_id).where(ReferenceItem.paper_id == paper.id))
            if ref_q.scalars().first():
                continue
            db.add(
                ReferenceItem(
                    project_id=project_id,
                    paper_id=paper.id,
                    source_format="paper_library",
                    citation_key=(paper.doi or paper.pmid or str(paper.id).split("-")[0]),
                    title=paper.title,
                    authors=[part.strip() for part in (paper.authors or "").split(";") if part.strip()] if paper.authors else None,
                    journal=paper.journal,
                    publication_year=paper.publication_year,
                    doi=paper.doi,
                    pmid=paper.pmid,
                    pmcid=paper.pmcid,
                    abstract_text=paper.abstract_text,
                    language=paper.language,
                    raw_payload={"paper_id": str(paper.id), "source_provider": paper.source_provider},
                )
            )
            created += 1
        offset += batch_size
    await db.commit()
    await log_audit(
        db,
        user=user,
        action="create",
        entity_type="reference_sync",
        entity_id=project_id,
        details={"created": created},
        request=request,
    )
    return {"created": created}


@router.get("/export", response_class=PlainTextResponse)
async def export_references(
    project_id: UUID,
    format: str = Query(..., pattern="^(bibtex|ris)$"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await require_project_access(db, project_id=project_id, user=user, required_role="viewer")
    q = await db.execute(select(ReferenceItem).where(ReferenceItem.project_id == project_id).order_by(ReferenceItem.created_at.asc()))
    items = q.scalars().all()
    payload = [
        {
            "citation_key": item.citation_key,
            "title": item.title,
            "authors": item.authors or [],
            "journal": item.journal,
            "publication_year": item.publication_year,
            "doi": item.doi,
            "pmid": item.pmid,
        }
        for item in items
    ]
    body = export_bibtex(payload) if format == "bibtex" else export_ris(payload)
    media_type = "application/x-bibtex" if format == "bibtex" else "application/x-research-info-systems"
    return PlainTextResponse(body, media_type=media_type)
