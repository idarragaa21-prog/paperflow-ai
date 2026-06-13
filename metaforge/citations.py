"""Reference interchange: RIS and BibTeX export/import.

Bridges MetaForge with Zotero (and Mendeley/EndNote): export the included
studies as RIS/BibTeX, or import an RIS/BibTeX file you exported from Zotero to
seed screening with references you already collected.
"""
from __future__ import annotations

import re


def _authors_list(authors: str) -> list[str]:
    if not authors:
        return []
    return [a.strip() for a in re.split(r"[;,]\s*(?=[A-ZÁÉÍÓÚÑ])|;\s*", authors) if a.strip()] or \
           [a.strip() for a in authors.split(";") if a.strip()]


def to_ris(records: list[dict]) -> str:
    out = []
    for r in records:
        lines = ["TY  - JOUR", f"TI  - {r.get('title', '')}"]
        for au in _authors_list(r.get("authors", "")):
            lines.append(f"AU  - {au}")
        if r.get("year"):
            lines.append(f"PY  - {r['year']}")
        if r.get("journal"):
            lines.append(f"JO  - {r['journal']}")
        if r.get("doi"):
            lines.append(f"DO  - {r['doi']}")
        if r.get("abstract"):
            lines.append(f"AB  - {r['abstract']}")
        if r.get("pmid"):
            lines.append(f"AN  - {r['pmid']}")
        url = r.get("doi_url") or r.get("pdf_url")
        if url:
            lines.append(f"UR  - {url}")
        lines.append("ER  - ")
        out.append("\n".join(lines))
    return "\n\n".join(out) + "\n"


def _bibtex_key(r: dict, i: int) -> str:
    first = (r.get("authors", "").split(",")[0].split()[0] if r.get("authors") else "ref")
    return re.sub(r"[^A-Za-z0-9]", "", f"{first}{r.get('year', '')}") or f"ref{i}"


def to_bibtex(records: list[dict]) -> str:
    out = []
    for i, r in enumerate(records):
        authors = " and ".join(_authors_list(r.get("authors", "")))
        fields = [f"  title = {{{r.get('title', '')}}}"]
        if authors:
            fields.append(f"  author = {{{authors}}}")
        if r.get("journal"):
            fields.append(f"  journal = {{{r['journal']}}}")
        if r.get("year"):
            fields.append(f"  year = {{{r['year']}}}")
        if r.get("doi"):
            fields.append(f"  doi = {{{r['doi']}}}")
        if r.get("abstract"):
            fields.append(f"  abstract = {{{r['abstract']}}}")
        out.append(f"@article{{{_bibtex_key(r, i)},\n" + ",\n".join(fields) + "\n}")
    return "\n\n".join(out) + "\n"


def _record(*, title="", authors="", journal="", year="", doi="", abstract="", pmid="") -> dict:
    doi = (doi or "").strip()
    return {
        "id": ("doi:" + doi.lower()) if doi else ("pmid:" + pmid if pmid else "imp:" + re.sub(r"\W+", "", title.lower())[:40]),
        "source": "Importado", "title": title.strip().rstrip("."), "authors": authors.strip(),
        "journal": journal.strip(), "year": str(year).strip()[:4], "doi": doi or None,
        "abstract": abstract.strip(), "pmid": pmid or None, "pmcid": None, "is_oa": False,
        "pub_types": [], "cited_by": 0, "fulltext_urls": [], "pdf_url": None,
        "doi_url": (f"https://doi.org/{doi}" if doi else None),
    }


def parse_ris(text: str) -> list[dict]:
    records, cur, authors = [], {}, []
    for raw in text.splitlines():
        m = re.match(r"^([A-Z][A-Z0-9])  -\s?(.*)$", raw)
        if not m:
            if cur and raw.strip():  # continuation of previous field
                cur["_last"] = cur.get("_last", "") + " " + raw.strip()
            continue
        tag, val = m.group(1), m.group(2).strip()
        if tag == "TY":
            cur, authors = {}, []
        elif tag in ("T1", "TI"):
            cur["title"] = val
        elif tag in ("AU", "A1"):
            authors.append(val)
        elif tag in ("PY", "Y1"):
            cur["year"] = val[:4]
        elif tag in ("JO", "JF", "T2", "JA"):
            cur.setdefault("journal", val)
        elif tag == "DO":
            cur["doi"] = val
        elif tag == "AB":
            cur["abstract"] = val
        elif tag == "AN":
            cur["pmid"] = val
        elif tag == "ER":
            records.append(_record(title=cur.get("title", ""), authors=", ".join(authors),
                                   journal=cur.get("journal", ""), year=cur.get("year", ""),
                                   doi=cur.get("doi", ""), abstract=cur.get("abstract", ""),
                                   pmid=cur.get("pmid", "")))
            cur, authors = {}, []
    return records


_BIB_ENTRY = re.compile(r"@\w+\s*\{[^,]*,(.*?)\n\}", re.S)
_BIB_FIELD = re.compile(r"(\w+)\s*=\s*[{\"](.+?)[}\"]\s*,?\s*$", re.S | re.M)


def parse_bibtex(text: str) -> list[dict]:
    records = []
    for body in _BIB_ENTRY.findall(text):
        f = {k.lower(): re.sub(r"\s+", " ", v).strip() for k, v in _BIB_FIELD.findall(body)}
        authors = " , ".join(a.strip() for a in f.get("author", "").split(" and ") if a.strip())
        records.append(_record(title=f.get("title", ""), authors=authors, journal=f.get("journal", ""),
                               year=f.get("year", ""), doi=f.get("doi", ""), abstract=f.get("abstract", "")))
    return records


def parse_references(text: str) -> list[dict]:
    """Auto-detect RIS vs BibTeX and parse."""
    text = (text or "").strip()
    if not text:
        return []
    if text.lstrip().startswith("@") or "@article" in text.lower():
        return parse_bibtex(text)
    return parse_ris(text)
