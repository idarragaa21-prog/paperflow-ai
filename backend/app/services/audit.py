from __future__ import annotations

from typing import Any
from uuid import UUID

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
    """Persist an audit log entry.

    Security: callers must ensure `details` does not contain secrets (tokens/headers).
    """

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
