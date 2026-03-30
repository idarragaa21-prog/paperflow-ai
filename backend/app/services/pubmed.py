from __future__ import annotations

import re
import time
import xml.etree.ElementTree as ET
from typing import Any

import asyncio

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.logger import logger


EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


class PubMedClient:
    """Thin PubMed E-utilities client with polite throttling.

    NCBI rate limits are easy to hit when we do multiple queries in a single job.
    We enforce a minimal delay between requests to avoid 429 stalls.
    """

    _lock: Any = None
    _last_request_ts: float = 0.0

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=20)
        # Lazy init so import-time doesn't create event-loop objects.
        if PubMedClient._lock is None:
            import asyncio

            PubMedClient._lock = asyncio.Lock()

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(httpx.HTTPError),
    )
    async def _get(self, url: str, params: dict[str, Any]) -> httpx.Response:
        # Polite throttling to reduce 429s (NCBI: ~3 req/s without API key).
        # We serialize requests because clinical jobs fan out multiple queries.
        min_interval_s = 0.45
        async with PubMedClient._lock:
            now = time.perf_counter()
            wait_s = min_interval_s - (now - PubMedClient._last_request_ts)
            if wait_s > 0:
                await asyncio.sleep(wait_s)
            PubMedClient._last_request_ts = time.perf_counter()

        t0 = time.perf_counter()
        resp = await self.client.get(url, params=params)
        latency_ms = int((time.perf_counter() - t0) * 1000)
        logger.info(f"PubMed GET {url} status={resp.status_code} latency_ms={latency_ms}")
        resp.raise_for_status()
        return resp

    async def esearch(self, query: str, retmax: int = 20) -> dict[str, Any]:
        url = f"{EUTILS_BASE}/esearch.fcgi"
        params = {
            "db": "pubmed",
            "term": query,
            "retmode": "json",
            "retmax": retmax,
        }
        resp = await self._get(url, params)
        return resp.json()

    async def esummary(self, pmids: list[str]) -> dict[str, Any]:
        url = f"{EUTILS_BASE}/esummary.fcgi"
        params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "json",
        }
        resp = await self._get(url, params)
        return resp.json()

    async def efetch_xml(self, pmids: list[str]) -> str:
        url = f"{EUTILS_BASE}/efetch.fcgi"
        params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",
        }
        resp = await self._get(url, params)
        return resp.text

    def _collect_efetch_enrichment(self, xml_text: str) -> tuple[dict[str, str], dict[str, list[str]], list[str]]:
        """Parse efetch XML and return (abstracts, pub_types, warnings).

        Returns a warning string instead of silently degrading so callers
        can surface the issue to the user.
        """
        abstracts: dict[str, str] = {}
        pub_types: dict[str, list[str]] = {}
        warnings: list[str] = []

        try:
            root = ET.fromstring(xml_text)
        except Exception as _xml_err:
            logger.warning(f"[PubMedClient] failed to parse efetch XML: {_xml_err!r}")
            warnings.append("PubMed abstract enrichment unavailable; continuing with metadata-only results.")
            return abstracts, pub_types, warnings

        for article in root.findall(".//PubmedArticle"):
            pmid_el = article.find(".//MedlineCitation/PMID")
            if pmid_el is None or not (pmid_el.text or "").strip():
                continue
            pmid = pmid_el.text.strip()

            abs_parts: list[str] = []
            for abs_el in article.findall(".//Article/Abstract/AbstractText"):
                if abs_el.text:
                    abs_parts.append(abs_el.text.strip())
            if abs_parts:
                abstracts[pmid] = "\n".join(abs_parts).strip()

            pts: list[str] = []
            for pt_el in article.findall(".//Article/PublicationTypeList/PublicationType"):
                if pt_el.text and pt_el.text.strip():
                    pts.append(pt_el.text.strip())
            if pts:
                pub_types[pmid] = pts

        return abstracts, pub_types, warnings

    def _parse_efetch_abstracts(self, xml_text: str) -> dict[str, str]:
        """Return pmid -> abstract text (best effort). Legacy; prefer _collect_efetch_enrichment."""
        abstracts, _, _ = self._collect_efetch_enrichment(xml_text)
        return abstracts

    def _parse_efetch_publication_types(self, xml_text: str) -> dict[str, list[str]]:
        """Return pmid -> publication types list (best effort). Legacy; prefer _collect_efetch_enrichment."""
        _, pub_types, _ = self._collect_efetch_enrichment(xml_text)
        return pub_types

    def _extract_ids_from_esummary(self, item: dict[str, Any]) -> tuple[str | None, str | None]:
        pmcid = None
        doi = None
        for aid in item.get("articleids", []) or []:
            idtype = (aid.get("idtype") or "").lower()
            val = aid.get("value")
            if not val:
                continue
            if idtype == "pmcid":
                # PubMed sometimes returns values like "pmc-id: PMC1234567;".
                m = re.search(r"(PMC\d+)", str(val))
                pmcid = m.group(1) if m else str(val).strip().strip(";")
            elif idtype == "doi":
                doi = str(val).strip()
        return pmcid, doi

    def _apply_filters_to_query(self, query: str, filters: Any) -> str:
        """Append PubMed date-range filters to a query string."""
        parts = [query]
        if filters is not None:
            year_from = getattr(filters, "year_from", None)
            year_to = getattr(filters, "year_to", None)
            if year_from is not None:
                parts.append(f'"{year_from}"[Date - Publication]')
            if year_to is not None:
                parts.append(f'"{year_to}"[Date - Publication]')
        return " AND ".join(parts) if len(parts) > 1 else parts[0]

    async def search_and_fetch(self, query: str, max_results: int = 20, filters: Any = None) -> dict[str, Any]:
        effective_query = self._apply_filters_to_query(query, filters)
        s = await self.esearch(query=effective_query, retmax=max_results)
        es = s.get("esearchresult", {})
        pmids = es.get("idlist", []) or []
        query_translation = es.get("querytranslation")

        if not pmids:
            return {"results": [], "query_translation": query_translation}

        summ = await self.esummary(pmids)
        result_map = (summ.get("result") or {})

        # Abstracts + publication types via efetch (best effort)
        abstracts: dict[str, str] = {}
        pub_types: dict[str, list[str]] = {}
        enrich_warnings: list[str] = []
        try:
            xml_text = await self.efetch_xml(pmids)
            abstracts, pub_types, enrich_warnings = self._collect_efetch_enrichment(xml_text)
        except Exception as _fetch_err:
            logger.warning(f"[PubMedClient] efetch failed for pmids={pmids[:5]}...: {_fetch_err!r} — results will have no abstracts or publication types")
            enrich_warnings.append("PubMed abstract enrichment unavailable; continuing with metadata-only results.")
            abstracts = {}
            pub_types = {}

        results: list[dict[str, Any]] = []
        for pmid in pmids:
            item = result_map.get(pmid)
            if not isinstance(item, dict):
                continue

            title = item.get("title") or ""
            journal = item.get("fulljournalname") or item.get("source")
            pubdate = item.get("pubdate") or ""
            pub_year = None
            for tok in str(pubdate).split():
                if tok.isdigit() and len(tok) == 4:
                    pub_year = int(tok)
                    break

            authors = []
            for a in item.get("authors", []) or []:
                name = a.get("name") if isinstance(a, dict) else None
                if name:
                    authors.append(name)

            pmcid, doi = self._extract_ids_from_esummary(item)
            abstract = abstracts.get(str(pmid))
            publication_types = pub_types.get(str(pmid), [])

            # OA detection: only mark true when we have a PMCID (PMC implies OA) or a known OA URL.
            is_oa = bool(pmcid)
            oa_url = None
            if pmcid:
                oa_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/pdf/"

            results.append(
                {
                    "pmid": str(pmid),
                    "pmcid": pmcid,
                    "doi": doi,
                    "title": title,
                    "authors": authors,
                    "journal": journal,
                    "pub_year": pub_year,
                    "abstract": abstract,
                    "publication_types": publication_types,
                    "is_open_access": is_oa,
                    "oa_url": oa_url,
                }
            )

        return {"results": results, "query_translation": query_translation, "warnings": enrich_warnings}


pubmed_client = PubMedClient()
