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
    used_fallback: bool = False
    oa_url_provided: str | None = None


class PaperDownloadService:
    def __init__(self):
        self.unpaywall = UnpaywallResolver()
        self.europepmc = EuropePMCResolver()

    async def download_open_access_pdf(
        self,
        *,
        doi: str | None,
        pmid: str | None,
        oa_url: str | None = None,
        client: httpx.AsyncClient,
        _original_oa_url: str | None = None,  # internal: tracks original for fallback detection
    ) -> DownloadResult:
        """Resolve OA PDF URL via caller-provided URL, Unpaywall (DOI), or EuropePMC (PMID), then download bytes.

        Priority order:
        1. oa_url provided by caller (from search result the user actually saw)
        2. Unpaywall via DOI
        3. EuropePMC via PMID

        Returns DownloadResult with used_fallback=True when the caller-provided oa_url
        was unusable and the resolver chain was used instead.
        """
        # Track original oa_url for fallback detection across recursive calls.
        original_oa_url = _original_oa_url if _original_oa_url is not None else oa_url

        resolved_url: str | None = None
        source: str | None = None
        last_err: str | None = None

        # Priority 1: Use the exact OA URL the user saw in search results.
        if oa_url:
            resolved_url = oa_url
            source = "user_provided_oa"

        # Priority 2: Unpaywall via DOI.
        if (not resolved_url) and doi:
            try:
                resolved = await self.unpaywall.resolve(doi, client)
                resolved_url, source = resolved.url_for_pdf, resolved.source
            except (OAResolverError, httpx.HTTPError) as e:
                last_err = str(e)
                resolved_url = None
                source = None

        # Priority 3: EuropePMC via PMID.
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
            # If caller-provided URL failed validation, retry with resolvers.
            if oa_url and source == "user_provided_oa":
                return await self.download_open_access_pdf(
                    doi=doi, pmid=pmid, oa_url=None, client=client,
                    _original_oa_url=original_oa_url,
                )
            ct = r.headers.get("content-type")
            raise PaperServiceError(
                f"La URL resuelta no devolvió un PDF válido (content-type={ct})."
            )

        used_fallback = bool(original_oa_url and source != "user_provided_oa")
        return DownloadResult(
            pdf_bytes=data,
            source=source,
            resolved_url=resolved_url,
            used_fallback=used_fallback,
            oa_url_provided=original_oa_url,
        )
