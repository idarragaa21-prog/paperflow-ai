from __future__ import annotations

import pytest

from app.services import runtime_health


class DummyResponse:
    def __init__(self, text: str = "ok", json_payload: dict | None = None):
        self.text = text
        self._json_payload = json_payload or {}

    def raise_for_status(self):
        return None

    def json(self):
        return self._json_payload


class DummyAsyncClient:
    def __init__(self, *args, **kwargs):
        return None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url: str):
        if url.endswith("/api/tags"):
            return DummyResponse(json_payload={"models": []})
        if url.endswith("/api/isalive"):
            return DummyResponse(text="true")
        return DummyResponse(text="ok")


class DummyQdrantClient:
    def __init__(self, *args, **kwargs):
        return None

    def get_collections(self):
        return {"collections": []}


@pytest.mark.asyncio
async def test_collect_runtime_health_separates_required_and_optional(monkeypatch):
    monkeypatch.setattr(runtime_health, "redis_available", lambda: True)
    monkeypatch.setattr(runtime_health.storage_manager, "ensure_bucket", lambda: None)
    monkeypatch.setattr(runtime_health.httpx, "AsyncClient", DummyAsyncClient)
    monkeypatch.setattr("qdrant_client.QdrantClient", DummyQdrantClient)

    health = await runtime_health.collect_runtime_health()

    assert health["overall_status"] in {"ok", "degraded"}
    assert health["required_services"]["redis"]["status"] == "ok"
    assert health["required_services"]["qdrant"]["status"] == "ok"
    assert health["required_services"]["ollama"]["status"] == "ok"
    assert "prometheus" in health["optional_services"]
