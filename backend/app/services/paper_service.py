from __future__ import annotations

import hashlib
from dataclasses import dataclass

import httpx

from app.core.storage import storage_manager
from app.services.oa_resolvers import EuropePMCResolver, OAResolverError, UnpaywallResolver


class PaperServiceError(Exception):
    pass


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass
class DownloadResult:
    pdf_bytes: bytes
    source: str
    resolved_url: str


class PaperDownloadService:
    def __init__(self):
        self.unpaywall = UnpaywallResolver()
        self.europepmc = EuropePMCResolver()

    async def download_open_access_pdf(
        self,
        *,
        doi: str | None,
        pmid: str | None,
        client: httpx.AsyncClient,
    ) -> DownloadResult:
        """Resolve OA PDF URL via Unpaywall (DOI) or EuropePMC (PMID), then download bytes."""

        resolved_url: str | None = None
        source: str | None = None

        # Prefer DOI via Unpaywall, but when both DOI+PMID are available
        # fall back to Europe PMC if Unpaywall fails (rate limits / missing PDF).
        last_err: str | None = None

        if doi:
            try:
                resolved = await self.unpaywall.resolve(doi, client)
                resolved_url, source = resolved.url_for_pdf, resolved.source
            except (OAResolverError, httpx.HTTPError) as e:
                last_err = str(e)
                resolved_url = None
                source = None

        if (not resolved_url) and pmid:
            try:
                resolved = await self.europepmc.resolve_by_pmid(pmid, client)
                resolved_url, source = resolved.url_for_pdf, resolved.source
            except (OAResolverError, httpx.HTTPError) as e:
                last_err = str(e)
                resolved_url = None
                source = None

        if not resolved_url or not source:
            raise PaperServiceError(last_err or "No se pudo resolver un PDF open-access")

        assert resolved_url and source
        r = await client.get(resolved_url, timeout=60, follow_redirects=True)
        r.raise_for_status()
        data = r.content

        # Hard validation: magic bytes + %%EOF.
        if not storage_manager.validate_pdf(data):
            # Common failure mode: HTML error pages.
            ct = r.headers.get("content-type")
            raise PaperServiceError(
                f"La URL resuelta no devolvió un PDF válido (content-type={ct})."  # no secrets
            )

        return DownloadResult(pdf_bytes=data, source=source, resolved_url=resolved_url)
