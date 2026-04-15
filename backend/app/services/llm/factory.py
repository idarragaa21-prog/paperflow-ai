from __future__ import annotations

from app.config import settings
from app.services.llm.base import LLMProvider
from app.services.llm.claude import ClaudeProvider
from app.services.llm.ensemble import EnsembleLLMProvider
from app.services.llm.local_auto import LocalAutoProvider
from app.services.llm.ollama import OllamaProvider
from app.services.llm.openclaw import OpenClawProvider


def get_llm_provider() -> LLMProvider:
    provider_type = settings.LLM_PROVIDER

    # Ensemble strategy requires OpenClaw multi-vendor routing
    if settings.LLM_STRATEGY == "ensemble":
        if provider_type != "openclaw":
            raise ValueError("LLM_STRATEGY=ensemble requiere LLM_PROVIDER=openclaw")
        return EnsembleLLMProvider(OpenClawProvider())

    # Single strategy
    if provider_type == "auto_local":
        return LocalAutoProvider()
    if provider_type == "openclaw":
        return OpenClawProvider()
    if provider_type == "ollama":
        return OllamaProvider()
    if provider_type == "direct_claude":
        return ClaudeProvider()
    raise ValueError(f"LLM_PROVIDER inválido: {provider_type}")


_provider: LLMProvider | None = None


def llm_provider() -> LLMProvider:
    global _provider
    if _provider is None:
        _provider = get_llm_provider()
    return _provider


def reset_llm_provider_for_tests() -> None:
    global _provider
    _provider = None
