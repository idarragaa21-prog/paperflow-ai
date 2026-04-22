from __future__ import annotations

import asyncio
import inspect
from collections import OrderedDict
from typing import Any


def _patch_paper_record_response() -> None:
    try:
        from app.schemas import papers as paper_schemas
    except Exception:
        return

    current = getattr(paper_schemas, "PaperRecordResponse", None)
    if current is None or "resolved_url" in getattr(current, "model_fields", {}):
        return

    class PaperRecordResponse(current):  # type: ignore[misc, valid-type]
        resolved_url: str | None = None
        landing_url: str | None = None
        used_fallback: bool = False

    PaperRecordResponse.__name__ = "PaperRecordResponse"
    PaperRecordResponse.__qualname__ = "PaperRecordResponse"
    paper_schemas.PaperRecordResponse = PaperRecordResponse


def _patch_individual_download_trace() -> None:
    try:
        from sqlalchemy import text

        from app.services.paper_service import PaperDownloadService
    except Exception:
        return

    if getattr(PaperDownloadService, "_paperflow_trace_patch", False):
        return

    original_resolve = getattr(PaperDownloadService, "resolve_open_access_target", None)
    original_download = getattr(PaperDownloadService, "download_and_store_from_metadata", None)

    if not original_resolve or not original_download:
        return

    async def resolve_with_trace(self: Any, *args: Any, **kwargs: Any) -> Any:
        target = await original_resolve(self, *args, **kwargs)
        self._paperflow_last_download_trace = {
            "source_provider": getattr(target, "source", None),
            "oa_url": getattr(target, "oa_url", None),
            "landing_url": getattr(target, "landing_url", None),
            "resolved_url": getattr(target, "resolved_url", None),
            "used_fallback": bool(getattr(target, "used_fallback", False)),
        }
        return target

    async def download_with_trace(self: Any, *args: Any, **kwargs: Any) -> Any:
        self._paperflow_last_download_trace = None
        result = await original_download(self, *args, **kwargs)
        trace = dict(getattr(self, "_paperflow_last_download_trace", {}) or {})
        if not trace:
            return result

        if result is not None:
            for field in ("source_provider", "oa_url", "landing_url", "resolved_url", "used_fallback"):
                try:
                    setattr(result, field, trace.get(field))
                except Exception:
                    pass
            if isinstance(result, dict):
                result.update(trace)

        db = kwargs.get("db")
        if db is None and args:
            db = args[0]

        paper_id = getattr(result, "id", None)
        if paper_id is None and isinstance(result, dict):
            paper_id = result.get("id")

        if db is not None and paper_id is not None:
            payload = {
                "paper_id": str(paper_id),
                "source_provider": trace.get("source_provider"),
                "source": trace.get("source_provider"),
                "oa_url": trace.get("oa_url"),
                "landing_url": trace.get("landing_url"),
                "resolved_url": trace.get("resolved_url"),
                "used_fallback": bool(trace.get("used_fallback")),
            }
            try:
                db.execute(
                    text(
                        """
                        WITH last_audit AS (
                          SELECT id
                          FROM audit_logs
                          WHERE action = 'download' AND entity_type = 'paper' AND entity_id = :paper_id::uuid
                          ORDER BY created_at DESC
                          LIMIT 1
                        )
                        UPDATE audit_logs
                        SET details = COALESCE(details, '{}'::jsonb) || jsonb_strip_nulls(
                          jsonb_build_object(
                            'source_provider', :source_provider,
                            'source', :source,
                            'oa_url', :oa_url,
                            'landing_url', :landing_url,
                            'resolved_url', :resolved_url,
                            'used_fallback', :used_fallback
                          )
                        )
                        WHERE id IN (SELECT id FROM last_audit)
                        """
                    ),
                    payload,
                )
                flush = getattr(db, "flush", None)
                if callable(flush):
                    flush()
            except Exception:
                pass

        return result

    PaperDownloadService.resolve_open_access_target = resolve_with_trace
    PaperDownloadService.download_and_store_from_metadata = download_with_trace
    PaperDownloadService._paperflow_trace_patch = True


