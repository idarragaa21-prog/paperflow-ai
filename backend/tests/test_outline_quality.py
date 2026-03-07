from __future__ import annotations

from app.services.llm.quality_gate import quality_gate_and_fix
from app.services.llm.schemas import PresentationOutline, SlideType


def _make_min_outline(slide_count: int = 30) -> dict:
    slides = [
        {"type": "title", "title": "Tema", "content": "Subtítulo"},
        {"type": "content", "title": "Objetivos", "content": ["A", "B", "C"], "notes": "n", "citations": []},
        {"type": "content", "title": "Agenda", "content": ["A", "B", "C", "D"], "notes": "n", "citations": []},
    ]

    # Fill
    while len(slides) < slide_count - 1:
        slides.append(
            {
                "type": "content",
                "title": f"Slide {len(slides)+1}",
                "content": ["p1", "p2", "p3", "p4"],
                "notes": "nota",
                "citations": [],
            }
        )

    slides.append({"type": "references", "title": "Referencias", "notes": ""})

    return {
        "title": "Tema",
        "slides": slides,
        "meta": {"target_slides": 36, "audience": "R1", "duration_minutes": 45, "topic": "Tema"},
    }


def test_outline_slide_count_in_range():
    outline = _make_min_outline(slide_count=29)  # intentionally out of range
    fixed = quality_gate_and_fix(outline)
    assert 30 <= len(fixed.slides) <= 40


def test_outline_schema_validates():
    outline = _make_min_outline(slide_count=30)
    parsed = PresentationOutline.model_validate(outline)
    assert parsed.slides[0].type == SlideType.title
    assert parsed.slides[-1].type == SlideType.references
