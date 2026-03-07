from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class SlideType(str, Enum):
    title = "title"
    section = "section"
    content = "content"
    image_placeholder = "image_placeholder"
    references = "references"


class SlideBase(BaseModel):
    type: SlideType
    title: str = Field(default="")


class TitleSlide(SlideBase):
    type: Literal[SlideType.title]
    # subtitle in "content" (string) to match required shape
    content: str = Field(default="")
    notes: str = Field(default="")


class SectionSlide(SlideBase):
    type: Literal[SlideType.section]
    notes: str


class ContentSlide(SlideBase):
    type: Literal[SlideType.content]
    content: list[str] = Field(default_factory=list, description="Bullets")
    notes: str
    citations: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_bullets(self):
        if len(self.content) > 8:
            raise ValueError("content bullets hard cap is 8")
        return self


class ImagePlaceholderSlide(SlideBase):
    type: Literal[SlideType.image_placeholder]
    notes: str
    citations: list[str] = Field(default_factory=list)
    image_suggestion: str | None = None


class ReferencesSlide(SlideBase):
    type: Literal[SlideType.references]
    notes: str = Field(default="")


Slide = TitleSlide | SectionSlide | ContentSlide | ImagePlaceholderSlide | ReferencesSlide


class OutlineMeta(BaseModel):
    target_slides: int = 36
    audience: str
    duration_minutes: int
    topic: str


class PresentationOutline(BaseModel):
    title: str
    slides: list[Slide]
    meta: OutlineMeta

    @model_validator(mode="after")
    def _validate_outline(self):
        n = len(self.slides)
        if n < 30 or n > 40:
            raise ValueError("slides count must be between 30 and 40")

        if not self.slides:
            raise ValueError("slides cannot be empty")

        if self.slides[0].type != SlideType.title:
            raise ValueError("Slide 1 must be type=title")

        if self.slides[-1].type != SlideType.references:
            raise ValueError("Last slide must be type=references")

        # Notes required where stated
        for i, s in enumerate(self.slides):
            if s.type in (SlideType.section, SlideType.content, SlideType.image_placeholder):
                notes = getattr(s, "notes", None)
                if not notes or not str(notes).strip():
                    raise ValueError(f"Slide {i+1} ({s.type}) must include notes")

            if s.type in (SlideType.content, SlideType.image_placeholder):
                citations = getattr(s, "citations", None)
                if citations is None or not isinstance(citations, list):
                    raise ValueError(f"Slide {i+1} ({s.type}) citations must be list[str]")

        return self


class OutlineResponse(BaseModel):
    outline: PresentationOutline
    usage: dict[str, Any]
    model: str
