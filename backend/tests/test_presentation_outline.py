import pytest
from unittest.mock import patch
from pydantic import ValidationError

from app.schemas.presentation_outline import (
    PresentationOutline,
    TitleSlide,
    SectionSlide,
    ContentSlide,
    ImageSlide,
    ReferencesSlide,
    outline_warnings,
)


@pytest.fixture
def mock_settings():
    with patch("app.schemas.presentation_outline.settings") as mock:
        mock.PRESENTATION_SLIDE_MIN = 3
        mock.PRESENTATION_SLIDE_MAX = 5
        yield mock


def test_valid_presentation_outline(mock_settings):
    outline = PresentationOutline(
        title="Valid Presentation",
        slides=[
            TitleSlide(type="title", title="Main Title", subtitle="Subtitle", notes="notes"),
            ContentSlide(type="content", title="Content 1", content=["point 1", "point 2"], notes="notes"),
            ReferencesSlide(type="references", title="References", notes="notes"),
        ],
    )
    assert outline.title == "Valid Presentation"
    assert len(outline.slides) == 3


def test_slides_count_below_min(mock_settings):
    with pytest.raises(ValidationError) as exc_info:
        PresentationOutline(
            title="Short Presentation",
            slides=[
                TitleSlide(type="title", title="Main Title"),
                ReferencesSlide(type="references", title="References"),
            ],
        )
    assert "slides count must be between 3 and 5" in str(exc_info.value)


def test_slides_count_above_max(mock_settings):
    with pytest.raises(ValidationError) as exc_info:
        PresentationOutline(
            title="Long Presentation",
            slides=[
                TitleSlide(type="title", title="Main Title"),
                SectionSlide(type="section", title="S1"),
                SectionSlide(type="section", title="S2"),
                SectionSlide(type="section", title="S3"),
                SectionSlide(type="section", title="S4"),
                ReferencesSlide(type="references", title="References"),
            ],
        )
    assert "slides count must be between 3 and 5" in str(exc_info.value)


def test_first_slide_not_title(mock_settings):
    with pytest.raises(ValidationError) as exc_info:
        PresentationOutline(
            title="Invalid First Slide",
            slides=[
                ContentSlide(type="content", title="Content 1", content=["point 1"]),
                SectionSlide(type="section", title="Section 1"),
                ReferencesSlide(type="references", title="References"),
            ],
        )
    assert "first slide must be type=title" in str(exc_info.value)


def test_no_references_slide(mock_settings):
    with pytest.raises(ValidationError) as exc_info:
        PresentationOutline(
            title="No References",
            slides=[
                TitleSlide(type="title", title="Main Title"),
                SectionSlide(type="section", title="Section 1"),
                ContentSlide(type="content", title="Content 1", content=["point 1"]),
            ],
        )
    assert "must contain exactly 1 references slide" in str(exc_info.value)


def test_multiple_references_slides(mock_settings):
    with pytest.raises(ValidationError) as exc_info:
        PresentationOutline(
            title="Multiple References",
            slides=[
                TitleSlide(type="title", title="Main Title"),
                ReferencesSlide(type="references", title="Refs 1"),
                ReferencesSlide(type="references", title="Refs 2"),
            ],
        )
    assert "must contain exactly 1 references slide" in str(exc_info.value)


def test_references_slide_not_last(mock_settings):
    with pytest.raises(ValidationError) as exc_info:
        PresentationOutline(
            title="Refs Not Last",
            slides=[
                TitleSlide(type="title", title="Main Title"),
                ReferencesSlide(type="references", title="References"),
                ContentSlide(type="content", title="Content", content=["point 1"]),
            ],
        )
    assert "references slide must be the last slide" in str(exc_info.value)


def test_empty_slide_title(mock_settings):
    with pytest.raises(ValidationError) as exc_info:
        PresentationOutline(
            title="Empty Slide Title",
            slides=[
                TitleSlide(type="title", title="Main Title"),
                ContentSlide(type="content", title="   ", content=["point 1"]),
                ReferencesSlide(type="references", title="References"),
            ],
        )
    assert "slides[1].title is empty" in str(exc_info.value)


def test_content_slide_empty_bullets():
    with pytest.raises(ValidationError) as exc_info:
        ContentSlide(type="content", title="Content", content=["   ", "point 2"])
    assert "content bullets cannot be empty" in str(exc_info.value)


def test_content_slide_no_bullets():
    # Should be handled by max_length/min_length directly via field validation
    with pytest.raises(ValidationError) as exc_info:
        ContentSlide(type="content", title="Content", content=[])
    assert "List should have at least 1 item after validation" in str(exc_info.value)


def test_outline_warnings(mock_settings):
    outline = PresentationOutline(
        title="Warnings Presentation",
        slides=[
            TitleSlide(type="title", title="Main Title", notes="Has notes"),
            ContentSlide(
                type="content",
                title="Many Bullets",
                content=["1", "2", "3", "4", "5", "6", "7"],
                notes="Has notes",
            ),
            SectionSlide(type="section", title="Section without notes"), # missing notes
            ReferencesSlide(type="references", title="References"),
        ],
    )

    warnings = outline_warnings(outline)
    assert len(warnings) == 2
    assert "slides[1] has 7 bullets; recommended <= 6" in warnings[0]
    assert "slides[2] missing notes" in warnings[1]


def test_outline_no_warnings(mock_settings):
    outline = PresentationOutline(
        title="Valid Presentation",
        slides=[
            TitleSlide(type="title", title="Main Title", subtitle="Subtitle", notes="notes"),
            ContentSlide(type="content", title="Content 1", content=["point 1", "point 2"], notes="notes"),
            ReferencesSlide(type="references", title="References", notes="notes"),
        ],
    )
    warnings = outline_warnings(outline)
    assert len(warnings) == 0

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
