from __future__ import annotations

import asyncio
import re
from collections import OrderedDict
from typing import Any
from urllib.parse import quote

import httpx

from app.core.logger import logger
from app.schemas.search import SearchFilters
from app.services.oa_resolvers import normalize_doi
from app.services.pubmed import pubmed_client
from app.services.search_results import enrich_search_result


def _normalize_title(value: str | None) -> str:
    text = (value or "").strip().lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^a-z0-9 ]+", "", text)
    return text


def _normalized_journal(value: str | None) -> str:
    return _normalize_title(value)


def _record_key(item: dict[str, Any]) -> str:
    doi = normalize_doi(item.get("doi"))
    if doi:
        return f"doi:{doi}"
    for key in ("pmid", "pmcid"):
        value = (item.get(key) or "").strip().lower()
        if value:
            return f"{key}:{value}"
    title = _normalize_title(str(item.get("title") or ""))
    year = item.get("pub_year") or "na"
    return f"title:{title}:{year}"


SOURCE_PRIORITY = {"europepmc": 3, "pubmed": 2, "doaj": 1}


def _abstract_quality_score(item: dict[str, Any]) -> int:
    abstract = str(item.get("abstract") or "").strip()
    if not abstract:
        return 0
    word_count = len(abstract.split())
    if word_count >= 120:
        return 5
    if word_count >= 60:
        return 4
    if word_count >= 30:
        return 3
    if word_count >= 10:
        return 2
    return 1


def _metadata_score(item: dict[str, Any]) -> int:
    authors = item.get("authors") or []
    oa_url = str(item.get("oa_url") or "").strip()
    score = 0
    score += 5 if normalize_doi(item.get("doi")) else 0
    score += 4 if str(item.get("pmid") or "").strip() else 0
    score += 2 if str(item.get("pmcid") or "").strip() else 0
    score += _abstract_quality_score(item) * 3
    score += 4 if item.get("journal") else 0
    score += 3 if item.get("pub_year") else 0
    score += 2 if item.get("language") else 0
    score += 2 if authors else 0
    score += min(len(authors), 6)
    score += 6 if oa_url.lower().endswith(".pdf") else 0
    score += 4 if oa_url else 0
    score += 2 if item.get("is_open_access") else 0
    score += SOURCE_PRIORITY.get(str(item.get("source") or "").lower(), 0)
    return score


def _consistency_score(candidate: dict[str, Any], peers: list[dict[str, Any]]) -> int:
    score = 0
    candidate_doi = normalize_doi(candidate.get("doi"))
    candidate_pmid = str(candidate.get("pmid") or "").strip()
    candidate_pmcid = str(candidate.get("pmcid") or "").strip()
    candidate_title = _normalize_title(candidate.get("title"))
    candidate_year = candidate.get("pub_year")
    candidate_journal = _normalized_journal(candidate.get("journal"))

    for peer in peers:
        if peer is candidate:
            continue
        if candidate_doi and candidate_doi == normalize_doi(peer.get("doi")):
            score += 4
        if candidate_pmid and candidate_pmid == str(peer.get("pmid") or "").strip():
            score += 4
        if candidate_pmcid and candidate_pmcid == str(peer.get("pmcid") or "").strip():
            score += 2
        if candidate_title and candidate_title == _normalize_title(peer.get("title")):
            score += 2
        if candidate_year and candidate_year == peer.get("pub_year"):
            score += 1
        if candidate_journal and candidate_journal == _normalized_journal(peer.get("journal")):
            score += 1
    return score


def _candidate_rank(candidate: dict[str, Any], peers: list[dict[str, Any]]) -> tuple[int, int, int]:
    return (
        _metadata_score(candidate),
        _consistency_score(candidate, peers),
        SOURCE_PRIORITY.get(str(candidate.get("source") or "").lower(), 0),
    )


def _pick_richer_value(current, candidate):
    if current in (None, "", [], {}):
        return candidate
    if candidate in (None, "", [], {}):
        return current
    if isinstance(current, str) and isinstance(candidate, str):
        return candidate if len(candidate.strip()) > len(current.strip()) else current
    if isinstance(current, list) and isinstance(candidate, list):
        return candidate if len(candidate) > len(current) else current
    return current


