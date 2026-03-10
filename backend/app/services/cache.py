from __future__ import annotations

import hashlib
import json
from typing import Any

from redis import asyncio as redis_async

from app.config import settings


class CacheManager:
    SEARCH_SCHEMA_VERSION = 2

    def __init__(self):
        self._redis = None

    def _client(self):
        if self._redis is None:
            self._redis = redis_async.from_url(settings.REDIS_URL, decode_responses=True)
        return self._redis

    async def get(self, key: str) -> Any | None:
        try:
            val = await self._client().get(key)
            if not val:
                return None
            return json.loads(val)
        except Exception:
            return None

    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        try:
            payload = json.dumps(value, ensure_ascii=False, sort_keys=True)
            await self._client().set(key, payload, ex=ttl)
        except Exception:
            return None

    async def delete(self, key: str) -> None:
        try:
            await self._client().delete(key)
        except Exception:
            return None

    def generate_search_key(
        self,
        query: str,
        filters: dict | None = None,
        *,
        max_results: int | None = None,
        source: str = "pubmed",
    ) -> str:
        normalized = {
            "schema_version": self.SEARCH_SCHEMA_VERSION,
            "source": source,
            "q": query.strip(),
            "filters": filters or {},
            "max_results": max_results,
        }
        raw = json.dumps(normalized, sort_keys=True, ensure_ascii=False)
        digest = hashlib.md5(raw.encode("utf-8")).hexdigest()
        return f"search:{source}:{digest}"


cache = CacheManager()
