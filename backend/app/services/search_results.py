from __future__ import annotations

from typing import Any
from urllib.parse import quote


def build_open_targets(item: dict[str, Any]) -> list[dict[str, str]]:
    targets: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    def add_target(kind: str, url: str | None, label: str) -> None:
        normalized = str(url or "").strip()
        if not normalized or normalized in seen_urls:
            return
        seen_urls.add(normalized)
        targets.append({"kind": kind, "url": normalized, "label": label})

    oa_url = str(item.get("oa_url") or "").strip()
    if oa_url:
        label = "Abrir PDF OA" if oa_url.lower().endswith(".pdf") else "Abrir fuente OA"
        add_target("oa_pdf", oa_url, label)

    doi = str(item.get("doi") or "").strip()
    if doi:
        add_target("doi", f"https://doi.org/{quote(doi, safe='/:')}", "Abrir DOI")

    pmid = str(item.get("pmid") or "").strip()
    if pmid:
        add_target("pubmed", f"https://pubmed.ncbi.nlm.nih.gov/{quote(pmid)}/", "Abrir PubMed")

    return targets


def enrich_search_result(item: dict[str, Any]) -> dict[str, Any]:
    abstract = str(item.get("abstract") or "").strip()
    has_abstract = bool(abstract)
    open_targets = build_open_targets(item)
    can_open_external = bool(open_targets)
    can_save_pdf = bool(item.get("is_open_access")) and bool(item.get("oa_url")) and bool(item.get("doi") or item.get("pmid"))

    if can_save_pdf:
        content_state = "pdf_available"
    elif has_abstract or can_open_external:
        content_state = "abstract_available"
    else:
        content_state = "metadata_only"

    return {
        **item,
        "has_abstract": has_abstract,
        "can_save_pdf": can_save_pdf,
        "can_open_external": can_open_external,
        "content_state": content_state,
        "open_targets": open_targets,
    }
