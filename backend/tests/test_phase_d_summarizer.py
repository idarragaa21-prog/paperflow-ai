from __future__ import annotations

import uuid
from datetime import datetime

import pytest

from app.models.note import Note
from app.models.paper import Paper
from app.services import summarizer
from app.services.summarizer import parse_summary_markdown


class FakeSession:
    def __init__(self, paper: Paper):
        self.paper = paper
        self.added: list[object] = []

    async def get(self, model, obj_id):
        if model is Paper and obj_id == self.paper.id:
            return self.paper
        return None

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        return None

    async def refresh(self, obj):
        # emulate DB assigned id
        if isinstance(obj, Note) and not getattr(obj, "id", None):
            obj.id = uuid.uuid4()
        return None


class FakeLLM:
    async def summarize_paper(self, full_text: str, title: str, custom_instructions: str | None = None):
        return {
            "summary": "## Objetivo\nTexto\n\n## Resultados\nMás texto",
            "usage": {"input_tokens": 10, "output_tokens": 20, "cost_usd": 0.01},
            "model": "mock-model",
        }


@pytest.mark.asyncio
async def test_summary_creates_note(monkeypatch):
    paper_id = uuid.uuid4()
    project_id = uuid.uuid4()

    paper = Paper(
        id=paper_id,
        project_id=project_id,
        search_result_id=None,
        title="T",
        authors=None,
        doi=None,
        pmid=None,
        pmcid=None,
        filename="x.pdf",
        file_path="papers/x.pdf",
        file_size_kb=1,
        content_hash="abc",
        is_processed=True,
        full_text_extracted=("full text " * 120),
        downloaded_at=datetime.utcnow(),
    )

    db = FakeSession(paper)

    monkeypatch.setattr(summarizer, "llm_provider", lambda: FakeLLM())

    r = await summarizer.generate_summary_async(paper_id=paper_id, custom_instructions=None, db=db)

    assert r["paper_id"] == str(paper_id)
    assert "note_id" in r

    notes = [x for x in db.added if isinstance(x, Note)]
    assert len(notes) == 1
    assert notes[0].project_id == project_id
    assert notes[0].paper_id == paper_id
    assert notes[0].note_type == "summary"
    assert notes[0].llm_model == "mock-model"


def test_parse_summary_markdown_empty():
    assert parse_summary_markdown("") == {}
    assert parse_summary_markdown(None) == {}


def test_parse_summary_markdown_no_headings():
    text = "Just some text\nwithout any headings."
    expected = {"Resumen": "Just some text\nwithout any headings."}
    assert parse_summary_markdown(text) == expected


def test_parse_summary_markdown_h2_headings():
    text = "## Objective\nTo test the code.\n## Results\nIt works."
    expected = {
        "Objective": "To test the code.",
        "Results": "It works."
    }
    assert parse_summary_markdown(text) == expected


def test_parse_summary_markdown_bold_headings():
    text = "**Objective**\nTo test the code.\n**Results**\nIt works."
    expected = {
        "Objective": "To test the code.",
        "Results": "It works."
    }
    assert parse_summary_markdown(text) == expected


def test_parse_summary_markdown_mixed_headings():
    text = "Introductory text.\n## Method\nDid some stuff.\n**Conclusion**\nIt is good."
    expected = {
        "Resumen": "Introductory text.",
        "Method": "Did some stuff.",
        "Conclusion": "It is good."
    }
    assert parse_summary_markdown(text) == expected


def test_parse_summary_markdown_ignores_empty_sections():
    text = "## Empty Section\n\n## Next Section\nHas content."
    expected = {
        "Next Section": "Has content."
    }
    assert parse_summary_markdown(text) == expected


def test_parse_summary_markdown_windows_line_endings():
    text = "## First\r\nContent\r\n## Second\r\nMore content"
    expected = {
        "First": "Content",
        "Second": "More content"
    }
    assert parse_summary_markdown(text) == expected
