from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.core.storage import storage_manager
from app.models.paper import Paper
from app.services.audit import get_latest_paper_download_trace, log_audit
from app.services.paper_repo import PaperRepository
from app.services.paper_service import PaperServiceError, PaperDownloadService, sha256_hex


@dataclass
class BatchDownloadTraceItem:
    title: str
    pmid: str | None
    pmcid: str | None
    doi: str | None
    paper_id: str | None
    source_provider: str | None
    oa_url: str | None
    landing_url: str | None
    resolved_url: str | None
    used_fallback: bool
    final_status: str
    failure_reason: str | None = None


@dataclass
class BatchDownloadResult:
    items: list[dict[str, Any]]
    downloaded: list[dict[str, Any]]
    already_exists: list[dict[str, Any]]
    not_available: list[dict[str, Any]]
    failed: list[dict[str, Any]]

    def to_output(self) -> dict[str, Any]:
        return {
            "items": self.items,
            "downloaded": self.downloaded,
            "already_exists": self.already_exists,
            "not_available": self.not_available,
            "failed": self.failed,
        }


def _trace_item(**kwargs: Any) -> dict[str, Any]:
    return asdict(BatchDownloadTraceItem(**kwargs))


async def _enrich_trace_from_existing_audit(
    *,
    db: AsyncSession | None,
    paper: Paper,
    trace: dict[str, Any],
) -> None:
    if db is None:
        return

    audit_trace = await get_latest_paper_download_trace(
        db,
        paper_id=paper.id,
        title=paper.title,
        doi=paper.doi,
        pmid=paper.pmid,
        pmcid=paper.pmcid,
    )
    if not audit_trace:
        return

    trace.update(
        source_provider=audit_trace.get("source_provider") or trace.get("source_provider"),
        oa_url=audit_trace.get("oa_url") or trace.get("oa_url"),
        landing_url=audit_trace.get("landing_url") or trace.get("landing_url"),
        resolved_url=audit_trace.get("resolved_url") or trace.get("resolved_url"),
        used_fallback=bool(audit_trace.get("used_fallback", trace.get("used_fallback", False))),
        failure_reason=audit_trace.get("failure_reason") or trace.get("failure_reason"),
    )


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
    """

    items: list[dict[str, Any]] = []
    downloaded: list[dict[str, Any]] = []
    already_exists: list[dict[str, Any]] = []
    not_available: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []

    total = max(len(papers), 1)
    repo_db = getattr(repo, "db", None)
    for idx, it in enumerate(papers):
        pmid = (it.get("pmid") or None)
        pmcid = (it.get("pmcid") or None)
        doi = (it.get("doi") or None)
        title = (it.get("title") or None) or doi or pmid or "Paper"
        trace: dict[str, Any] = _trace_item(
            title=title,
            pmid=pmid,
            pmcid=pmcid,
            doi=doi,
            paper_id=None,
            source_provider=None,
            oa_url=None,
            landing_url=None,
            resolved_url=None,
            used_fallback=False,
            final_status="failed",
            failure_reason=None,
        )

        try:
            # Dedup 1: identifiers
            dup = await repo.find_duplicate_by_identifiers(project_id=project_id, pmid=pmid, doi=doi)
            if dup:
                trace.update(
                    paper_id=str(dup.id),
                    source_provider=getattr(dup, "source_provider", None),
                    oa_url=getattr(dup, "oa_url", None),
                    final_status="existing",
                )
                await _enrich_trace_from_existing_audit(db=repo_db, paper=dup, trace=trace)
                already_exists.append(dict(trace))
                items.append(dict(trace))
                continue

            try:
                resolution = await downloader.resolve_open_access_target(
                    doi=doi,
                    pmid=pmid,
                    pmcid=pmcid,
                    client=client,
                )
            except Exception as exc:
                raise PaperServiceError(str(exc)) from exc
            trace.update(
                source_provider=resolution.source,
                oa_url=resolution.oa_url,
                landing_url=resolution.landing_url,
                resolved_url=resolution.resolved_url,
                used_fallback=resolution.used_fallback,
            )

            resp = await client.get(resolution.resolved_url, timeout=60, follow_redirects=True)
            resp.raise_for_status()
            pdf_bytes = resp.content
            trace["resolved_url"] = str(resp.url)

            if not storage_manager.validate_pdf(pdf_bytes):
                ct = resp.headers.get("content-type")
                raise PaperServiceError(f"Resolved URL did not return a valid PDF (content-type={ct})")

            content_hash = sha256_hex(pdf_bytes)

            # Dedup 2: content hash
            dup2 = await repo.find_duplicate_by_hash(project_id=project_id, content_hash=content_hash)
            if dup2:
                trace.update(
                    paper_id=str(dup2.id),
                    source_provider=getattr(dup2, "source_provider", None) or trace["source_provider"],
                    oa_url=getattr(dup2, "oa_url", None) or trace["oa_url"],
                    final_status="existing",
                )
                await _enrich_trace_from_existing_audit(db=repo_db, paper=dup2, trace=trace)
                already_exists.append(dict(trace))
                items.append(dict(trace))
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
                source_provider=trace["source_provider"],
                source_type="download",
                is_open_access=True,
                oa_url=trace["oa_url"] or trace["resolved_url"],
                filename=saved["filename"],
                file_path=saved["file_path"],
                file_size_kb=saved["size_kb"],
                content_hash=saved["content_hash"],
                downloaded_at=datetime.utcnow(),
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
                            "paper_id": str(paper.id),
                            "title": paper.title,
                            "source": trace["source_provider"],
                            "source_provider": trace["source_provider"],
                            "oa_url": trace["oa_url"],
                            "resolved_url": trace["resolved_url"],
                            "landing_url": trace["landing_url"],
                            "used_fallback": trace["used_fallback"],
                            "final_status": "downloaded",
                            "failure_reason": None,
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

            trace.update(paper_id=str(paper.id), final_status="downloaded")
            downloaded.append(dict(trace))
            items.append(dict(trace))
        except PaperServiceError as e:
            trace.update(final_status="unavailable", failure_reason=str(e))
            not_available.append(dict(trace))
            items.append(dict(trace))
        except Exception as e:
            logger.warning(f"batch download failed pmid={pmid} doi={doi}: {e}")
            trace.update(final_status="failed", failure_reason=str(e))
            failed.append(dict(trace))
            items.append(dict(trace))
        finally:
            if progress_cb:
                try:
                    import inspect

                    snapshot = {
                        "items": items,
                        "downloaded": downloaded,
                        "already_exists": already_exists,
                        "not_available": not_available,
                        "failed": failed,
                    }
                    r = progress_cb(idx + 1, total, snapshot)
                    if inspect.isawaitable(r):
                        await r
                except Exception:
                    pass

    return BatchDownloadResult(
        items=items,
        downloaded=downloaded,
        already_exists=already_exists,
        not_available=not_available,
        failed=failed,
    )
