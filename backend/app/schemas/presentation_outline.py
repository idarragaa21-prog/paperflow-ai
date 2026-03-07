from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, model_validator

from app.config import settings


class SlideBase(BaseModel):
    type: str
    title: str = Field(..., min_length=1)
    notes: str | None = None


class TitleSlide(SlideBase):
    type: Literal["title"]
    subtitle: str = Field("", description="Subtitle shown on title slide")


class SectionSlide(SlideBase):
    type: Literal["section", "divider"]


class ContentSlide(SlideBase):
    type: Literal["content"]
    content: list[str] = Field(..., min_length=1, max_length=8)
    citations: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _no_empty_bullets(self):
        if any(not (b or "").strip() for b in self.content):
            raise ValueError("content bullets cannot be empty")
        return self


class ImageSlide(SlideBase):
    type: Literal["image_placeholder"]
    image_suggestion: str = Field(..., min_length=3)
    citations: list[str] = Field(default_factory=list)


class ReferencesSlide(SlideBase):
    type: Literal["references"]


Slide = Annotated[
    Union[TitleSlide, SectionSlide, ContentSlide, ImageSlide, ReferencesSlide],
    Field(discriminator="type"),
]


class PresentationOutline(BaseModel):
    title: str = Field(..., min_length=1)
    slides: list[Slide] = Field(..., min_length=1)

    @model_validator(mode="after")
    def _validate_hard_rules(self):
        min_slides = settings.PRESENTATION_SLIDE_MIN
        max_slides = settings.PRESENTATION_SLIDE_MAX

        n = len(self.slides)
        if n < min_slides or n > max_slides:
            raise ValueError(f"slides count must be between {min_slides} and {max_slides}")

        # First slide must be title
        if self.slides[0].type != "title":
            raise ValueError("first slide must be type=title")

        # Exactly one references slide and must be last
        refs = [i for i, s in enumerate(self.slides) if s.type == "references"]
        if len(refs) != 1:
            raise ValueError("must contain exactly 1 references slide")
        if refs[0] != n - 1:
            raise ValueError("references slide must be the last slide")

        # No empty slides
        for i, s in enumerate(self.slides):
            if not (s.title or "").strip():
                raise ValueError(f"slides[{i}].title is empty")

        return self


def outline_warnings(outline: PresentationOutline) -> list[str]:
    warnings: list[str] = []

    for i, s in enumerate(outline.slides):
        if isinstance(s, ContentSlide) and len(s.content) > 6:
            warnings.append(f"slides[{i}] has {len(s.content)} bullets; recommended <= 6")

        if s.type in ("section", "divider", "content", "image_placeholder"):
            if not (s.notes or "").strip():
                warnings.append(f"slides[{i}] missing notes")

    return warnings
