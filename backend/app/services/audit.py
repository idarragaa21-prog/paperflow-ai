from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.models.audit_log import AuditLog
from app.models.user import User


async def log_audit(
    db: AsyncSession,
    *,
    user: User,
    action: str,
    entity_type: str,
    entity_id: UUID,
    details: dict[str, Any] | None = None,
    request: Request | None = None,
) -> None:
    ip: str | None = None
    if request and request.client:
        ip = request.client.host

    entry = AuditLog(
        user_id=user.id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
        ip_address=ip,
    )
    db.add(entry)
    await db.commit()


def extract_paper_download_trace(
    *,
    details: dict[str, Any] | None,
    paper_id: UUID,
    title: str | None = None,
    doi: str | None = None,
    pmid: str | None = None,
    pmcid: str | None = None,
    audited_at=None,
) -> dict[str, Any] | None:
    payload = details or {}
    if not payload:
        return None

    return {
        "title": str(payload.get("title") or title or "Paper"),
        "paper_id": str(payload.get("paper_id") or paper_id),
        "doi": payload.get("doi") or doi,
        "pmid": payload.get("pmid") or pmid,
        "pmcid": payload.get("pmcid") or pmcid,
        "source_provider": payload.get("source_provider") or payload.get("source"),
        "oa_url": payload.get("oa_url"),
        "landing_url": payload.get("landing_url"),
        "resolved_url": payload.get("resolved_url"),
        "used_fallback": bool(payload.get("used_fallback", False)),
        "final_status": payload.get("final_status") or "downloaded",
        "failure_reason": payload.get("failure_reason"),
        "audited_at": audited_at.isoformat() if audited_at else None,
    }


async def get_latest_paper_download_trace(
    db: AsyncSession,
    *,
    paper_id: UUID,
    title: str | None = None,
    doi: str | None = None,
    pmid: str | None = None,
    pmcid: str | None = None,
) -> dict[str, Any] | None:
    stmt = (
        select(AuditLog)
        .where(AuditLog.entity_type == "paper", AuditLog.entity_id == paper_id, AuditLog.action == "download")
        .order_by(AuditLog.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    entry = result.scalars().first()
    if entry is None:
        return None
    return extract_paper_download_trace(
        details=entry.details,
        paper_id=paper_id,
        title=title,
        doi=doi,
        pmid=pmid,
        pmcid=pmcid,
        audited_at=entry.created_at,
    )
