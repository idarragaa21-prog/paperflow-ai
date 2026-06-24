"""Unit tests for the Writing document export helpers (MD/DOCX/PDF/bibliography)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

import pytest


# Lightweight stand-ins so we don't need the full SQLAlchemy stack.
@dataclass
class _Section:
    section_key: str
    heading: str
    position: int
    content_markdown: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class _Document:
    title: str
    mode: str
    version: int
    sections: list[_Section]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class _Reference:
    title: str
    authors: list[str] | None
    journal: str | None
    publication_year: int | None
    doi: str | None = None
    pmid: str | None = None


def _sample_doc() -> _Document:
    return _Document(
        title="Aspirin in Secondary Prevention",
        mode="meta_analysis",
        version=2,
        sections=[
            _Section(
                section_key="abstract",
                heading="Abstract",
                position=1,
                content_markdown="## Abstract\n\nWe synthesised evidence supporting **aspirin** [M1].",
            ),
            _Section(
                section_key="methods",
                heading="Methods",
                position=2,
                content_markdown="## Methods\n\n- Random-effects model\n- 12 trials [R1]",
            ),
            _Section(
                section_key="empty",
                heading="Empty",
                position=3,
                content_markdown="",
            ),
        ],
    )


def _sample_refs() -> list[_Reference]:
    return [
        _Reference(
            title="Aspirin trial overview",
            authors=["Doe J", "Smith K"],
            journal="J Stroke",
            publication_year=2023,
            doi="10.1000/abc",
        ),
        _Reference(
            title="Antiplatelet therapy meta-analysis",
            authors=["Garcia M"],
            journal="Lancet",
            publication_year=2021,
            pmid="12345678",
        ),
    ]


def test_format_reference_apa() -> None:
    from app.services.writing_export import format_reference

    ref = _sample_refs()[0]
    out = format_reference(ref, style="apa")
    assert "Aspirin trial overview" in out
    assert "(2023)" in out
    assert "10.1000/abc" in out


def test_format_reference_vancouver_truncates_authors() -> None:
    from app.services.writing_export import format_reference

    many = _Reference(
        title="Big trial",
        authors=[f"Author {i}" for i in range(10)],
        journal="J Tests",
        publication_year=2020,
    )
    out = format_reference(many, style="vancouver")
    assert "et al." in out


def test_build_markdown_includes_bibliography() -> None:
    from app.services.writing_export import build_markdown

    md = build_markdown(_sample_doc(), references=_sample_refs(), citation_style="apa")
    assert "Aspirin in Secondary Prevention" in md
    assert "## Abstract" in md
    assert "## Methods" in md
    assert "## References" in md
    assert "Aspirin trial overview" in md
    # Empty section should still render with a heading
    assert "## Empty" in md


def test_build_docx_returns_nonempty_blob() -> None:
    pytest.importorskip("docx")
    from app.services.writing_export import build_docx

    blob = build_docx(_sample_doc(), references=_sample_refs(), citation_style="apa")
    assert isinstance(blob, (bytes, bytearray))
    # docx files start with the ZIP magic bytes "PK"
    assert blob[:2] == b"PK"
    assert len(blob) > 2000


def test_build_pdf_returns_pdf_blob() -> None:
    pytest.importorskip("reportlab")
    from app.services.writing_export import build_pdf

    blob = build_pdf(_sample_doc(), references=_sample_refs(), citation_style="vancouver")
    assert isinstance(blob, (bytes, bytearray))
    assert blob.startswith(b"%PDF")
