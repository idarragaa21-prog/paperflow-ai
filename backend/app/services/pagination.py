from __future__ import annotations

import base64
from datetime import datetime
import json
from uuid import UUID

from sqlalchemy import and_, or_


def encode_cursor(*, created_at: datetime, row_id: UUID) -> str:
    payload = {"created_at": created_at.isoformat(), "id": str(row_id)}
    return base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")


def decode_cursor(cursor: str | None) -> tuple[datetime, UUID] | None:
    if not cursor:
        return None
    decoded = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
    payload = json.loads(decoded)
    return datetime.fromisoformat(payload["created_at"]), UUID(payload["id"])


def apply_desc_cursor(model, *, created_at, row_id, cursor: str | None):
    parsed = decode_cursor(cursor)
    if parsed is None:
        return None
    cursor_created_at, cursor_id = parsed
    return or_(
        created_at < cursor_created_at,
        and_(created_at == cursor_created_at, row_id < cursor_id),
    )
