from __future__ import annotations

from typing import Any

from anthropic import AsyncAnthropic

from app.config import settings
from app.core.logger import logger
from app.services.llm.base import LLMProvider

_NOT_IMPLEMENTED_MSG = (
    "direct-Claude mode does not implement this method. "
    "Set LLM_PROVIDER=openclaw in your environment to use the full feature set."
)


class ClaudeProvider(LLMProvider):
    def __init__(self):
        if not settings.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY requerida para Claude directo")
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = settings.CLAUDE_MODEL
        self.max_tokens = settings.CLAUDE_MAX_TOKENS
        self.temperature = settings.CLAUDE_TEMPERATURE

    async def summarize_paper(self, full_text: str, title: str, custom_instructions: str | None = None) -> dict[str, Any]:
        logger.warning(f"[ClaudeProvider] summarize_paper not implemented in direct-Claude mode. {_NOT_IMPLEMENTED_MSG}")
        raise NotImplementedError(_NOT_IMPLEMENTED_MSG)

    async def generate_slide_outline(
        self,
        topic: str,
        duration_minutes: int,
        audience: str,
        papers: list[dict[str, Any]] | None = None,
        num_slides: int | None = None,
    ) -> dict[str, Any]:
        logger.warning(f"[ClaudeProvider] generate_slide_outline not implemented in direct-Claude mode. {_NOT_IMPLEMENTED_MSG}")
        raise NotImplementedError(_NOT_IMPLEMENTED_MSG)

    async def format_references_vancouver(self, papers: list[dict[str, Any]]) -> list[str]:
        logger.warning(f"[ClaudeProvider] format_references_vancouver not implemented in direct-Claude mode. {_NOT_IMPLEMENTED_MSG}")
        raise NotImplementedError(_NOT_IMPLEMENTED_MSG)
