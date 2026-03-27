from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.billing import BillingUsageEvent
from app.services.llm.presets import USER_TIERS


def _norm_user_id(user_id: UUID | str) -> UUID:
    return UUID(str(user_id)) if not isinstance(user_id, UUID) else user_id


def _month_start() -> datetime:
    now = datetime.now(tz=timezone.utc)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


@dataclass
class CanGenerateResult:
    ok: bool
    message: str


class UsageTracker:
    """Usage tracker with DB mode for app code and JSON mode for local/test flows."""

    def __init__(self, db: AsyncSession | None = None, *, path: str | Path | None = None) -> None:
        self.db = db
        self.path = Path(path) if path is not None else None
        if self.db is None and self.path is None:
            raise ValueError("UsageTracker requires either db or path")

    def _load_file_data(self) -> dict[str, list[dict[str, Any]]]:
        if self.path is None or not self.path.exists():
            return {}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
        return payload if isinstance(payload, dict) else {}

    def _save_file_data(self, payload: dict[str, list[dict[str, Any]]]) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    async def _record_generation_db(
        self,
        *,
        user_id: UUID | str,
        sheet_id: UUID | str | None,
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

    def record_generation(
        self,
        *,
        user_id: UUID | str,
        sheet_id: UUID | str | None = None,
        preset: str,
        models_used: list[str],
        tokens_total: int,
        cost_usd: float,
        duration_sec: float,
    ):
        if self.db is not None:
            return self._record_generation_db(
                user_id=user_id,
                sheet_id=sheet_id,
                preset=preset,
                models_used=models_used,
                tokens_total=tokens_total,
                cost_usd=cost_usd,
                duration_sec=duration_sec,
            )

        payload = self._load_file_data()
        user_key = str(user_id)
        payload.setdefault(user_key, []).append(
            {
                "sheet_id": str(sheet_id) if sheet_id else None,
                "preset": preset,
                "models": list(models_used),
                "tokens": int(tokens_total),
                "cost": float(cost_usd),
                "duration": float(duration_sec),
                "at": datetime.now(tz=timezone.utc).isoformat(),
            }
        )
        self._save_file_data(payload)
        return None

    async def _can_generate_db(self, *, user_id: UUID | str, tier: str) -> CanGenerateResult:
        tier_cfg = USER_TIERS.get(tier, {})
        limit = int(tier_cfg.get("sheets_per_month", 0))

        if limit == -1:
            return CanGenerateResult(ok=True, message="unlimited")

        uid = _norm_user_id(user_id)
        month_start = _month_start()

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

    def can_generate(self, *, user_id: UUID | str, tier: str):
        if self.db is not None:
            return self._can_generate_db(user_id=user_id, tier=tier)

        tier_cfg = USER_TIERS.get(tier, {})
        limit = int(tier_cfg.get("sheets_per_month", 0))
        if limit == -1:
            return CanGenerateResult(ok=True, message="unlimited")

        stats = self.get_stats(user_id=user_id)
        used = int(stats["sheets_this_month"])
        if used >= limit:
            return CanGenerateResult(ok=False, message=f"Limit reached ({used}/{limit})")
        return CanGenerateResult(ok=True, message=f"{used}/{limit}")

    async def _get_stats_db(self, *, user_id: UUID | str) -> dict[str, Any]:
        uid = _norm_user_id(user_id)
        month_start = _month_start()
        now = datetime.now(tz=timezone.utc)

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

    def get_stats(self, *, user_id: UUID | str):
        if self.db is not None:
            return self._get_stats_db(user_id=user_id)

        now = datetime.now(tz=timezone.utc)
        month_prefix = now.strftime("%Y-%m")
        payload = self._load_file_data()
        events = [
            event
            for event in payload.get(str(user_id), [])
            if str(event.get("at") or "").startswith(month_prefix)
        ]
        recent = sorted(events, key=lambda item: str(item.get("at") or ""), reverse=True)[:10]
        return {
            "month": month_prefix,
            "sheets_this_month": len(events),
            "tokens_this_month": sum(int(event.get("tokens") or 0) for event in events),
            "cost_this_month": float(sum(float(event.get("cost") or 0.0) for event in events)),
            "recent": recent,
        }
