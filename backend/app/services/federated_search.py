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


async def _search_europe_pmc(query: str, max_results: int) -> list[dict[str, Any]]:
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(
            url,
            params={"query": query, "format": "json", "pageSize": max_results, "resultType": "core"},
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
    return results


_SOURCE_TRUST: dict[str, int] = {"pubmed": 3, "europepmc": 2, "doaj": 1}


def _metadata_coverage(item: dict[str, Any]) -> float:
    """Return a 0-1 quality score based on metadata richness."""
    score = 0.0
    # Abstract length (up to 300 chars = full credit)
    abstract = item.get("abstract") or ""
    score += 0.30 * min(1.0, len(abstract) / 300)
    # Direct PDF URL is worth more than a landing-page URL
    oa_url = (item.get("oa_url") or "").lower()
    if oa_url.endswith(".pdf"):
        score += 0.25
    elif oa_url:
        score += 0.10
    # Identifier richness: doi + pmid + pmcid
    id_count = sum(1 for k in ("doi", "pmid", "pmcid") if item.get(k))
    score += 0.25 * (id_count / 3)
    # Bibliographic completeness: journal + authors
    bib_count = sum(1 for k in ("journal", "authors") if item.get(k))
    score += 0.20 * (bib_count / 2)
    return round(score, 4)


def _merge_records(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    """Field-level best-of-both merge. Higher-trust source wins for contested fields."""
    trust_existing = _SOURCE_TRUST.get(str(existing.get("source") or ""), 0)
    trust_incoming = _SOURCE_TRUST.get(str(incoming.get("source") or ""), 0)
    primary, secondary = (existing, incoming) if trust_existing >= trust_incoming else (incoming, existing)

    merged = dict(primary)

    # Fill missing identifiers from secondary
    for id_field in ("doi", "pmid", "pmcid"):
        if not merged.get(id_field) and secondary.get(id_field):
            merged[id_field] = secondary[id_field]

    # Prefer longer abstract
    abs_primary = str(primary.get("abstract") or "")
    abs_secondary = str(secondary.get("abstract") or "")
    if len(abs_secondary) > len(abs_primary):
        merged["abstract"] = abs_secondary

    # Prefer direct PDF URL over landing-page URL
    oa_primary = str(primary.get("oa_url") or "").lower()
    oa_secondary = str(secondary.get("oa_url") or "").lower()
    if oa_secondary.endswith(".pdf") and not oa_primary.endswith(".pdf"):
        merged["oa_url"] = secondary["oa_url"]
    elif not merged.get("oa_url") and secondary.get("oa_url"):
        merged["oa_url"] = secondary["oa_url"]

    # OR open-access flag
    if secondary.get("is_open_access"):
        merged["is_open_access"] = True

    # Track contributing sources for transparency
    src_set: list[str] = list(dict.fromkeys(
        (existing.get("_sources") or [existing.get("source")]) +
        (incoming.get("_sources") or [incoming.get("source")])
    ))
    merged["_sources"] = [s for s in src_set if s]

    return merged


def _relevance_score(item: dict[str, Any], query: str) -> float:
    """Compute a relevance score for ranking federated results.

    Components (all 0-1, weighted):
      - title_match   (0.30): unigram + bigram token overlap between query and title
      - metadata_qual (0.25): _metadata_coverage() — abstract length, direct PDF, ids, bib
      - oa_available  (0.15): direct PDF URL vs landing page vs OA flag only
      - id_strength   (0.15): has DOI and/or PMID (resolvability)
      - recency       (0.15): newer papers score higher (2026=1.0, 2000=0.0)
    """
    score = 0.0

    # --- Title match with bigram bonus (0.30) ---
    query_norm = re.sub(r"[^a-z0-9 ]+", "", query.lower())
    title_norm = re.sub(r"[^a-z0-9 ]+", "", (item.get("title") or "").lower())
    query_tokens = query_norm.split()
    title_tokens = title_norm.split()
    query_set = set(query_tokens)
    title_set = set(title_tokens)
    if query_set and title_set:
        unigram_overlap = len(query_set & title_set) / max(len(query_set), 1)
        # Bigram bonus: consecutive query token pairs present in title
        query_bigrams = {(query_tokens[i], query_tokens[i + 1]) for i in range(len(query_tokens) - 1)}
        title_bigrams = {(title_tokens[i], title_tokens[i + 1]) for i in range(len(title_tokens) - 1)}
        bigram_bonus = (len(query_bigrams & title_bigrams) / max(len(query_bigrams), 1)) if query_bigrams else 0.0
        title_score = min(1.0, unigram_overlap + 0.20 * bigram_bonus)
        score += 0.30 * title_score

    # --- Metadata quality (0.25) ---
    score += 0.25 * _metadata_coverage(item)

    # --- OA availability (0.15) ---
    oa_url = (item.get("oa_url") or "").lower()
    if oa_url.endswith(".pdf"):
        score += 0.15
    elif oa_url:
        score += 0.08
    elif item.get("is_open_access"):
        score += 0.04

    # --- ID strength / resolvability (0.15) ---
    has_doi = bool(item.get("doi"))
    has_pmid = bool(item.get("pmid"))
    if has_doi and has_pmid:
        score += 0.15
    elif has_doi:
        score += 0.12
    elif has_pmid:
        score += 0.09

    # --- Recency (0.15) ---
    pub_year = item.get("pub_year")
    if isinstance(pub_year, int) and 1900 < pub_year <= 2026:
        recency = max(0.0, min(1.0, (pub_year - 2000) / 26))
        score += 0.15 * recency

    return round(score, 4)


async def federated_search(query: str, *, max_results: int, filters: SearchFilters | None = None) -> dict[str, Any]:
    pubmed = await pubmed_client.search_and_fetch(query, max_results=max_results)
    pubmed_results = [{**item, "source": "pubmed"} for item in pubmed["results"]]

    europe_results: list[dict[str, Any]] = []
    doaj_results: list[dict[str, Any]] = []
    results_or_errors = await asyncio.gather(
        _search_europe_pmc(query, max_results=max_results),
        _search_doaj(query, max_results=max_results),
        return_exceptions=True,
    )
    if isinstance(results_or_errors[0], Exception):
        logger.warning(f"Federated search Europe PMC failure: {results_or_errors[0]}")
    else:
        europe_results = results_or_errors[0]
    if isinstance(results_or_errors[1], Exception):
        logger.warning(f"Federated search DOAJ failure: {results_or_errors[1]}")
    else:
        doaj_results = results_or_errors[1]

    # Dedup: field-level best-of-both merge per unique key.
    deduped: OrderedDict[str, dict[str, Any]] = OrderedDict()
    for item in [*pubmed_results, *europe_results, *doaj_results]:
        if not _passes_filters(item, filters):
            continue
        key = _record_key(item)
        existing = deduped.get(key)
        if existing is None:
            deduped[key] = item
            continue
        deduped[key] = _merge_records(existing, item)

    # Rank by relevance score instead of arbitrary source order.
    ranked = sorted(deduped.values(), key=lambda r: _relevance_score(r, query), reverse=True)

    # Attach score to each result for transparency.
    results: list[dict[str, Any]] = []
    for item in ranked[:max_results]:
        item["relevance_score"] = _relevance_score(item, query)
        results.append(item)

    return {
        "count": len(results),
        "results": results,
        "query_translation": pubmed.get("query_translation"),
        "cached": False,
        "sources": ["pubmed", "europepmc", "doaj"],
    }
