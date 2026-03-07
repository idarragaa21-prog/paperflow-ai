from __future__ import annotations

import hashlib
from dataclasses import dataclass

import httpx

from app.core.storage import storage_manager
from app.services.oa_resolvers import OAResolverError, normalize_reference_identity, resolve_open_access_pdf


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
    async def download_open_access_pdf(
        self,
        *,
        doi: str | None,
        pmid: str | None,
        client: httpx.AsyncClient,
    ) -> DownloadResult:
        try:
            resolved = await resolve_open_access_pdf(doi=doi, pmid=pmid, client=client)
        except (OAResolverError, httpx.HTTPError) as exc:
            raise PaperServiceError(str(exc)) from exc

        r = await client.get(resolved.url_for_pdf, timeout=60, follow_redirects=True)
        r.raise_for_status()
        data = r.content

        # Hard validation: magic bytes + %%EOF.
        if not storage_manager.validate_pdf(data):
            # Common failure mode: HTML error pages.
            ct = r.headers.get("content-type")
            raise PaperServiceError(
                f"La URL resuelta no devolvió un PDF válido (content-type={ct})."  # no secrets
            )

        return DownloadResult(pdf_bytes=data, source=resolved.source, resolved_url=resolved.url_for_pdf)


def canonical_reference_identity(*, doi: str | None, pmid: str | None, title: str | None, source: str | None) -> dict:
    return normalize_reference_identity(doi=doi, pmid=pmid, title=title, source=source)
