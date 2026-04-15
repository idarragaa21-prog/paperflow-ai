from __future__ import annotations

from typing import Any

from app.config import settings
from app.services.llm.base import LLMProvider
from app.services.llm.ollama import OllamaProvider
from app.services.llm.openclaw import OpenClawProvider


class LocalAutoProvider(LLMProvider):
    """Primary OpenClaw with transparent local Ollama fallback."""

    def __init__(self):
        self.openclaw = OpenClawProvider()
        self.ollama = OllamaProvider()
        self.last_route: str = "openclaw"

    @staticmethod
    def _ollama_model_for_fallback(model: str | None) -> str:
        if not model or model == "default":
            return settings.PAPERFLOW_CHAT_MODEL
        return model

    async def chat(
        self,
        *,
        model: str,
        system: str,
        user: str,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        timeout: int | None = None,
        retry: int = 2,
    ) -> dict[str, Any]:
        try:
            response = await self.openclaw.chat(
                model=model,
                system=system,
                user=user,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
                retry=retry,
            )
            self.last_route = "openclaw"
            return response
        except Exception as primary_exc:
            fallback = await self.ollama.chat(
                model=self._ollama_model_for_fallback(model),
                system=system,
                user=user,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
                retry=max(1, retry),
            )
            self.last_route = "ollama"
            fallback["fallback_from"] = "openclaw"
            fallback["primary_error"] = str(primary_exc)
            return fallback

    async def summarize_paper(self, full_text: str, title: str, custom_instructions: str | None = None) -> dict[str, Any]:
        try:
            result = await self.openclaw.summarize_paper(full_text, title, custom_instructions)
            self.last_route = "openclaw"
            return result
        except Exception as primary_exc:
            fallback = await self.ollama.summarize_paper(full_text, title, custom_instructions)
            self.last_route = "ollama"
            usage = fallback.get("usage") or {}
            usage["fallback_from"] = "openclaw"
            usage["primary_error"] = str(primary_exc)
            fallback["usage"] = usage
            return fallback

    async def format_references_vancouver(self, papers: list[dict[str, Any]]) -> list[str]:
        # Deterministic formatter does not require network calls.
        return await self.ollama.format_references_vancouver(papers)