def _merge_duplicate_group(records: list[dict[str, Any]]) -> dict[str, Any]:
    ordered = sorted(records, key=lambda record: _candidate_rank(record, records), reverse=True)
    merged = dict(ordered[0])

    for candidate in ordered[1:]:
        for field in ("doi", "pmid", "pmcid", "journal", "pub_year", "language"):
            merged[field] = _pick_richer_value(merged.get(field), candidate.get(field))

        if _abstract_quality_score(candidate) > _abstract_quality_score(merged):
            merged["abstract"] = candidate.get("abstract")

        merged["authors"] = _pick_richer_value(merged.get("authors"), candidate.get("authors"))

        candidate_oa = str(candidate.get("oa_url") or "").strip()
        merged_oa = str(merged.get("oa_url") or "").strip()
        if (candidate_oa and not merged_oa) or (
            candidate_oa.lower().endswith(".pdf") and not merged_oa.lower().endswith(".pdf")
        ):
            merged["oa_url"] = candidate_oa
        merged["is_open_access"] = bool(merged.get("is_open_access") or candidate.get("is_open_access"))

    return enrich_search_result(merged)


def _passes_filters(item: dict[str, Any], filters: SearchFilters | None) -> bool:
    if not filters:
        return True
    pub_year = item.get("pub_year")
    if filters.year_from and isinstance(pub_year, int) and pub_year < filters.year_from:
        return False
    if filters.year_to and isinstance(pub_year, int) and pub_year > filters.year_to:
        return False
    if filters.open_access_only and not item.get("is_open_access"):
        return False
    if filters.journal and filters.journal.lower() not in str(item.get("journal") or "").lower():
        return False
    if filters.source and filters.source.lower() != str(item.get("source") or "").lower():
        return False
    return True


def _should_drop_yearless_result(item: dict[str, Any], filters: SearchFilters | None) -> bool:
    if not filters or not (filters.year_from or filters.year_to):
        return False
    if item.get("pub_year") is not None:
        return False
    return str(item.get("source") or "").lower() == "doaj"


def _apply_europe_pmc_filters(query: str, filters: SearchFilters | None) -> str:
    if not filters:
        return query
    parts = [f"({query})"]
    if filters.year_from or filters.year_to:
        start = filters.year_from or 1900
        end = filters.year_to or 3000
        parts.append(f"PUB_YEAR:[{start} TO {end}]")
    if filters.open_access_only:
        parts.append("OPEN_ACCESS:y")
    return " AND ".join(parts)


async def _search_europe_pmc(query: str, max_results: int, filters: SearchFilters | None = None) -> list[dict[str, Any]]:
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    filtered_query = _apply_europe_pmc_filters(query, filters)
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(
            url,
            params={"query": filtered_query, "format": "json", "pageSize": max_results, "resultType": "core"},
        )
        response.raise_for_status()
    hits = ((response.json() or {}).get("resultList") or {}).get("result") or []
    results: list[dict[str, Any]] = []
    for item in hits:
        authors = []
        author_string = str(item.get("authorString") or "").strip()
        if author_string:
            authors = [part.strip() for part in re.split(r",|;", author_string) if part.strip()]
        is_oa = str(item.get("isOpenAccess") or "").lower() in {"y", "yes", "true", "1"}
        pdf_url = None
        for candidate in ((item.get("fullTextUrlList") or {}).get("fullTextUrl") or []):
            url_value = str((candidate or {}).get("url") or "").strip()
            if url_value.lower().endswith(".pdf"):
                pdf_url = url_value
                break
        results.append(
            enrich_search_result(
                {
                    "pmid": str(item.get("pmid") or "") or None,
                    "pmcid": str(item.get("pmcid") or "") or None,
                    "doi": str(item.get("doi") or "") or None,
                    "title": str(item.get("title") or "").strip() or "Untitled paper",
                    "authors": authors,
                    "journal": str(item.get("journalTitle") or "").strip() or None,
                    "pub_year": int(item["pubYear"]) if str(item.get("pubYear") or "").isdigit() else None,
                    "abstract": str(item.get("abstractText") or "").strip() or None,
                    "source": "europepmc",
                    "language": str(item.get("language") or "").strip() or None,
                    "is_open_access": is_oa,
                    "oa_url": pdf_url,
                }
            )
        )
    return results


