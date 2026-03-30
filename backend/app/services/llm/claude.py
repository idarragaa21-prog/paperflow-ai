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
        """Direct Anthropic Messages API call.

        Returns dict compatible with OpenClawProvider.chat: content, usage, latency_ms, model.
        """
        import time

        last_err: Exception | None = None
        for attempt in range(retry + 1):
            t0 = time.perf_counter()
            try:
                resp = await self.client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                    temperature=temperature,
                )
                latency_ms = int((time.perf_counter() - t0) * 1000)
                content = resp.content[0].text if resp.content else ""
                usage = {
                    "prompt_tokens": resp.usage.input_tokens,
                    "completion_tokens": resp.usage.output_tokens,
                }
                return {"content": content, "usage": usage, "latency_ms": latency_ms, "model": resp.model}
            except Exception as exc:
                last_err = exc
                logger.warning(f"[ClaudeProvider] chat attempt {attempt + 1} failed: {exc!r}")
        raise RuntimeError(f"ClaudeProvider.chat failed after {retry + 1} attempts") from last_err
