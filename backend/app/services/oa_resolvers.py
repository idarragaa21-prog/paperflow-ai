from __future__ import annotations

from dataclasses import dataclass
import re

import httpx

from app.config import settings


class OAResolverError(Exception):
    pass


@dataclass
class OAResolved:
    url_for_pdf: str
    source: str
    oa_url: str | None = None
    landing_url: str | None = None


_DOI_PREFIX_RE = re.compile(r"^https?://(dx\.)?doi\.org/", flags=re.IGNORECASE)


def normalize_doi(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip()
    cleaned = _DOI_PREFIX_RE.sub("", cleaned)
    return cleaned.lower() or None


_SPACE_RE = re.compile(r"\s+")
_NONALNUM_RE = re.compile(r"[^a-z0-9 ]")


def normalize_title(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = _SPACE_RE.sub(" ", value.strip().lower())
    cleaned = _NONALNUM_RE.sub("", cleaned)
    return cleaned or None


def normalize_reference_identity(
    *, doi: str | None, pmid: str | None, title: str | None, source: str | None
) -> dict:
    return {
        "doi": normalize_doi(doi),
        "pmid": (pmid or "").strip() or None,
        "title_normalized": normalize_title(title),
        "source_provenance": source,
    }


class UnpaywallResolver:
    base_url = "https://api.unpaywall.org/v2"

    async def resolve(self, doi: str, client: httpx.AsyncClient) -> OAResolved:
        normalized_doi = normalize_doi(doi)
        if not normalized_doi:
            raise OAResolverError("DOI requerido")
        email = settings.UNPAYWALL_EMAIL or "you@example.com"
        response = await client.get(
            f"{self.base_url}/{normalized_doi}", params={"email": email}, timeout=30
        )
        response.raise_for_status()
        data = response.json()

        best = data.get("best_oa_location") or {}
        pdf = best.get("url_for_pdf")
        landing_url = best.get("url")
        if not pdf:
            for loc in data.get("oa_locations") or []:
                pdf = (loc or {}).get("url_for_pdf")
                if pdf:
                    landing_url = (loc or {}).get("url") or landing_url
                    break
        if not pdf:
            raise OAResolverError("Unpaywall no devolvió URL PDF open-access")
        return OAResolved(
            url_for_pdf=pdf, source="unpaywall", oa_url=pdf, landing_url=landing_url
        )


class EuropePMCResolver:
    base_url = "https://www.ebi.ac.uk/europepmc/webservices/rest"

    async def resolve_by_pmid(self, pmid: str, client: httpx.AsyncClient) -> OAResolved:
        if not pmid:
            raise OAResolverError("PMID requerido")

        query = f"EXT_ID:{pmid} AND SRC:MED"
        response = await client.get(
            f"{self.base_url}/search",
            params={
                "query": query,
                "format": "json",
                "pageSize": 1,
                "resultType": "core",
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        hits = (data.get("resultList") or {}).get("result") or []
        if not hits:
            raise OAResolverError("Europe PMC no encontró resultado para el PMID")

        item = hits[0]
        is_oa = str(item.get("isOpenAccess") or "").lower() in ("y", "yes", "true", "1")
        if not is_oa:
            raise OAResolverError(
                "Europe PMC: el artículo no está marcado como Open Access"
            )

        full_text = (item.get("fullTextUrlList") or {}).get("fullTextUrl") or []
        pdf_url = None
        for candidate in full_text:
            url = (candidate or {}).get("url")
            if not url:
                continue
            style = str((candidate or {}).get("documentStyle") or "").lower()
            if style == "pdf" or url.lower().endswith(".pdf"):
                pdf_url = url
                break
        if not pdf_url:
            raise OAResolverError("Europe PMC no devolvió URL PDF open-access")
        return OAResolved(
            url_for_pdf=pdf_url,
            source="europepmc",
            oa_url=pdf_url,
            landing_url=f"https://europepmc.org/article/MED/{pmid}",
        )


class DOIContentNegotiationResolver:
    async def resolve(self, doi: str, client: httpx.AsyncClient) -> OAResolved:
        normalized_doi = normalize_doi(doi)
        if not normalized_doi:
            raise OAResolverError("DOI requerido")

        response = await client.get(
            f"https://doi.org/{normalized_doi}",
            headers={"Accept": "application/pdf"},
            follow_redirects=True,
            timeout=30,
        )
        response.raise_for_status()
        content_type = str(response.headers.get("content-type") or "").lower()
        if "pdf" not in content_type and not str(response.url).lower().endswith(".pdf"):
            raise OAResolverError("DOI resolution did not return a PDF")
        landing_url = f"https://doi.org/{normalized_doi}"
        return OAResolved(
            url_for_pdf=str(response.url),
            source="doi_content_negotiation",
            oa_url=str(response.url),
            landing_url=landing_url,
        )


async def resolve_open_access_pdf(
    *,
    doi: str | None,
    pmid: str | None,
    client: httpx.AsyncClient,
) -> OAResolved:
    attempts: list[str] = []
    if doi:
        for resolver in (UnpaywallResolver(), DOIContentNegotiationResolver()):
            try:
                return await resolver.resolve(doi, client)
            except (OAResolverError, httpx.HTTPError) as exc:
                attempts.append(str(exc))
    if pmid:
        try:
            return await EuropePMCResolver().resolve_by_pmid(pmid, client)
        except (OAResolverError, httpx.HTTPError) as exc:
            attempts.append(str(exc))
    raise OAResolverError(
        "; ".join([attempt for attempt in attempts if attempt])
        or "No se pudo resolver un PDF open-access"
    )