async def _search_doaj(query: str, max_results: int) -> list[dict[str, Any]]:
    url = "https://doaj.org/api/search/articles/" + quote(query, safe="")
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(url, params={"pageSize": max_results})
        response.raise_for_status()
    hits = (response.json() or {}).get("results") or []
    results: list[dict[str, Any]] = []
    for hit in hits:
        bib = (((hit or {}).get("bibjson") or {}))
        identifiers = bib.get("identifier") or []
        doi = None
        for identifier in identifiers:
            if str((identifier or {}).get("type") or "").lower() == "doi":
                doi = str((identifier or {}).get("id") or "").strip() or None
                break
        authors = [
            str((author or {}).get("name") or "").strip()
            for author in (bib.get("author") or [])
            if str((author or {}).get("name") or "").strip()
        ]
        journal = ((bib.get("journal") or {}).get("title") or None)
        year = None
        for candidate in (bib.get("year"), ((bib.get("journal") or {}).get("year"))):
            if str(candidate or "").isdigit():
                year = int(candidate)
                break
        abstract = str(bib.get("abstract") or "").strip() or None
        fulltext = None
        for link in (bib.get("link") or []):
            url_value = str((link or {}).get("url") or "").strip()
            if not url_value:
                continue
            fulltext = url_value
            if url_value.lower().endswith(".pdf"):
                break
        results.append(
            enrich_search_result(
                {
                    "pmid": None,
                    "pmcid": None,
                    "doi": doi,
                    "title": str(bib.get("title") or "").strip() or "Untitled paper",
                    "authors": authors,
                    "journal": journal,
                    "pub_year": year,
                    "abstract": abstract,
                    "source": "doaj",
                    "language": str(bib.get("language") or "").strip() or None,
                    "is_open_access": True,
                    "oa_url": fulltext,
                }
            )
        )
    return results


async def _search_semantic_scholar(query: str, max_results: int) -> list[dict[str, Any]]:
    """Search Semantic Scholar Academic Graph API (no key required for basic use, M4)."""
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    fields = "paperId,title,abstract,authors,year,journal,externalIds,openAccessPdf,isOpenAccess"
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                url,
                params={"query": query, "limit": min(max_results, 100), "fields": fields},
                headers={"User-Agent": "PaperFlowAI/1.0 (academic research tool)"},
            )
            response.raise_for_status()
    except Exception as exc:
        logger.warning(f"Semantic Scholar search failed: {exc}")
        return []

    data = response.json() or {}
    hits = data.get("data") or []
    results: list[dict[str, Any]] = []
    for item in hits:
        external_ids = item.get("externalIds") or {}
        doi = external_ids.get("DOI") or None
        pmid = str(external_ids.get("PubMed") or "").strip() or None
        authors = [
            str((a or {}).get("name") or "").strip()
            for a in (item.get("authors") or [])
            if str((a or {}).get("name") or "").strip()
        ]
        oa_pdf = (item.get("openAccessPdf") or {}).get("url") or None
        journal_info = item.get("journal") or {}
        journal = str(journal_info.get("name") or "").strip() or None
        year = item.get("year") or None
        if year is not None:
            try:
                year = int(year)
            except (ValueError, TypeError):
                year = None
        results.append(
            enrich_search_result(
                {
                    "pmid": pmid,
                    "pmcid": None,
                    "doi": doi,
                    "title": str(item.get("title") or "").strip() or "Untitled paper",
                    "authors": authors,
                    "journal": journal,
                    "pub_year": year,
                    "abstract": str(item.get("abstract") or "").strip() or None,
                    "source": "semantic_scholar",
                    "language": None,
                    "is_open_access": bool(item.get("isOpenAccess")),
                    "oa_url": oa_pdf,
                }
            )
        )
    return results


