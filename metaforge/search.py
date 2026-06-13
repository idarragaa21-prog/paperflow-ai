"""Real literature search and retrieval.

Queries Europe PMC (which indexes MEDLINE/PubMed + PMC, returns abstracts and
open-access full-text links in JSON) and reports the PubMed hit count for the
same query for transparency. This turns the protocol's search strategy into an
actual, reproducible set of candidate records — not a copy-pasteable string.
"""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request

EUROPEPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
_UA = {"User-Agent": "MetaForge/1.0 (systematic-review tool)"}


def _get_json(url: str, *, timeout: int = 30) -> dict:
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def europepmc_query(pubmed_query: str) -> str:
    """Make a PubMed-style string friendlier for Europe PMC's parser.

    Europe PMC does not understand PubMed field tags like [Mesh]/[tiab]/[pt];
    stripping them leaves a clean boolean free-text/keyword query that Europe
    PMC handles well across title, abstract and indexing terms.
    """
    q = re.sub(r"\[[^\]]*\]", "", pubmed_query or "")   # drop [Mesh], [tiab], [pt]…
    q = re.sub(r'"\s*"', "", q)
    q = re.sub(r"\s+", " ", q).strip()
    return q


def _parse_record(rec: dict) -> dict:
    ft = (rec.get("fullTextUrlList") or {}).get("fullTextUrl", []) or []
    fulltext = [
        {"url": u.get("url"), "style": u.get("documentStyle"), "availability": u.get("availability")}
        for u in ft if u.get("url")
    ]
    pdf = next((u["url"] for u in fulltext if (u["style"] or "").lower() == "pdf"), None)
    return {
        "id": rec.get("id"),
        "source": rec.get("source"),
        "pmid": rec.get("pmid"),
        "pmcid": rec.get("pmcid"),
        "doi": rec.get("doi"),
        "title": rec.get("title", "").rstrip("."),
        "abstract": rec.get("abstractText", "") or "",
        "authors": rec.get("authorString", ""),
        "journal": ((rec.get("journalInfo") or {}).get("journal") or {}).get("title", ""),
        "year": rec.get("pubYear", ""),
        "pub_types": (rec.get("pubTypeList") or {}).get("pubType", []),
        "is_oa": rec.get("isOpenAccess") == "Y",
        "cited_by": rec.get("citedByCount", 0),
        "fulltext_urls": fulltext,
        "pdf_url": pdf,
        "doi_url": (f"https://doi.org/{rec['doi']}" if rec.get("doi") else None),
    }


def pubmed_count(query: str, *, timeout: int = 20) -> int | None:
    try:
        url = EUTILS + "?" + urllib.parse.urlencode(
            {"db": "pubmed", "term": query, "retmax": 0, "retmode": "json"})
        data = _get_json(url, timeout=timeout)
        return int(data.get("esearchresult", {}).get("count", 0))
    except Exception:  # noqa: BLE001
        return None


def search_literature(query: str, *, page_size: int = 25, only_oa: bool = False,
                      pubmed_query: str | None = None, sort: str = "relevance",
                      timeout: int = 30) -> dict:
    """Search Europe PMC; return parsed records + hit counts.

    Default sort is by relevance so the returned page is the most pertinent
    records for screening (sorting by date surfaces recent but off-topic work).
    """
    query = (query or "").strip()
    if not query:
        raise ValueError("Escribe una consulta de búsqueda.")
    epmc_q = query
    if only_oa:
        epmc_q = f"({epmc_q}) AND OPEN_ACCESS:y"
    params = {"query": epmc_q, "format": "json", "resultType": "core",
              "pageSize": max(1, min(int(page_size), 100))}
    if sort == "date":
        params["sort"] = "P_PDATE_D desc"
    elif sort == "cited":
        params["sort"] = "CITED desc"
    # relevance = Europe PMC default (no sort param)
    url = EUROPEPMC + "?" + urllib.parse.urlencode(params)
    try:
        data = _get_json(url, timeout=timeout)
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"No se pudo conectar a Europe PMC: {exc}") from exc
    records = [_parse_record(r) for r in (data.get("resultList") or {}).get("result", [])]
    return {
        "query": query,
        "europepmc_query": epmc_q,
        "hit_count": int(data.get("hitCount", 0)),
        "pubmed_count": pubmed_count(pubmed_query or query),
        "returned": len(records),
        "records": records,
    }
