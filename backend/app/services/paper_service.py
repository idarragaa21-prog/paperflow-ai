from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass

import httpx

from app.core.storage import storage_manager
from app.services.oa_resolvers import (
    DOIContentNegotiationResolver,
    EuropePMCResolver,
    OAResolverError,
    UnpaywallResolver,
    normalize_reference_identity,
)


class PaperServiceError(Exception):
    pass


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass
class DownloadResult:
    pdf_bytes: bytes
    source: str
    resolved_url: str
    oa_url: str | None = None
    landing_url: str | None = None
    used_fallback: bool = False


@dataclass
class OAResolutionTrace:
    source: str
    resolved_url: str
    oa_url: str | None = None
    landing_url: str | None = None
    used_fallback: bool = False


def _normalized_error_message(exc: Exception) -> str:
    return str(exc).strip() or exc.__class__.__name__


class PaperDownloadService:
    def __init__(self) -> None:
        self.europepmc = EuropePMCResolver()
        self.unpaywall = UnpaywallResolver()
        self.doi_content_negotiation = DOIContentNegotiationResolver()

    async def resolve_open_access_target(
        self,
        *,
        doi: str | None,
        pmid: str | None,
        pmcid: str | None = None,
        client: httpx.AsyncClient,
    ) -> OAResolutionTrace:
        attempts: list[str] = []
        resolvers: list[tuple[str, Callable[[], object]]] = []

        if pmcid and pmid:
            resolvers.append(("europepmc", lambda: self.europepmc.resolve_by_pmid(pmid, client)))
        if doi:
            resolvers.append(("unpaywall", lambda: self.unpaywall.resolve(doi, client)))
            resolvers.append(("doi_content_negotiation", lambda: self.doi_content_negotiation.resolve(doi, client)))
        if (not pmcid) and pmid:
            resolvers.append(("europepmc", lambda: self.europepmc.resolve_by_pmid(pmid, client)))

        for index, (name, resolver) in enumerate(resolvers):
            try:
                resolved = await resolver()
                return OAResolutionTrace(
                    source=resolved.source,
                    resolved_url=resolved.url_for_pdf,
                    oa_url=resolved.oa_url or resolved.url_for_pdf,
                    landing_url=resolved.landing_url,
                    used_fallback=index > 0,
                )
            except (OAResolverError, httpx.HTTPError) as exc:
                attempts.append(f"{name}: {_normalized_error_message(exc)}")

        raise PaperServiceError("; ".join(attempts) or "No se pudo resolver un PDF open-access")

    async def download_open_access_pdf(
        self,
        *,
        doi: str | None,
        pmid: str | None,
        pmcid: str | None = None,
        oa_url: str | None = None,
        client: httpx.AsyncClient,
    ) -> DownloadResult:
        resolved = None
        if oa_url:
            resolved = OAResolutionTrace(
                source="user_provided_oa",
                resolved_url=oa_url,
                oa_url=oa_url,
                landing_url=None,
                used_fallback=False,
            )
        else:
            try:
                resolved = await self.resolve_open_access_target(doi=doi, pmid=pmid, pmcid=pmcid, client=client)
            except PaperServiceError as exc:
                raise PaperServiceError(str(exc)) from exc

        r = await client.get(resolved.resolved_url, timeout=60, follow_redirects=True)
        r.raise_for_status()
        data = r.content

        if not storage_manager.validate_pdf(data):
            if oa_url and resolved.source == "user_provided_oa":
                try:
                    resolved = await self.resolve_open_access_target(doi=doi, pmid=pmid, pmcid=pmcid, client=client)
                except PaperServiceError as exc:
                    raise PaperServiceError(str(exc)) from exc
                r = await client.get(resolved.resolved_url, timeout=60, follow_redirects=True)
                r.raise_for_status()
                data = r.content
            if not storage_manager.validate_pdf(data):
                ct = r.headers.get("content-type")
                raise PaperServiceError(f"La URL resuelta no devolvió un PDF válido (content-type={ct}).")

        return DownloadResult(
            pdf_bytes=data,
            source=resolved.source,
            resolved_url=str(r.url),
            oa_url=resolved.oa_url,
            landing_url=resolved.landing_url,
            used_fallback=resolved.used_fallback,
        )


def canonical_reference_identity(*, doi: str | None, pmid: str | None, title: str | None, source: str | None) -> dict:
    return normalize_reference_identity(doi=doi, pmid=pmid, title=title, source=source)
