from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.billing import BillingUsageEvent
from app.services.llm.presets import USER_TIERS


def _norm_user_id(user_id: UUID | str) -> UUID:
    return UUID(str(user_id)) if not isinstance(user_id, UUID) else user_id


@dataclass
class CanGenerateResult:
    ok: bool
    message: str


class UsageTracker:
    """PostgreSQL-backed usage tracking with monthly limits.

    All writes are fully atomic — no JSON file, no race conditions.
    Pass an open AsyncSession from the request context or create one for
    background tasks.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def record_generation(
        self,
        *,
        user_id: UUID | str,
        sheet_id: UUID | str | None = None,
        preset: str,
        models_used: list[str],
        tokens_total: int,
        cost_usd: float,
        duration_sec: float,
    ) -> None:
        uid = _norm_user_id(user_id)
        sid = UUID(str(sheet_id)) if sheet_id else None

        event = BillingUsageEvent(
            user_id=uid,
            sheet_id=sid,
            preset=preset,
            models_used=models_used,
            tokens_total=int(tokens_total),
            cost_usd=Decimal(str(cost_usd)),
            duration_sec=float(duration_sec),
        )
        self.db.add(event)
        await self.db.flush()

    async def can_generate(self, *, user_id: UUID | str, tier: str) -> CanGenerateResult:
        tier_cfg = USER_TIERS.get(tier, {})
        limit = int(tier_cfg.get("sheets_per_month", 0))

        if limit == -1:
            return CanGenerateResult(ok=True, message="unlimited")

        uid = _norm_user_id(user_id)
        now = datetime.now(tz=timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        result = await self.db.execute(
            select(func.count(BillingUsageEvent.id)).where(
                BillingUsageEvent.user_id == uid,
                BillingUsageEvent.created_at >= month_start,
            )
        )
        used = result.scalar_one() or 0

        if used >= limit:
            return CanGenerateResult(ok=False, message=f"Limit reached ({used}/{limit})")
        return CanGenerateResult(ok=True, message=f"{used}/{limit}")

    async def get_stats(self, *, user_id: UUID | str) -> dict[str, Any]:
        uid = _norm_user_id(user_id)
        now = datetime.now(tz=timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        result = await self.db.execute(
            select(BillingUsageEvent)
            .where(
                BillingUsageEvent.user_id == uid,
                BillingUsageEvent.created_at >= month_start,
            )
            .order_by(BillingUsageEvent.created_at.desc())
        )
        events = result.scalars().all()

        total_tokens = sum(e.tokens_total for e in events)
        total_cost = float(sum(e.cost_usd for e in events))

        recent = [
            {
                "sheet_id": str(e.sheet_id) if e.sheet_id else None,
                "preset": e.preset,
                "models": e.models_used or [],
                "tokens": e.tokens_total,
                "cost": float(e.cost_usd),
                "duration": e.duration_sec,
                "at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events[:10]
        ]

        return {
            "month": now.strftime("%Y-%m"),
            "sheets_this_month": len(events),
            "tokens_this_month": total_tokens,
            "cost_this_month": total_cost,
            "recent": recent,
        }
