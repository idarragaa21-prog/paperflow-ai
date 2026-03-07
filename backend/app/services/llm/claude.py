from __future__ import annotations

from typing import Any

from anthropic import AsyncAnthropic

from app.config import settings
from app.services.llm.base import LLMProvider


class ClaudeProvider(LLMProvider):
    def __init__(self):
        if not settings.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY requerida para Claude directo")
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = settings.CLAUDE_MODEL
        self.max_tokens = settings.CLAUDE_MAX_TOKENS
        self.temperature = settings.CLAUDE_TEMPERATURE

    async def summarize_paper(self, full_text: str, title: str, custom_instructions: str | None = None) -> dict[str, Any]:
        raise NotImplementedError

    async def generate_slide_outline(
        self,
        topic: str,
        duration_minutes: int,
        audience: str,
        papers: list[dict[str, Any]] | None = None,
        num_slides: int | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError

    async def format_references_vancouver(self, papers: list[dict[str, Any]]) -> list[str]:
        raise NotImplementedError
