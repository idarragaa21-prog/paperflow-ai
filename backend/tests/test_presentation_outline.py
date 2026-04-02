from app.schemas.presentation_outline import (
    PresentationOutline,
    ContentSlide,
    TitleSlide,
    SectionSlide,
    ImageSlide,
    ReferencesSlide,
    outline_warnings,
)

def test_outline_warnings_bullet_count():
    # Test that > 6 bullets generates a warning
    outline = PresentationOutline.model_construct(
        title="Test Outline",
        slides=[
            TitleSlide.model_construct(type="title", title="Title", subtitle="", notes="notes"),
            ContentSlide.model_construct(
                type="content",
                title="Too many bullets",
                content=["b1", "b2", "b3", "b4", "b5", "b6", "b7"],
                citations=[],
                notes="notes"
            ),
        ]
    )
    warnings = outline_warnings(outline)
    assert len(warnings) == 1
    assert "slides[1] has 7 bullets; recommended <= 6" in warnings[0]

    # Test that <= 6 bullets generates no warning for bullets
    outline_ok = PresentationOutline.model_construct(
        title="Test Outline",
        slides=[
            TitleSlide.model_construct(type="title", title="Title", subtitle="", notes="notes"),
            ContentSlide.model_construct(
                type="content",
                title="Valid bullets",
                content=["b1", "b2", "b3", "b4", "b5", "b6"],
                citations=[],
                notes="notes"
            ),
        ]
    )
    warnings_ok = outline_warnings(outline_ok)
    assert len(warnings_ok) == 0

def test_outline_warnings_missing_notes():
    # Test that section, divider, content, image_placeholder missing notes generate warning
    outline = PresentationOutline.model_construct(
        title="Test Outline missing notes",
        slides=[
            TitleSlide.model_construct(type="title", title="T", subtitle="", notes=""), # no warning for title
            SectionSlide.model_construct(type="section", title="S", notes=""), # warning
            SectionSlide.model_construct(type="divider", title="D", notes="   "), # warning
            ContentSlide.model_construct(type="content", title="C", content=["a"], citations=[], notes=None), # warning
            ImageSlide.model_construct(type="image_placeholder", title="I", image_suggestion="x", citations=[], notes=""), # warning
            ReferencesSlide.model_construct(type="references", title="R", notes=""), # no warning for references
            ContentSlide.model_construct(type="content", title="C2", content=["a"], citations=[], notes="has notes"), # no warning
        ]
    )
    warnings = outline_warnings(outline)

    # We expect warnings for indices 1, 2, 3, 4
    assert len(warnings) == 4
    assert any("slides[1] missing notes" in w for w in warnings)
    assert any("slides[2] missing notes" in w for w in warnings)
    assert any("slides[3] missing notes" in w for w in warnings)
    assert any("slides[4] missing notes" in w for w in warnings)
    assert not any("slides[0]" in w for w in warnings)
    assert not any("slides[5]" in w for w in warnings)
    assert not any("slides[6]" in w for w in warnings)
