from __future__ import annotations

from urllib.parse import quote

from .web import safe_fetch_json


CROSSREF_API = 'https://api.crossref.org/works?rows={rows}&query.title={query}'
DOI_API = 'https://api.crossref.org/works/{doi}'


def _candidate_from_crossref_item(item: dict, index: int = 1) -> dict:
    title_list = item.get('title') or []
    link_list = item.get('link') or []
    pdf_link = None
    landing_url = item.get('URL')
    for link in link_list:
        content_type = (link.get('content-type') or '').lower()
        if 'pdf' in content_type:
            pdf_link = link.get('URL')
            break
    issued = item.get('issued', {}).get('date-parts', [[None]])[0]
    year = issued[0] if issued else None
    authors = []
    for author in item.get('author') or []:
        parts = [author.get('given'), author.get('family')]
        authors.append(' '.join(part for part in parts if part))
    return {
        'rank': index,
        'title': title_list[0] if title_list else 'Untitled result',
        'doi': item.get('DOI'),
        'pmid': None,
        'year': year,
        'authors': authors[:6],
        'journal': (item.get('container-title') or [None])[0],
        'type': item.get('type'),
        'oa_status': 'candidate' if pdf_link else 'unknown',
        'landing_url': landing_url,
        'pdf_url': pdf_link,
        'confidence': round(max(0.25, 0.95 - ((index - 1) * 0.08)), 2),
    }


def search_crossref(query: str, *, rows: int = 5) -> tuple[list[dict], list[str]]:
    url = CROSSREF_API.format(rows=rows, query=quote(query))
    payload, error = safe_fetch_json(url)
    warnings: list[str] = []
    if error:
        warnings.append(f'crossref_error: {error}')
        return [], warnings

    items = ((payload or {}).get('message') or {}).get('items') or []
    results: list[dict] = []
    for index, item in enumerate(items, start=1):
        results.append(_candidate_from_crossref_item(item, index=index))
    return results, warnings


def lookup_crossref_doi(doi: str) -> tuple[dict | None, list[str]]:
    normalized = doi.strip().replace('https://doi.org/', '').replace('http://doi.org/', '')
    payload, error = safe_fetch_json(DOI_API.format(doi=quote(normalized, safe='')))
    warnings: list[str] = []
    if error:
        warnings.append(f'crossref_doi_error: {error}')
        return None, warnings
    item = ((payload or {}).get('message')) or {}
    return _candidate_from_crossref_item(item, index=1), warnings
