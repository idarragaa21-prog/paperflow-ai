from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.middleware.rate_limit import limiter
from app.models.project import Project
from app.models.search import Search, SearchResult
from app.models.user import User
from app.schemas.search import SearchRecordResponse, SearchRequest, SearchResponse
from app.services.cache import cache
from app.services.federated_search import federated_search
from app.services.permissions import require_project_access
from app.services.pubmed import pubmed_client

router = APIRouter(prefix="/search", tags=["search"])


@router.post("/pubmed", response_model=SearchResponse)
@limiter.limit("3/minute")
async def search_pubmed(
    request: Request,
    payload: SearchRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await require_project_access(db, project_id=payload.project_id, user=user, required_role="viewer")

    filters_dict = payload.filters.model_dump() if payload.filters else None
    cache_key = cache.generate_search_key(payload.query, filters_dict)

    cached_payload = await cache.get(cache_key)
    if cached_payload:
        return SearchResponse(**{**cached_payload, "cached": True})

    data = await pubmed_client.search_and_fetch(payload.query, max_results=payload.max_results)
    results = data["results"]

    search = Search(
        project_id=payload.project_id,
        query=payload.query,
        source="pubmed",
        filters=filters_dict,
        results_count=len(results),
        executed_at=datetime.utcnow(),
    )
    db.add(search)
    await db.flush()

    for r in results:
        pmid = r.get("pmid")
        doi = r.get("doi")

        # Dedup safety for partial unique constraints on pmid/doi.
        if pmid:
            existing = await db.execute(select(SearchResult.id).where(SearchResult.pmid == pmid).limit(1))
            if existing.scalar_one_or_none():
                continue
        if doi:
            existing = await db.execute(select(SearchResult.id).where(SearchResult.doi == doi).limit(1))
            if existing.scalar_one_or_none():
                continue

        sr = SearchResult(
            search_id=search.id,
            pmid=pmid,
            pmcid=r.get("pmcid"),
            doi=doi,
            title=r.get("title") or "",
            authors=r.get("authors"),
            journal=r.get("journal"),
            pub_year=r.get("pub_year"),
            abstract=r.get("abstract"),
            source="pubmed",
            language=r.get("language"),
            is_open_access=bool(r.get("is_open_access")),
            oa_url=r.get("oa_url"),
        )
        db.add(sr)

    await db.commit()

    response_payload = {
        "count": len(results),
        "results": results,
        "query_translation": data.get("query_translation"),
        "cached": False,
        "sources": ["pubmed"],
    }
    await cache.set(cache_key, response_payload, ttl=3600)

    return SearchResponse(**response_payload)


@router.post("/federated", response_model=SearchResponse)
@limiter.limit("3/minute")
async def search_federated(
    request: Request,
    payload: SearchRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await require_project_access(db, project_id=payload.project_id, user=user, required_role="viewer")

    filters_dict = payload.filters.model_dump() if payload.filters else None
    cache_key = cache.generate_search_key(f"federated::{payload.query}", filters_dict)
    cached_payload = await cache.get(cache_key)
    if cached_payload:
        return SearchResponse(**{**cached_payload, "cached": True})

    response_payload = await federated_search(payload.query, max_results=payload.max_results, filters=payload.filters)
    results = response_payload["results"]

    search = Search(
        project_id=payload.project_id,
        query=payload.query,
        source="federated",
        filters=filters_dict,
        results_count=len(results),
        executed_at=datetime.utcnow(),
    )
    db.add(search)
    await db.flush()

    for r in results:
        sr = SearchResult(
            search_id=search.id,
            pmid=r.get("pmid"),
            pmcid=r.get("pmcid"),
            doi=r.get("doi"),
            title=r.get("title") or "",
            authors=r.get("authors"),
            journal=r.get("journal"),
            pub_year=r.get("pub_year"),
            abstract=r.get("abstract"),
            source=r.get("source"),
            language=r.get("language"),
            is_open_access=bool(r.get("is_open_access")),
            oa_url=r.get("oa_url"),
        )
        db.add(sr)

    await db.commit()
    await cache.set(cache_key, response_payload, ttl=3600)
    return SearchResponse(**response_payload)


@router.get("/{search_id}/results")
async def get_search_results(
    search_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = await db.execute(
        select(Search, Project)
        .join(Project, Search.project_id == Project.id)
        .where(Search.id == search_id)
    )
    row = q.first()
    if not row:
        raise HTTPException(status_code=404, detail="Search not found")

    search, project = row
    await require_project_access(db, project_id=project.id, user=user, required_role="viewer")

    q2 = await db.execute(select(SearchResult).where(SearchResult.search_id == search.id))
    results = q2.scalars().all()
    return [
        {
            "id": str(r.id),
            "pmid": r.pmid,
            "pmcid": r.pmcid,
            "doi": r.doi,
            "title": r.title,
            "authors": r.authors,
            "journal": r.journal,
            "pub_year": r.pub_year,
            "abstract": r.abstract,
            "source": r.source,
            "language": r.language,
            "is_open_access": r.is_open_access,
            "oa_url": r.oa_url,
        }
        for r in results
    ]


@router.get("/projects/{project_id}/searches", response_model=list[SearchRecordResponse])
async def list_searches(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await require_project_access(db, project_id=project_id, user=user, required_role="viewer")

    q = await db.execute(
        select(Search)
        .where(Search.project_id == project_id)
        .order_by(Search.executed_at.desc().nullslast())
    )
    items = q.scalars().all()
    return [
        SearchRecordResponse(
            id=s.id,
            project_id=s.project_id,
            query=s.query,
            source=s.source,
            results_count=s.results_count,
            executed_at=s.executed_at,
        )
        for s in items
    ]