def _relevance_score(item: dict[str, Any], query: str) -> float:
    score = 0.0
    query_tokens = set(re.sub(r"[^a-z0-9 ]+", "", query.lower()).split())
    title_tokens = set(re.sub(r"[^a-z0-9 ]+", "", (item.get("title") or "").lower()).split())
    if query_tokens and title_tokens:
        overlap = len(query_tokens & title_tokens)
        score += 0.30 * (overlap / max(len(query_tokens), 1))

    pub_year = item.get("pub_year")
    if isinstance(pub_year, int) and 1900 < pub_year <= 2026:
        recency = max(0.0, min(1.0, (pub_year - 2000) / 26))
        score += 0.20 * recency

    meta_fields = ["abstract", "doi", "journal", "authors"]
    filled = sum(1 for field in meta_fields if item.get(field))
    score += 0.20 * (filled / len(meta_fields))

    if item.get("oa_url"):
        score += 0.15
    elif item.get("is_open_access"):
        score += 0.07

    has_doi = bool(item.get("doi"))
    has_pmid = bool(item.get("pmid"))
    id_score = 0.0
    if has_doi and has_pmid:
        id_score = 1.0
    elif has_doi:
        id_score = 0.8
    elif has_pmid:
        id_score = 0.6
    score += 0.15 * id_score

    score += min(_metadata_score(item) / 100, 0.10)
    return round(min(max(score, 0.0), 1.0), 4)


async def federated_search(query: str, *, max_results: int, filters: SearchFilters | None = None) -> dict[str, Any]:
    pubmed = await pubmed_client.search_and_fetch(query, max_results=max_results, filters=filters)
    pubmed_results = [enrich_search_result({**item, "source": "pubmed"}) for item in pubmed["results"]]

    europe_results: list[dict[str, Any]] = []
    doaj_results: list[dict[str, Any]] = []
    semantic_results: list[dict[str, Any]] = []
    provider_status: dict[str, str] = {"pubmed": "ok", "europepmc": "ok", "doaj": "ok", "semantic_scholar": "ok"}
    warnings: list[str] = []
    results_or_errors = await asyncio.gather(
        _search_europe_pmc(query, max_results=max_results, filters=filters),
        _search_doaj(query, max_results=max_results),
        _search_semantic_scholar(query, max_results=max_results),
        return_exceptions=True,
    )
    if isinstance(results_or_errors[0], Exception):
        logger.warning(f"Federated search Europe PMC failure: {results_or_errors[0]}")
        provider_status["europepmc"] = "error"
        warnings.append("Europe PMC no respondió")
    else:
        europe_results = results_or_errors[0]
    if isinstance(results_or_errors[1], Exception):
        logger.warning(f"Federated search DOAJ failure: {results_or_errors[1]}")
        provider_status["doaj"] = "error"
        warnings.append("DOAJ no respondió")
    else:
        doaj_results = results_or_errors[1]
        if filters and (filters.year_from or filters.year_to):
            provider_status["doaj"] = "filtered_server_side"
            warnings.append("DOAJ se filtro por ano en el servidor")
    if isinstance(results_or_errors[2], Exception):
        logger.warning(f"Federated search Semantic Scholar failure: {results_or_errors[2]}")
        provider_status["semantic_scholar"] = "error"
        warnings.append("Semantic Scholar no respondió")
    else:
        semantic_results = results_or_errors[2]

    deduped: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
    for item in [*pubmed_results, *europe_results, *doaj_results, *semantic_results]:
        if not _passes_filters(item, filters):
            continue
        if _should_drop_yearless_result(item, filters):
            continue
        key = _record_key(item)
        deduped.setdefault(key, []).append(item)

    merged = [_merge_duplicate_group(group) for group in deduped.values()]
    ranked = sorted(merged, key=lambda item: (_relevance_score(item, query), _metadata_score(item)), reverse=True)

    results: list[dict[str, Any]] = []
    for item in ranked[:max_results]:
        enriched = dict(item)
        enriched["relevance_score"] = _relevance_score(enriched, query)
        results.append(enriched)

    return {
        "count": len(results),
        "results": results,
        "query_translation": pubmed.get("query_translation"),
        "cached": False,
        "sources": ["pubmed", "europepmc", "doaj", "semantic_scholar"],
        "partial_success": any(status != "ok" for status in provider_status.values()),
        "provider_status": provider_status,
        "warnings": warnings,
    }
