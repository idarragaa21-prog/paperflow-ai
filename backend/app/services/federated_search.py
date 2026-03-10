from __future__ import annotations

import asyncio
import re
from collections import OrderedDict
from typing import Any
from urllib.parse import quote

import httpx

from app.core.logger import logger
from app.schemas.search import SearchFilters
from app.services.pubmed import pubmed_client
from app.services.search_results import enrich_search_result


def _normalize_title(value: str | None) -> str:
    text = (value or "").strip().lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^a-z0-9 ]+", "", text)
    return text


def _record_key(item: dict[str, Any]) -> str:
    for key in ("doi", "pmid", "pmcid"):
        value = (item.get(key) or "").strip().lower()
        if value:
            return f"{key}:{value}"
    title = _normalize_title(str(item.get("title") or ""))
    year = item.get("pub_year") or "na"
    return f"title:{title}:{year}"


def _passes_filters(item: dict[str, Any], filters: SearchFilters | None) -> bool:
    if not filters:
        return True
    pub_year = item.get("pub_year")
    if filters.year_from or filters.year_to:
        if not isinstance(pub_year, int):
            return False
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
        authors = [str((author or {}).get("name") or "").strip() for author in (bib.get("author") or []) if str((author or {}).get("name") or "").strip()]
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


async def federated_search(query: str, *, max_results: int, filters: SearchFilters | None = None) -> dict[str, Any]:
    pubmed = await pubmed_client.search_and_fetch(query, max_results=max_results, filters=filters)
    pubmed_results = [enrich_search_result({**item, "source": "pubmed"}) for item in pubmed["results"]]

    europe_results: list[dict[str, Any]] = []
    doaj_results: list[dict[str, Any]] = []
    provider_status: dict[str, str] = {
        "pubmed": "ok",
        "europepmc": "ok",
        "doaj": "ok",
    }
    warnings: list[str] = []
    results_or_errors = await asyncio.gather(
        _search_europe_pmc(query, max_results=max_results, filters=filters),
        _search_doaj(query, max_results=max_results),
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

    deduped: OrderedDict[str, dict[str, Any]] = OrderedDict()
    for item in [*pubmed_results, *europe_results, *doaj_results]:
        if not _passes_filters(item, filters):
            continue
        key = _record_key(item)
        existing = deduped.get(key)
        if existing is None:
            deduped[key] = item
            continue

        # Prefer richer OA / metadata coverage.
        score_existing = int(bool(existing.get("abstract"))) + int(bool(existing.get("oa_url"))) + int(bool(existing.get("doi")))
        score_new = int(bool(item.get("abstract"))) + int(bool(item.get("oa_url"))) + int(bool(item.get("doi")))
        if score_new > score_existing:
            deduped[key] = item

    results = list(deduped.values())[:max_results]
    return {
        "count": len(results),
        "results": results,
        "query_translation": pubmed.get("query_translation"),
        "cached": False,
        "sources": ["pubmed", "europepmc", "doaj"],
        "partial_success": any(status != "ok" for status in provider_status.values()),
        "provider_status": provider_status,
        "warnings": warnings,
    }
