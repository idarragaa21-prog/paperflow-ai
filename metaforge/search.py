"""Real literature search and retrieval.

Searches Europe PMC (abstracts + open-access full-text links) and/or PubMed via
E-utilities (native MeSH query, the authoritative MEDLINE index), merges and
deduplicates the records by DOI/PMID/title. This turns the protocol's search
strategy into an actual, reproducible set of candidate records.
"""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

EUROPEPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
_UA = {"User-Agent": "MetaForge/1.0 (systematic-review tool)"}


def _get(url: str, *, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _get_json(url: str, *, timeout: int = 30) -> dict:
    return json.loads(_get(url, timeout=timeout).decode("utf-8"))


def europepmc_query(pubmed_query: str) -> str:
    """Strip PubMed field tags ([Mesh]/[tiab]/[pt]) for Europe PMC's parser."""
    q = re.sub(r"\[[^\]]*\]", "", pubmed_query or "")
    q = re.sub(r'"\s*"', "", q)
    return re.sub(r"\s+", " ", q).strip()


# --- Europe PMC --------------------------------------------------------------
def _parse_epmc(rec: dict) -> dict:
    ft = (rec.get("fullTextUrlList") or {}).get("fullTextUrl", []) or []
    fulltext = [{"url": u.get("url"), "style": u.get("documentStyle"), "availability": u.get("availability")}
                for u in ft if u.get("url")]
    pdf = next((u["url"] for u in fulltext if (u["style"] or "").lower() == "pdf"), None)
    return {
        "id": rec.get("id"), "source": "Europe PMC", "pmid": rec.get("pmid"),
        "pmcid": rec.get("pmcid"), "doi": rec.get("doi"),
        "title": (rec.get("title") or "").rstrip("."), "abstract": rec.get("abstractText", "") or "",
        "authors": rec.get("authorString", ""),
        "journal": ((rec.get("journalInfo") or {}).get("journal") or {}).get("title", ""),
        "year": rec.get("pubYear", ""), "pub_types": (rec.get("pubTypeList") or {}).get("pubType", []),
        "is_oa": rec.get("isOpenAccess") == "Y", "cited_by": rec.get("citedByCount", 0),
        "fulltext_urls": fulltext, "pdf_url": pdf,
        "doi_url": (f"https://doi.org/{rec['doi']}" if rec.get("doi") else None),
    }


def _search_europepmc(query: str, page_size: int, only_oa: bool, timeout: int) -> dict:
    q = f"({query}) AND OPEN_ACCESS:y" if only_oa else query
    params = {"query": q, "format": "json", "resultType": "core", "pageSize": page_size}
    data = _get_json(EUROPEPMC + "?" + urllib.parse.urlencode(params), timeout=timeout)
    records = [_parse_epmc(r) for r in (data.get("resultList") or {}).get("result", [])]
    return {"hit_count": int(data.get("hitCount", 0)), "records": records}


# --- PubMed (E-utilities) ----------------------------------------------------
def _txt(el) -> str:
    return "".join(el.itertext()).strip() if el is not None else ""


def _parse_pubmed(article: ET.Element) -> dict:
    art = article.find(".//Article")
    pmid = _txt(article.find(".//PMID"))
    title = _txt(art.find("ArticleTitle")) if art is not None else ""
    abstract = " ".join(_txt(a) for a in art.findall(".//Abstract/AbstractText")) if art is not None else ""
    authors = []
    if art is not None:
        for au in art.findall(".//AuthorList/Author"):
            ln, ini = _txt(au.find("LastName")), _txt(au.find("Initials"))
            if ln:
                authors.append(f"{ln} {ini}".strip())
    journal = _txt(art.find(".//Journal/Title")) if art is not None else ""
    year = ""
    if art is not None:
        year = _txt(art.find(".//JournalIssue/PubDate/Year")) or _txt(art.find(".//JournalIssue/PubDate/MedlineDate"))[:4]
    doi = ""
    for eid in article.findall(".//ArticleIdList/ArticleId"):
        if eid.get("IdType") == "doi":
            doi = _txt(eid)
    if not doi and art is not None:
        for eid in art.findall(".//ELocationID"):
            if eid.get("EIdType") == "doi":
                doi = _txt(eid)
    pubtypes = [_txt(pt) for pt in art.findall(".//PublicationTypeList/PublicationType")] if art is not None else []
    return {
        "id": f"pmid:{pmid}", "source": "PubMed", "pmid": pmid, "pmcid": None, "doi": doi or None,
        "title": title.rstrip("."), "abstract": abstract, "authors": ", ".join(authors[:8]),
        "journal": journal, "year": year, "pub_types": pubtypes, "is_oa": False, "cited_by": 0,
        "fulltext_urls": [], "pdf_url": None,
        "doi_url": (f"https://doi.org/{doi}" if doi else (f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else None)),
    }


def _search_pubmed(query: str, page_size: int, timeout: int) -> dict:
    es = _get_json(ESEARCH + "?" + urllib.parse.urlencode(
        {"db": "pubmed", "term": query, "retmax": page_size, "retmode": "json", "sort": "relevance"}), timeout=timeout)
    result = es.get("esearchresult", {})
    ids = result.get("idlist", [])
    count = int(result.get("count", 0))
    records = []
    if ids:
        xml = _get(EFETCH + "?" + urllib.parse.urlencode(
            {"db": "pubmed", "id": ",".join(ids), "retmode": "xml", "rettype": "abstract"}), timeout=timeout)
        root = ET.fromstring(xml)
        records = [_parse_pubmed(a) for a in root.findall(".//PubmedArticle")]
    return {"hit_count": count, "records": records}


def pubmed_count(query: str, *, timeout: int = 20) -> int | None:
    try:
        data = _get_json(ESEARCH + "?" + urllib.parse.urlencode(
            {"db": "pubmed", "term": query, "retmax": 0, "retmode": "json"}), timeout=timeout)
        return int(data.get("esearchresult", {}).get("count", 0))
    except Exception:  # noqa: BLE001
        return None


# --- Merge / dedup -----------------------------------------------------------
def _key(rec: dict) -> str:
    if rec.get("doi"):
        return "doi:" + rec["doi"].lower().strip()
    if rec.get("pmid"):
        return "pmid:" + str(rec["pmid"]).strip()
    return "title:" + re.sub(r"[^a-z0-9]+", "", (rec.get("title") or "").lower())[:60]


def _dedup(record_lists: list[list[dict]]) -> tuple[list[dict], int]:
    seen: dict[str, dict] = {}
    dropped = 0
    for records in record_lists:
        for r in records:
            k = _key(r)
            if k in seen:
                dropped += 1
                # prefer the record that carries an abstract / OA links
                if not seen[k].get("abstract") and r.get("abstract"):
                    seen[k]["abstract"] = r["abstract"]
                if not seen[k].get("pdf_url") and r.get("pdf_url"):
                    seen[k]["pdf_url"] = r["pdf_url"]
                    seen[k]["is_oa"] = seen[k]["is_oa"] or r.get("is_oa", False)
            else:
                seen[k] = dict(r)
    return list(seen.values()), dropped


def search_literature(query: str, *, source: str = "europepmc", page_size: int = 25,
                      only_oa: bool = False, pubmed_query: str | None = None, timeout: int = 30) -> dict:
    """Search one or both databases; return parsed, deduplicated records."""
    query = (query or "").strip()
    if not query:
        raise ValueError("Escribe una consulta de búsqueda.")
    page_size = max(1, min(int(page_size), 100))
    pm_query = (pubmed_query or query)

    lists, hit_epmc, hit_pubmed = [], None, None
    try:
        if source in ("europepmc", "both"):
            # Europe PMC's parser rejects PubMed field tags ([MeSH]/[tiab]/…) and
            # returns 0 results, so always convert before querying it.
            e = _search_europepmc(europepmc_query(query), page_size, only_oa, timeout)
            hit_epmc = e["hit_count"]
            lists.append(e["records"])
        if source in ("pubmed", "both"):
            p = _search_pubmed(pm_query, page_size, timeout)
            hit_pubmed = p["hit_count"]
            lists.append(p["records"])
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"No se pudo conectar a la base de datos: {exc}") from exc

    records, duplicates = _dedup(lists)
    return {
        "query": query, "source": source,
        "hit_count": hit_epmc if hit_epmc is not None else (hit_pubmed or 0),
        "hit_europepmc": hit_epmc,
        "pubmed_count": hit_pubmed if hit_pubmed is not None else pubmed_count(pm_query),
        "duplicates_removed": duplicates,
        "returned": len(records),
        "records": records,
    }
