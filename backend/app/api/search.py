"""Search API — federated and PubMed endpoints."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.middleware.rate_limit import limiter
from app.models.project import Project
from app.models.search import Search, SearchResult
from app.models.user import User
from app.schemas.search import (
    SearchRecordResponse,
    SearchRequest,
    SearchResponse,
    SearchSynthesizeRequest,
    SearchSynthesizeResponse,
)
from app.services.cache import cache
from app.services.llm.factory import llm_provider
from app.services.federated_search import (
    _NON_ALPHANUM_RE,
    _metadata_score,
    _passes_filters,
    _record_key,
    _relevance_score,
    federated_search,
)
from app.services.permissions import require_project_access
from app.services.pubmed import pubmed_client

router = APIRouter(prefix="/search", tags=["search"])


def _postprocess_pubmed(
    raw_results: list[dict],
    query: str,
    filters,
) -> list[dict]:
    """Apply dedup, filters, oa_url promotion and relevance ranking to PubMed raw results.

    Mirrors the same post-processing that the federated endpoint already applies,
    ensuring consistent behavior regardless of which search endpoint the caller uses.
    """
    seen: set[str] = set()
    filtered: list[dict] = []

    for r in raw_results:
        r.setdefault("source", "pubmed")

        # Dedup within this search only (not globally)
        key = _record_key(r)
        if key in seen:
            continue
        seen.add(key)

        # Post-fetch filter (year, journal, oa, source)
        if not _passes_filters(r, filters):
            continue

        # Promote oa_url via PMC when direct link is missing
        if not r.get("oa_url") and r.get("pmcid"):
            r["oa_url"] = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{r['pmcid']}/pdf/"
        if r.get("oa_url") and not r.get("is_open_access"):
            r["is_open_access"] = True

        filtered.append(r)

    # Attach + sort by relevance
    query_tokens = set(_NON_ALPHANUM_RE.sub("", query.lower()).split())
    for item in filtered:
        item["relevance_score"] = _relevance_score(
            item, query, query_tokens=query_tokens
        )

    filtered.sort(
        key=lambda x: (x["relevance_score"], _metadata_score(x)), reverse=True
    )
    return filtered


@router.post("/pubmed", response_model=SearchResponse)
@limiter.limit("3/minute")
async def search_pubmed(
    request: Request,
    payload: SearchRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await require_project_access(
        db, project_id=payload.project_id, user=user, required_role="viewer"
    )

    filters_dict = payload.filters.model_dump() if payload.filters else None
    cache_key = cache.generate_search_key(
        payload.query,
        filters_dict,
        max_results=payload.max_results,
        source="pubmed",
    )

    cached_payload = await cache.get(cache_key)
    if cached_payload:
        return SearchResponse(**{**cached_payload, "cached": True})

    data = await pubmed_client.search_and_fetch(
        payload.query,
        max_results=payload.max_results,
        filters=payload.filters,
    )

    # Apply filters, dedup, oa_url promotion and ranking (same as federated)
    results = _postprocess_pubmed(data["results"], payload.query, payload.filters)

    search = Search(
        project_id=payload.project_id,
        query=payload.query,
        source="pubmed",
        filters=filters_dict,
        results_count=len(results),
        executed_at=datetime.now(timezone.utc),
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
            source="pubmed",
            language=r.get("language"),
            is_open_access=bool(r.get("is_open_access")),
            oa_url=r.get("oa_url"),
            relevance_score=r.get("relevance_score"),
        )
        db.add(sr)

    await db.commit()

    response_payload = {
        "count": len(results),
        "results": results,
        "query_translation": data.get("query_translation"),
        "cached": False,
        "sources": ["pubmed"],
        "warnings": data.get("warnings") or [],
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
    await require_project_access(
        db, project_id=payload.project_id, user=user, required_role="viewer"
    )

    filters_dict = payload.filters.model_dump() if payload.filters else None
    cache_key = cache.generate_search_key(
        payload.query,
        filters_dict,
        max_results=payload.max_results,
        source="federated",
    )
    cached_payload = await cache.get(cache_key)
    if cached_payload:
        return SearchResponse(**{**cached_payload, "cached": True})

    response_payload = await federated_search(
        payload.query, max_results=payload.max_results, filters=payload.filters
    )
    results = response_payload["results"]

    search = Search(
        project_id=payload.project_id,
        query=payload.query,
        source="federated",
        filters=filters_dict,
        results_count=len(results),
        executed_at=datetime.now(timezone.utc),
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
            relevance_score=r.get("relevance_score"),
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
    await require_project_access(
        db, project_id=project.id, user=user, required_role="viewer"
    )

    # ORDER BY relevance_score DESC so history matches what user originally saw.
    # NULLS LAST handles legacy rows that predate the relevance_score column.
    q2 = await db.execute(
        select(SearchResult)
        .where(SearchResult.search_id == search.id)
        .order_by(SearchResult.relevance_score.desc().nullslast())
    )
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
            "relevance_score": r.relevance_score,
        }
        for r in results
    ]


@router.get(
    "/projects/{project_id}/searches", response_model=list[SearchRecordResponse]
)
async def list_searches(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await require_project_access(
        db, project_id=project_id, user=user, required_role="viewer"
    )

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


@router.post("/synthesize", response_model=SearchSynthesizeResponse)
@limiter.limit("5/minute")
async def synthesize_search(
    request: Request,
    payload: SearchSynthesizeRequest,
    user: User = Depends(get_current_user),
):
    """
    Synthesizes an answer to the search query using the top N retrieved papers.
    """
    if not payload.papers:
        raise HTTPException(status_code=400, detail="No papers provided for synthesis.")

    # We build the context directly from the provided SearchResult/PaperMetadata abstracts.
    context_parts = []
    for i, paper in enumerate(payload.papers[:10], start=1):
        abstract = (paper.abstract or "No abstract available.").strip()
        # Keep abstract reasonably sized
        if len(abstract) > 2000:
            abstract = abstract[:2000] + "..."

        context_parts.append(
            f"[{i}] {paper.title}\n"
            f"Authors: {', '.join(paper.authors[:3]) if paper.authors else 'Unknown'}\n"
            f"Journal: {paper.journal or 'N/A'} ({paper.pub_year or 'N/A'})\n"
            f"Abstract:\n{abstract}\n"
        )

    papers_context = "\n".join(context_parts)

    system_prompt = (
        "You are an expert medical research assistant generating a synthesized overview "
        "of the literature to answer a specific research question. "
        "Always cite specific papers using their number in brackets, e.g., [1] or [2, 4]. "
        "Write in Spanish, clearly and concisely. Structure the response in paragraphs. "
        "Do NOT invent any data; rely ONLY on the provided abstracts."
    )

    user_prompt = (
        f"Research Question: {payload.query}\n\n"
        f"AVAILABLE PAPERS:\n{papers_context}\n\n"
        "Synthesize the findings from the papers above to answer the research question. "
        "Include key outcomes and consensus or contradictions if they exist. "
        "Cite the sources by their bracketed number."
    )

    provider = llm_provider()

    if hasattr(provider, "chat"):
        try:
            r = await provider.chat(  # type: ignore[attr-defined]
                model="default",  # Or let OpenClaw fallback / route
                system=system_prompt,
                user=user_prompt,
                temperature=0.3,
                max_tokens=1500,
            )
            answer = (r.get("content") or "").strip()
        except Exception as e:
            # Fallback for LLM issues
            from app.core.logger import logger

            logger.error(f"Search synthesis LLM failed: {e}")
            raise HTTPException(
                status_code=503, detail="LLM synthesis service unavailable."
            )
    else:
        # If using ClaudeProvider directly, which might only implement base methods:
        raise HTTPException(
            status_code=501, detail="Synthesis requires a chat-capable LLM provider."
        )

    return SearchSynthesizeResponse(answer=answer)
