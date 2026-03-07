from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from app.config import settings
from app.services.llm.presets import USER_TIERS


def _norm_user_id(user_id: UUID | str) -> str:
    return str(user_id)


@dataclass
class CanGenerateResult:
    ok: bool
    message: str


class UsageTracker:
    """Lightweight usage tracking with monthly limits.

    Storage:
      - JSON file under STORAGE_BASE_PATH/data/usage.json by default.

    Notes:
      - This is scaffolding for billing hooks; it is intentionally file-backed
        to avoid schema changes.
      - user_id is normalized to string (UUID-safe).
    """

    def __init__(self, *, path: str | Path | None = None):
        if path is None:
            base = Path(settings.STORAGE_BASE_PATH).expanduser().resolve()
            path = base / "data" / "usage.json"
        self.path = Path(path)
        self.usage: dict[str, Any] = self._load()

    def _load(self) -> dict[str, Any]:
        if self.path.exists():
            with self.path.open("r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(self.usage, f, indent=2, ensure_ascii=False, default=str)
        os.replace(tmp, self.path)

    def record_generation(
        self,
        *,
        user_id: UUID | str,
        sheet_id: UUID | str,
        preset: str,
        models_used: list[str],
        tokens_total: int,
        cost_usd: float,
        duration_sec: float,
    ) -> None:
        uid = _norm_user_id(user_id)
        month = datetime.now().strftime("%Y-%m")

        self.usage.setdefault(uid, {})
        self.usage[uid].setdefault(month, {"sheets": 0, "tokens": 0, "cost": 0.0, "log": []})

        entry = self.usage[uid][month]
        entry["sheets"] += 1
        entry["tokens"] += int(tokens_total)
        entry["cost"] += float(cost_usd)
        entry["log"].append(
            {
                "sheet_id": str(sheet_id),
                "preset": preset,
                "models": list(models_used),
                "tokens": int(tokens_total),
                "cost": float(cost_usd),
                "duration": float(duration_sec),
                "at": datetime.now().isoformat(),
            }
        )

        self._save()

    def can_generate(self, *, user_id: UUID | str, tier: str) -> CanGenerateResult:
        uid = _norm_user_id(user_id)
        tier_cfg = USER_TIERS.get(tier, {})
        limit = int(tier_cfg.get("sheets_per_month", 0))

        if limit == -1:
            return CanGenerateResult(ok=True, message="unlimited")

        month = datetime.now().strftime("%Y-%m")
        used = int(self.usage.get(uid, {}).get(month, {}).get("sheets", 0) or 0)
        if used >= limit:
            return CanGenerateResult(ok=False, message=f"Limit reached ({used}/{limit})")
        return CanGenerateResult(ok=True, message=f"{used}/{limit}")

    def get_stats(self, *, user_id: UUID | str) -> dict[str, Any]:
        uid = _norm_user_id(user_id)
        month = datetime.now().strftime("%Y-%m")
        data = self.usage.get(uid, {}).get(month, {})
        log = data.get("log", [])
        return {
            "month": month,
            "sheets_this_month": int(data.get("sheets", 0) or 0),
            "tokens_this_month": int(data.get("tokens", 0) or 0),
            "cost_this_month": float(data.get("cost", 0.0) or 0.0),
            "recent": log[-10:],
        }
