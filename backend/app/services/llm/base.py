from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.services.llm.schemas import GenerateOutlineInput


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
    async def generate_slide_outline(
        self,
        input_data: GenerateOutlineInput,
    ) -> dict[str, Any]:
        pass

    @abstractmethod
    async def format_references_vancouver(self, papers: list[dict[str, Any]]) -> list[str]:
        pass
