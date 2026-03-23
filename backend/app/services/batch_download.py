from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.core.logger import logger
from app.core.storage import storage_manager
from app.models.paper import Paper
from app.services.audit import log_audit
from app.services.paper_repo import PaperRepository
from app.services.paper_service import PaperServiceError, PaperDownloadService, sha256_hex


@dataclass
class BatchDownloadResult:
    downloaded: list[dict[str, Any]]
    already_exists: list[dict[str, Any]]
    not_available: list[dict[str, Any]]
    failed: list[dict[str, Any]]


def _paper_trace(
    *,
    pmid: str | None,
    doi: str | None,
    title: str | None,
    oa_url: str | None = None,
    resolved_url: str | None = None,
    source_provider: str | None = None,
    used_fallback: bool = False,
    final_status: str,
    paper_id: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    """Produce a per-paper traceability record for batch download results."""
    return {
        "pmid": pmid,
        "doi": doi,
        "title": title,
        "oa_url": oa_url,
        "resolved_url": resolved_url,
        "source_provider": source_provider,
        "used_fallback": used_fallback,
        "final_status": final_status,
        "paper_id": paper_id,
        "reason": reason,
    }


async def batch_download_papers(
    *,
    repo: PaperRepository,
    downloader: PaperDownloadService,
    client: httpx.AsyncClient,
    user,
    project_id,
    papers: list[dict[str, Any]],
    progress_cb=None,
) -> BatchDownloadResult:
    """Download multiple OA papers and persist them.

    The returned structure is designed to be stored into Job.result.output.
    Each entry in every list carries full per-paper traceability:
    pmid, doi, title, oa_url (provided), resolved_url (used), source_provider,
    used_fallback, final_status, paper_id (if persisted), reason (if failed).
    """

    downloaded: list[dict[str, Any]] = []
    already_exists: list[dict[str, Any]] = []
    not_available: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []

    total = max(len(papers), 1)
    for idx, it in enumerate(papers):
        pmid = (it.get("pmid") or None)
        pmcid = (it.get("pmcid") or None)
        doi = (it.get("doi") or None)
        oa_url = (it.get("oa_url") or None)
        title = (it.get("title") or None) or doi or pmid or "Paper"

        try:
            # Dedup 1: identifiers
            dup = await repo.find_duplicate_by_identifiers(project_id=project_id, pmid=pmid, doi=doi)
            if dup:
                already_exists.append(_paper_trace(
                    pmid=pmid, doi=doi, title=title,
                    oa_url=oa_url,
                    final_status="existing",
                    paper_id=str(dup.id),
                    reason="Duplicate identifier",
                ))
                continue

            # Resolve OA URL with priority:
            # 0) Caller-provided oa_url (from search result the user saw)
            # 1) Europe PMC if PMCID exists (uses PMID query)
            # 2) Unpaywall if DOI exists
            # 3) otherwise not_available
            resolved_url: str | None = None
            source: str | None = None
            last_err: str | None = None

            # Priority 0: caller-provided OA URL from search results.
            if oa_url:
                resolved_url = oa_url
                source = "user_provided_oa"

            if (not resolved_url) and pmcid and pmid:
                try:
                    r = await downloader.europepmc.resolve_by_pmid(pmid, client)
                    resolved_url, source = r.url_for_pdf, r.source
                except Exception as e:
                    last_err = str(e)

            if (not resolved_url) and doi:
                try:
                    r = await downloader.unpaywall.resolve(doi, client)
                    resolved_url, source = r.url_for_pdf, r.source
                except Exception as e:
                    last_err = str(e)

            if (not resolved_url) and (not pmcid) and pmid:
                try:
                    r = await downloader.europepmc.resolve_by_pmid(pmid, client)
                    resolved_url, source = r.url_for_pdf, r.source
                except Exception as e:
                    last_err = str(e)

            if not resolved_url or not source:
                not_available.append(_paper_trace(
                    pmid=pmid, doi=doi, title=title,
                    oa_url=oa_url,
                    final_status="unavailable",
                    reason=last_err or "No OA source found",
                ))
                continue

            # Download
            used_fallback = False
            final_resolved_url = resolved_url
            final_source = source

            resp = await client.get(resolved_url, timeout=60, follow_redirects=True)
            resp.raise_for_status()
            pdf_bytes = resp.content

            if not storage_manager.validate_pdf(pdf_bytes):
                # If this was a user-provided URL, retry with resolver chain.
                if source == "user_provided_oa":
                    fallback_url = None
                    fallback_source = None
                    if pmcid and pmid:
                        try:
                            r = await downloader.europepmc.resolve_by_pmid(pmid, client)
                            fallback_url, fallback_source = r.url_for_pdf, r.source
                        except Exception:
                            pass
                    if (not fallback_url) and doi:
                        try:
                            r = await downloader.unpaywall.resolve(doi, client)
                            fallback_url, fallback_source = r.url_for_pdf, r.source
                        except Exception:
                            pass
                    if fallback_url and fallback_source:
                        resp2 = await client.get(fallback_url, timeout=60, follow_redirects=True)
                        resp2.raise_for_status()
                        pdf_bytes = resp2.content
                        final_resolved_url = fallback_url
                        final_source = fallback_source
                        used_fallback = True
                        if not storage_manager.validate_pdf(pdf_bytes):
                            ct = resp2.headers.get("content-type")
                            raise PaperServiceError(f"Resolved URL did not return a valid PDF (content-type={ct})")
                    else:
                        ct = resp.headers.get("content-type")
                        raise PaperServiceError(f"Resolved URL did not return a valid PDF (content-type={ct})")
                else:
                    ct = resp.headers.get("content-type")
                    raise PaperServiceError(f"Resolved URL did not return a valid PDF (content-type={ct})")

            content_hash = sha256_hex(pdf_bytes)

            # Dedup 2: content hash
            dup2 = await repo.find_duplicate_by_hash(project_id=project_id, content_hash=content_hash)
            if dup2:
                already_exists.append(_paper_trace(
                    pmid=pmid, doi=doi, title=title,
                    oa_url=oa_url,
                    resolved_url=final_resolved_url,
                    source_provider=final_source,
                    used_fallback=used_fallback,
                    final_status="existing",
                    paper_id=str(dup2.id),
                    reason="Duplicate content hash",
                ))
                continue

            saved = await storage_manager.save_paper_bytes(
                data=pdf_bytes,
                project_id=project_id,
                suggested_filename=(title + ".pdf") if title else None,
            )

            paper = Paper(
                project_id=project_id,
                title=title,
                authors=None,
                doi=doi,
                pmid=pmid,
                pmcid=pmcid,
                source_provider=final_source,
                source_type="download",
                is_open_access=True,
                oa_url=final_resolved_url,
                filename=saved["filename"],
                file_path=saved["file_path"],
                file_size_kb=saved["size_kb"],
                content_hash=saved["content_hash"],
            )

            paper = await repo.create_paper(paper)

            # audit (no request in worker). Only for SQL repo.
            if hasattr(repo, "db"):
                try:
                    await log_audit(
                        repo.db,  # type: ignore[arg-type]
                        user=user,
                        action="download",
                        entity_type="paper",
                        entity_id=paper.id,
                        details={
                            "project_id": str(project_id),
                            "source_provider": final_source,
                            "resolved_url": final_resolved_url,
                            "oa_url_provided": oa_url,
                            "used_fallback": used_fallback,
                            "doi": doi,
                            "pmid": pmid,
                            "pmcid": pmcid,
                            "filename": paper.filename,
                            "size_kb": paper.file_size_kb,
                            "content_hash": paper.content_hash,
                        },
                        request=None,
                    )
                except Exception:
                    pass

            downloaded.append(_paper_trace(
                pmid=pmid, doi=doi, title=title,
                oa_url=oa_url,
                resolved_url=final_resolved_url,
                source_provider=final_source,
                used_fallback=used_fallback,
                final_status="downloaded",
                paper_id=str(paper.id),
            ))

        except PaperServiceError as e:
            not_available.append(_paper_trace(
                pmid=pmid, doi=doi, title=title,
                oa_url=oa_url,
                final_status="unavailable",
                reason=str(e),
            ))
        except Exception as e:
            logger.warning(f"batch download failed pmid={pmid} doi={doi}: {e}")
            failed.append(_paper_trace(
                pmid=pmid, doi=doi, title=title,
                oa_url=oa_url,
                final_status="failed",
                reason=str(e),
            ))
        finally:
            if progress_cb:
                try:
                    import inspect

                    r = progress_cb(idx + 1, total)
                    if inspect.isawaitable(r):
                        await r
                except Exception:
                    pass

    return BatchDownloadResult(
        downloaded=downloaded,
        already_exists=already_exists,
        not_available=not_available,
        failed=failed,
    )