def _metadata_score(item: dict[str, Any]) -> int:
    score = 0
    if item.get("doi"):
        score += 40
    if item.get("pmid"):
        score += 26
    if item.get("pmcid"):
        score += 14

    abstract = str(item.get("abstract") or "").strip()
    if len(abstract) >= 1200:
        score += 28
    elif len(abstract) >= 700:
        score += 22
    elif len(abstract) >= 300:
        score += 16
    elif abstract:
        score += 8

    if item.get("oa_url"):
        score += 15
    if item.get("journal"):
        score += 10
    if isinstance(item.get("pub_year"), int):
        score += 8
    if item.get("authors"):
        score += 8

    source = str(item.get("source") or "").lower()
    source_rank = {"pubmed": 12, "europepmc": 10, "doaj": 8, "unpaywall": 6}.get(source, 0)
    score += source_rank
    return score


def _merge_duplicate_group(module: Any, items: list[dict[str, Any]]) -> dict[str, Any]:
    best = max(items, key=_metadata_score).copy()
    best["authors"] = list(best.get("authors") or [])
    best["open_targets"] = list(best.get("open_targets") or [])

    for candidate in sorted(items, key=_metadata_score, reverse=True):
        if not best.get("doi") and candidate.get("doi"):
            best["doi"] = candidate["doi"]
        if not best.get("pmid") and candidate.get("pmid"):
            best["pmid"] = candidate["pmid"]
        if not best.get("pmcid") and candidate.get("pmcid"):
            best["pmcid"] = candidate["pmcid"]
        if not best.get("journal") and candidate.get("journal"):
            best["journal"] = candidate["journal"]
        if not best.get("pub_year") and candidate.get("pub_year"):
            best["pub_year"] = candidate["pub_year"]
        if not best.get("language") and candidate.get("language"):
            best["language"] = candidate["language"]
        if not best.get("oa_url") and candidate.get("oa_url"):
            best["oa_url"] = candidate["oa_url"]
        if len(str(candidate.get("abstract") or "")) > len(str(best.get("abstract") or "")):
            best["abstract"] = candidate.get("abstract")
        if len(list(candidate.get("authors") or [])) > len(list(best.get("authors") or [])):
            best["authors"] = list(candidate.get("authors") or [])
        if not best.get("source") and candidate.get("source"):
            best["source"] = candidate["source"]

        merged_targets = []
        seen_targets: set[tuple[str, str]] = set()
        for target in [*(best.get("open_targets") or []), *(candidate.get("open_targets") or [])]:
            if not isinstance(target, dict):
                continue
            key = (str(target.get("kind") or ""), str(target.get("url") or ""))
            if key in seen_targets or not key[1]:
                continue
            seen_targets.add(key)
            merged_targets.append(target)
        best["open_targets"] = merged_targets

        if candidate.get("is_open_access"):
            best["is_open_access"] = True
        if candidate.get("has_abstract"):
            best["has_abstract"] = True
        if candidate.get("can_save_pdf"):
            best["can_save_pdf"] = True
        if candidate.get("can_open_external"):
            best["can_open_external"] = True

    return module.enrich_search_result(best)


async def _call_with_signature(fn: Any, **kwargs: Any) -> Any:
    signature = inspect.signature(fn)
    usable = {key: value for key, value in kwargs.items() if key in signature.parameters}
    return await fn(**usable)


def _patch_federated_ranking() -> None:
    try:
        from app.services import federated_search as module
    except Exception:
        return

    if getattr(module, "_paperflow_rank_patch", False):
        return

    original = module.federated_search

    async def federated_search(query: str, max_results: int = 20, filters: Any = None, **kwargs: Any) -> dict[str, Any]:
        try:
            result = await original(query=query, max_results=max_results, filters=filters, **kwargs)
        except TypeError:
            result = await original(query, max_results, filters)

        results = list(result.get("results") or [])
        if not results:
            return result

        grouped: "OrderedDict[str, list[dict[str, Any]]]" = OrderedDict()
        for item in results:
            grouped.setdefault(module._record_key(item), []).append(item)

        reranked = [_merge_duplicate_group(module, group) for group in grouped.values()]
        reranked.sort(
            key=lambda item: (
                _metadata_score(item),
                int(item.get("pub_year") or 0),
                bool(item.get("oa_url")),
                len(str(item.get("abstract") or "")),
            ),
            reverse=True,
        )
        result["results"] = reranked[:max_results]
        return result

    module.federated_search = federated_search
    module._paperflow_rank_patch = True


_patch_paper_record_response()
_patch_individual_download_trace()
_patch_federated_ranking()
