from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.config import settings


class OAResolverError(Exception):
    pass


@dataclass
class OAResolved:
    url_for_pdf: str
    source: str


class UnpaywallResolver:
    base_url = "https://api.unpaywall.org/v2"

    async def resolve(self, doi: str, client: httpx.AsyncClient) -> OAResolved:
        if not doi:
            raise OAResolverError("DOI requerido")
        email = settings.UNPAYWALL_EMAIL or "idarragaa21@gmail.com"
        url = f"{self.base_url}/{doi}"
        r = await client.get(url, params={"email": email}, timeout=30)
        r.raise_for_status()
        data = r.json()

        best = data.get("best_oa_location") or {}
        pdf = best.get("url_for_pdf")
        if not pdf:
            # fallback to any oa_location
            for loc in data.get("oa_locations") or []:
                pdf = (loc or {}).get("url_for_pdf")
                if pdf:
                    break

        if not pdf:
            raise OAResolverError("Unpaywall no devolvió URL PDF open-access")

        return OAResolved(url_for_pdf=pdf, source="unpaywall")


class EuropePMCResolver:
    base_url = "https://www.ebi.ac.uk/europepmc/webservices/rest"

    async def resolve_by_pmid(self, pmid: str, client: httpx.AsyncClient) -> OAResolved:
        if not pmid:
            raise OAResolverError("PMID requerido")

        # Query by external id; request core fields incl. OA and fullTextUrlList.
        query = f"EXT_ID:{pmid} AND SRC:MED"
        r = await client.get(
            f"{self.base_url}/search",
            params={"query": query, "format": "json", "pageSize": 1, "resultType": "core"},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        hits = (data.get("resultList") or {}).get("result") or []
        if not hits:
            raise OAResolverError("Europe PMC no encontró resultado para el PMID")

        item = hits[0]
        is_oa = str(item.get("isOpenAccess") or "").lower() in ("y", "yes", "true", "1")
        if not is_oa:
            raise OAResolverError("Europe PMC: el artículo no está marcado como Open Access")

        ft = (item.get("fullTextUrlList") or {}).get("fullTextUrl") or []
        pdf_url = None
        for u in ft:
            url = (u or {}).get("url")
            if not url:
                continue
            style = str((u or {}).get("documentStyle") or "").lower()
            if style == "pdf" or url.lower().endswith(".pdf"):
                pdf_url = url
                break

        if not pdf_url:
            raise OAResolverError("Europe PMC no devolvió URL PDF open-access")

        return OAResolved(url_for_pdf=pdf_url, source="europepmc")
