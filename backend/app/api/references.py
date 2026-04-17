from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.middleware.rate_limit import limiter
from app.models.paper import Paper
from app.models.reference_item import ReferenceItem
from app.models.user import User
from app.schemas.references import ReferenceItemResponse, ReferencesImportRequest, ReferencesImportResponse
from app.services.audit import log_audit
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

    # Pre-fetch existing entries to avoid N+1 query problem during deduplication
    dois = {entry.get("doi") for entry in parsed if entry.get("doi")}
    pmids = {entry.get("pmid") for entry in parsed if entry.get("pmid")}
    titles = {entry.get("title") for entry in parsed if entry.get("title")}

    existing_refs_q = await db.execute(
        select(ReferenceItem).where(
            and_(
                ReferenceItem.project_id == payload.project_id,
                or_(
                    ReferenceItem.doi.in_(dois) if dois else False,
                    ReferenceItem.pmid.in_(pmids) if pmids else False,
                    ReferenceItem.title.in_(titles) if titles else False,
                ),
            )
        )
    )
    existing_refs = existing_refs_q.scalars().all()
    existing_dois = {ref.doi for ref in existing_refs if ref.doi}
    existing_pmids = {ref.pmid for ref in existing_refs if ref.pmid}
    existing_titles = {ref.title for ref in existing_refs if ref.title}

    imported: list[ReferenceItem] = []
    skipped = 0
    for entry in parsed:
        doi = entry.get("doi")
        pmid = entry.get("pmid")
        title = entry.get("title")

        is_duplicate = False
        if doi and doi in existing_dois:
            is_duplicate = True
        elif pmid and pmid in existing_pmids:
            is_duplicate = True
        elif title and title in existing_titles:
            is_duplicate = True

        if is_duplicate:
            skipped += 1
            continue

        item = ReferenceItem(project_id=payload.project_id, **entry)
        db.add(item)
        imported.append(item)

        # Add to existing sets to catch duplicates within the import payload itself
        if doi:
            existing_dois.add(doi)
        if pmid:
            existing_pmids.add(pmid)
        if title:
            existing_titles.add(title)

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


@router.get("", response_model=list[ReferenceItemResponse])
async def list_references(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await require_project_access(db, project_id=project_id, user=user, required_role="viewer")
    q = await db.execute(select(ReferenceItem).where(ReferenceItem.project_id == project_id).order_by(ReferenceItem.created_at.desc()))
    return [_to_response(item) for item in q.scalars().all()]


@router.post("/sync-from-library")
@limiter.limit("10/minute")
async def sync_references_from_library(
    request: Request,
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await require_project_access(db, project_id=project_id, user=user, required_role="editor")

    # Pre-fetch existing reference paper IDs to avoid N+1 query problem
    existing_refs_q = await db.execute(
        select(ReferenceItem.paper_id).where(ReferenceItem.project_id == project_id)
    )
    existing_paper_ids = {ref_id for ref_id in existing_refs_q.scalars().all() if ref_id is not None}

    papers_q = await db.execute(select(Paper).where(Paper.project_id == project_id))
    papers = papers_q.scalars().all()

    created = 0
    for paper in papers:
        if paper.id in existing_paper_ids:
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

@router.post("/sync-paper/{paper_id}")
@limiter.limit("10/minute")
async def sync_single_paper_reference(
    request: Request,
    paper_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Get paper
    paper_q = await db.execute(select(Paper).where(Paper.id == paper_id))
    paper = paper_q.scalars().first()
    if not paper:
        return {"created": 0}

    await require_project_access(db, project_id=paper.project_id, user=user, required_role="editor")

    ref_q = await db.execute(select(ReferenceItem).where(ReferenceItem.project_id == paper.project_id).where(ReferenceItem.paper_id == paper.id))
    if ref_q.scalars().first():
        return {"created": 0}

    db.add(
        ReferenceItem(
            project_id=paper.project_id,
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

    await db.commit()
    await log_audit(
        db,
        user=user,
        action="create",
        entity_type="reference_sync",
        entity_id=paper.project_id,
        details={"created": 1, "paper_id": str(paper.id)},
        request=request,
    )
    return {"created": 1}
