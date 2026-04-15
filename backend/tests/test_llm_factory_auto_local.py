from __future__ import annotations

import pytest

from app.services.llm.factory import get_llm_provider, reset_llm_provider_for_tests
from app.services.llm.local_auto import LocalAutoProvider
from app.services.llm.ollama import OllamaProvider


def test_get_llm_provider_auto_local(monkeypatch):
    from app import config

    monkeypatch.setattr(config.settings, "LLM_PROVIDER", "auto_local")
    monkeypatch.setattr(config.settings, "LLM_STRATEGY", "single")
    reset_llm_provider_for_tests()
    provider = get_llm_provider()
    assert isinstance(provider, LocalAutoProvider)


def test_get_llm_provider_ollama(monkeypatch):
    from app import config

    monkeypatch.setattr(config.settings, "LLM_PROVIDER", "ollama")
    monkeypatch.setattr(config.settings, "LLM_STRATEGY", "single")
    reset_llm_provider_for_tests()
    provider = get_llm_provider()
    assert isinstance(provider, OllamaProvider)


@pytest.mark.asyncio
async def test_local_auto_provider_falls_back_to_ollama(monkeypatch):
    provider = LocalAutoProvider()

    async def broken_openclaw(**kwargs):
        raise RuntimeError("openclaw down")

    async def fake_ollama(**kwargs):
        return {"content": "fallback ok", "model": "qwen2.5-coder:7b", "usage": {}, "latency_ms": 1}

    monkeypatch.setattr(provider.openclaw, "chat", broken_openclaw)
    monkeypatch.setattr(provider.ollama, "chat", fake_ollama)

    result = await provider.chat(
        model="default",
        system="sys",
        user="hello",
    )

    assert result["content"] == "fallback ok"
    assert result["fallback_from"] == "openclaw"
    assert provider.last_route == "ollama"
