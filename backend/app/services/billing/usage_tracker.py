from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.billing import BillingUsageEvent
from app.services.llm.presets import USER_TIERS

DEFAULT_USER_TIER = "free"


def _norm_user_id(user_id: UUID | str) -> UUID:
    return UUID(str(user_id)) if not isinstance(user_id, UUID) else user_id


def _month_start(reference: datetime | None = None) -> datetime:
    now = reference.astimezone(timezone.utc) if reference else datetime.now(tz=timezone.utc)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _period_start(period: str) -> datetime:
    now = datetime.now(tz=timezone.utc)
    normalized = str(period or "month").strip().lower()
    if normalized == "week":
        return now - timedelta(days=7)
    if normalized == "day":
        return now - timedelta(days=1)
    return _month_start(now)


def _coerce_dt(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def _estimate_llm_cost_usd(model: str, tokens_in: int, tokens_out: int) -> float:
    pricing = {
        "claude-sonnet-4-6": {"in": 3.0, "out": 15.0},
        "gpt-4o": {"in": 5.0, "out": 15.0},
        "gpt-4.1": {"in": 2.0, "out": 8.0},
    }
    price = pricing.get(str(model or "").strip())
    if not price:
        return 0.0
    return round((tokens_in / 1_000_000) * price["in"] + (tokens_out / 1_000_000) * price["out"], 6)


def _serialize_models_used(models_used: list[Any] | None, *, tokens_total: int) -> list[dict[str, Any]]:
    items = models_used or []
    if not items:
        return [{"model": "unknown", "tokens_in": int(tokens_total), "tokens_out": 0}]

    if all(isinstance(item, dict) for item in items):
        normalized: list[dict[str, Any]] = []
        for item in items:
            normalized.append(
                {
                    "model": str(item.get("model") or "unknown"),
                    "tokens_in": int(item.get("tokens_in") or 0),
                    "tokens_out": int(item.get("tokens_out") or 0),
                }
            )
        return normalized

    labels = [str(item or "unknown") for item in items]
    share = int(tokens_total / len(labels)) if labels else 0
    remainder = int(tokens_total) - (share * len(labels))
    normalized = []
    for index, label in enumerate(labels):
        normalized.append(
            {
                "model": label,
                "tokens_in": share + (remainder if index == 0 else 0),
                "tokens_out": 0,
            }
        )
    return normalized


def _month_cursor(months_back: int) -> list[str]:
    start = _month_start()
    cursor = start
    out: list[str] = []
    for _ in range(max(months_back, 1)):
        out.append(cursor.strftime("%Y-%m"))
        previous_month = (cursor - timedelta(days=1)).replace(day=1)
        cursor = previous_month
    return out


@dataclass
class CanGenerateResult:
    ok: bool
    message: str


class QuotaExceededError(RuntimeError):
    pass


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
        models_used: list[str] | list[dict[str, Any]],
        tokens_total: int,
        cost_usd: float,
        duration_sec: float | None,
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
            duration_sec=float(duration_sec) if duration_sec is not None else None,
        )
        self.db.add(event)
        await self.db.flush()

    def record_generation(
        self,
        *,
        user_id: UUID | str,
        sheet_id: UUID | str | None = None,
        preset: str,
        models_used: list[str] | list[dict[str, Any]],
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
                "models": _serialize_models_used(models_used, tokens_total=int(tokens_total)),
                "tokens": int(tokens_total),
                "cost": float(cost_usd),
                "duration": float(duration_sec),
                "at": datetime.now(tz=timezone.utc).isoformat(),
            }
        )
        self._save_file_data(payload)
        return None

    async def _track_llm_call_db(
        self,
        *,
        user_id: UUID | str,
        model: str,
        tokens_in: int,
        tokens_out: int,
    ) -> None:
        total_tokens = int(tokens_in) + int(tokens_out)
        cost = _estimate_llm_cost_usd(model, int(tokens_in), int(tokens_out))
        await self._record_generation_db(
            user_id=user_id,
            sheet_id=None,
            preset="llm_call",
            models_used=[{"model": str(model), "tokens_in": int(tokens_in), "tokens_out": int(tokens_out)}],
            tokens_total=total_tokens,
            cost_usd=cost,
            duration_sec=None,
        )

    def track_llm_call(
        self,
        user_id: UUID | str,
        model: str,
        tokens_in: int,
        tokens_out: int,
    ):
        if self.db is not None:
            return self._track_llm_call_db(
                user_id=user_id,
                model=model,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
            )

        payload = self._load_file_data()
        total_tokens = int(tokens_in) + int(tokens_out)
        user_key = str(user_id)
        payload.setdefault(user_key, []).append(
            {
                "sheet_id": None,
                "preset": "llm_call",
                "models": [{"model": str(model), "tokens_in": int(tokens_in), "tokens_out": int(tokens_out)}],
                "tokens": total_tokens,
                "cost": _estimate_llm_cost_usd(model, int(tokens_in), int(tokens_out)),
                "duration": None,
                "at": datetime.now(tz=timezone.utc).isoformat(),
            }
        )
        self._save_file_data(payload)
        return None

    def _build_summary(
        self,
        *,
        events: list[dict[str, Any]],
        period: str,
        tier: str = DEFAULT_USER_TIER,
    ) -> dict[str, Any]:
        tier_cfg = USER_TIERS.get(tier, USER_TIERS[DEFAULT_USER_TIER])
        quota_calls = int(tier_cfg.get("sheets_per_month", 0))
        now = datetime.now(tz=timezone.utc)
        models: dict[str, dict[str, Any]] = defaultdict(lambda: {"model": "unknown", "calls": 0, "tokens_in": 0, "tokens_out": 0, "total_tokens": 0})

        total_tokens = 0
        total_tokens_in = 0
        total_tokens_out = 0
        total_cost = 0.0
        recent: list[dict[str, Any]] = []

        for event in sorted(events, key=lambda item: str(item.get("at") or ""), reverse=True):
            event_models = _serialize_models_used(event.get("models"), tokens_total=int(event.get("tokens") or 0))
            event_tokens_in = sum(int(item.get("tokens_in") or 0) for item in event_models)
            event_tokens_out = sum(int(item.get("tokens_out") or 0) for item in event_models)
            event_total = int(event.get("tokens") or (event_tokens_in + event_tokens_out))
            event_cost = float(event.get("cost") or 0.0)

            total_tokens += event_total
            total_tokens_in += event_tokens_in
            total_tokens_out += event_tokens_out
            total_cost += event_cost

            for item in event_models:
                model_name = str(item.get("model") or "unknown")
                bucket = models[model_name]
                bucket["model"] = model_name
                bucket["calls"] += 1
                bucket["tokens_in"] += int(item.get("tokens_in") or 0)
                bucket["tokens_out"] += int(item.get("tokens_out") or 0)
                bucket["total_tokens"] += int(item.get("tokens_in") or 0) + int(item.get("tokens_out") or 0)

            recent.append(
                {
                    "preset": event.get("preset"),
                    "tokens_in": event_tokens_in,
                    "tokens_out": event_tokens_out,
                    "total_tokens": event_total,
                    "cost_usd": event_cost,
                    "models": event_models,
                    "at": event.get("at"),
                }
            )

        return {
            "period": period,
            "month": now.strftime("%Y-%m"),
            "tier": tier,
            "quota_calls": quota_calls,
            "calls_used": len(events),
            "quota_remaining": -1 if quota_calls == -1 else max(quota_calls - len(events), 0),
            "tokens_in": total_tokens_in,
            "tokens_out": total_tokens_out,
            "total_tokens": total_tokens,
            "cost_usd": round(total_cost, 6),
            "models": list(models.values()),
            "recent": recent[:10],
        }

    async def _load_events_db(self, *, user_id: UUID | str, since: datetime | None = None) -> list[dict[str, Any]]:
        uid = _norm_user_id(user_id)
        stmt = select(BillingUsageEvent).where(BillingUsageEvent.user_id == uid)
        if since is not None:
            stmt = stmt.where(BillingUsageEvent.created_at >= since)
        stmt = stmt.order_by(BillingUsageEvent.created_at.desc())
        result = await self.db.execute(stmt)
        events = result.scalars().all()
        serialized: list[dict[str, Any]] = []
        for event in events:
            serialized.append(
                {
                    "preset": event.preset,
                    "models": event.models_used or [],
                    "tokens": int(event.tokens_total or 0),
                    "cost": float(event.cost_usd or 0),
                    "duration": float(event.duration_sec or 0.0) if event.duration_sec is not None else None,
                    "at": event.created_at.isoformat() if event.created_at else None,
                }
            )
        return serialized

    def _load_events_file(self, *, user_id: UUID | str, since: datetime | None = None) -> list[dict[str, Any]]:
        payload = self._load_file_data()
        events = payload.get(str(user_id), [])
        if since is None:
            return list(events)
        filtered: list[dict[str, Any]] = []
        for event in events:
            event_at = _coerce_dt(event.get("at"))
            if event_at is not None and event_at >= since:
                filtered.append(event)
        return filtered

    async def _get_usage_summary_db(self, *, user_id: UUID | str, period: str = "month") -> dict[str, Any]:
        events = await self._load_events_db(user_id=user_id, since=_period_start(period))
        return self._build_summary(events=events, period=period)

    def get_usage_summary(self, user_id: UUID | str, period: str = "month"):
        if self.db is not None:
            return self._get_usage_summary_db(user_id=user_id, period=period)
        events = self._load_events_file(user_id=user_id, since=_period_start(period))
        return self._build_summary(events=events, period=period)

    def _history_from_events(self, events: list[dict[str, Any]], *, months: int) -> list[dict[str, Any]]:
        buckets: dict[str, dict[str, Any]] = {
            month: {
                "month": month,
                "calls": 0,
                "tokens_in": 0,
                "tokens_out": 0,
                "total_tokens": 0,
                "cost_usd": 0.0,
            }
            for month in _month_cursor(months)
        }

        for event in events:
            event_at = _coerce_dt(event.get("at"))
            if event_at is None:
                continue
            key = event_at.strftime("%Y-%m")
            if key not in buckets:
                continue
            event_models = _serialize_models_used(event.get("models"), tokens_total=int(event.get("tokens") or 0))
            tokens_in = sum(int(item.get("tokens_in") or 0) for item in event_models)
            tokens_out = sum(int(item.get("tokens_out") or 0) for item in event_models)
            total_tokens = int(event.get("tokens") or (tokens_in + tokens_out))
            bucket = buckets[key]
            bucket["calls"] += 1
            bucket["tokens_in"] += tokens_in
            bucket["tokens_out"] += tokens_out
            bucket["total_tokens"] += total_tokens
            bucket["cost_usd"] = round(float(bucket["cost_usd"]) + float(event.get("cost") or 0.0), 6)

        return [buckets[month] for month in _month_cursor(months)]

    async def _get_usage_history_db(self, *, user_id: UUID | str, months: int = 6) -> dict[str, Any]:
        oldest_month = _month_start()
        for _ in range(max(months - 1, 0)):
            oldest_month = (oldest_month - timedelta(days=1)).replace(day=1)
        events = await self._load_events_db(user_id=user_id, since=oldest_month)
        return {"months": self._history_from_events(events, months=months)}

    def get_usage_history(self, user_id: UUID | str, months: int = 6):
        if self.db is not None:
            return self._get_usage_history_db(user_id=user_id, months=months)
        oldest_month = _month_start()
        for _ in range(max(months - 1, 0)):
            oldest_month = (oldest_month - timedelta(days=1)).replace(day=1)
        events = self._load_events_file(user_id=user_id, since=oldest_month)
        return {"months": self._history_from_events(events, months=months)}

    async def _enforce_quota_db(self, *, user_id: UUID | str, tier: str = DEFAULT_USER_TIER) -> None:
        summary = await self._get_usage_summary_db(user_id=user_id, period="month")
        quota_calls = int(summary.get("quota_calls") or 0)
        if quota_calls != -1 and int(summary.get("calls_used") or 0) >= quota_calls:
            raise QuotaExceededError(f"Monthly quota exceeded ({summary['calls_used']}/{quota_calls})")

    def enforce_quota(self, user_id: UUID | str):
        if self.db is not None:
            return self._enforce_quota_db(user_id=user_id)

        summary = self.get_usage_summary(user_id=user_id, period="month")
        quota_calls = int(summary.get("quota_calls") or 0)
        if quota_calls != -1 and int(summary.get("calls_used") or 0) >= quota_calls:
            raise QuotaExceededError(f"Monthly quota exceeded ({summary['calls_used']}/{quota_calls})")
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
