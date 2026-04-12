from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    @abstractmethod
    async def summarize_paper(
        self,
        full_text: str,
        title: str,
        custom_instructions: str | None = None,
    ) -> dict[str, Any]:
        pass

    @abstractmethod
    async def format_references_vancouver(self, papers: list[dict[str, Any]]) -> list[str]:
        pass
