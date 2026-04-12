from __future__ import annotations

from typing import Any

from app.services.llm.base import LLMProvider
from app.services.llm.openclaw import OpenClawProvider


class EnsembleLLMProvider(LLMProvider):
    """OpenClaw-backed provider used when `LLM_STRATEGY=ensemble`.

    Presentation generation was removed from PaperFlow vNext scope.
    """

    def __init__(self, openclaw: OpenClawProvider):
        self.openclaw = openclaw

    async def summarize_paper(self, full_text: str, title: str, custom_instructions: str | None = None) -> dict[str, Any]:
        return await self.openclaw.summarize_paper(full_text, title, custom_instructions)

    async def format_references_vancouver(self, papers: list[dict[str, Any]]) -> list[str]:
        return await self.openclaw.format_references_vancouver(papers)
