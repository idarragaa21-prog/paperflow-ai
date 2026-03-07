from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

import pytest
from sqlalchemy import select

from app.core.storage import storage_manager
from app.models.document import PaperChunk, PaperParseRun
from app.models.paper import Paper
import app.services.pdf_processor as pdf_processor
from app.services.pdf_processor import process_paper


def _make_pdf_bytes_with_text(text: str) -> bytes:
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    data = doc.tobytes()
    doc.close()
    return data


class FakeSession:
    def __init__(self, paper: Paper | None):
        self._paper = paper
        self._added: list[object] = []

    async def get(self, model, obj_id):
        if model is Paper and self._paper and self._paper.id == obj_id:
            return self._paper
        return None

    def add(self, obj):
        self._added.append(obj)

    async def flush(self):
        for obj in self._added:
            if getattr(obj, "id", None) is None:
                setattr(obj, "id", uuid.uuid4())

    async def execute(self, query):
        class Result:
            def __init__(self, items):
                self._items = items

            def scalars(self):
                return self

            def first(self):
                return self._items[0] if self._items else None

        if isinstance(query, type(select(1))):
            return Result([])
        return Result([])

    async def commit(self):
        return None


@pytest.mark.asyncio
async def test_process_marks_processed_and_stores_text(tmp_path, monkeypatch):
    # Redirect storage to temp
    storage_manager.base_dir = tmp_path.resolve()
    storage_manager._ensure_directories()

    project_id = uuid.uuid4()
    year_dir = storage_manager.base_dir / "papers" / str(project_id) / "2026"
    year_dir.mkdir(parents=True, exist_ok=True)

    rel_path = Path("papers") / str(project_id) / "2026" / "x.pdf"
    abs_path = storage_manager.base_dir / rel_path

    abs_path.write_bytes(_make_pdf_bytes_with_text("Hello PDF"))

    paper_id = uuid.uuid4()
    paper = Paper(
        id=paper_id,
        project_id=project_id,
        search_result_id=None,
        title="Test",
        authors=None,
        doi=None,
        pmid=None,
        pmcid=None,
        filename="x.pdf",
        file_path=str(rel_path),
        file_size_kb=1,
        content_hash="abc",
        is_processed=False,
        full_text_extracted=None,
        downloaded_at=None,
    )

    async def fake_grobid(*args, **kwargs):
        return """<TEI xmlns='http://www.tei-c.org/ns/1.0'><teiHeader><fileDesc><titleStmt><title>GROBID Title</title></titleStmt></fileDesc></teiHeader><text><body><div><head>Methods</head><p>Participants: 40 adults.</p></div></body></text><back><listBibl><biblStruct><analytic><title>Ref title</title><author><persName><forename>Ana</forename><surname>Perez</surname></persName></author></analytic><monogr><imprint><date>2024</date></imprint></monogr></biblStruct></listBibl></back></TEI>"""  # noqa: E501

    monkeypatch.setattr(pdf_processor, "process_fulltext", fake_grobid)

    db = FakeSession(paper)
    result = await process_paper(paper_id, db)

    assert result["paper_id"] == str(paper_id)
    assert paper.is_processed is True
    assert paper.full_text_extracted and "Hello PDF" in paper.full_text_extracted
    assert result["chunks"] >= 1
    assert result["references"] == 1
    assert any(isinstance(obj, PaperParseRun) for obj in db._added)
    assert any(isinstance(obj, PaperChunk) for obj in db._added)
    parse_run = next(obj for obj in db._added if isinstance(obj, PaperParseRun))
    assert parse_run.metadata_json["document_model"] == "dual_semantic_layout_v1"
    assert parse_run.metadata_json["sections"][0]["heading"] == "Methods"
    assert parse_run.metadata_json["references"][0]["title"] == "Ref title"


@pytest.mark.asyncio
async def test_process_missing_file_fails(tmp_path, monkeypatch):
    storage_manager.base_dir = tmp_path.resolve()
    storage_manager._ensure_directories()

    project_id = uuid.uuid4()
    rel_path = Path("papers") / str(project_id) / "2026" / "missing.pdf"

    paper_id = uuid.uuid4()
    paper = Paper(
        id=paper_id,
        project_id=project_id,
        search_result_id=None,
        title="Test",
        authors=None,
        doi=None,
        pmid=None,
        pmcid=None,
        filename="missing.pdf",
        file_path=str(rel_path),
        file_size_kb=1,
        content_hash="abc",
        is_processed=False,
        full_text_extracted=None,
        downloaded_at=None,
    )

    db = FakeSession(paper)

    with pytest.raises(FileNotFoundError):
        await process_paper(paper_id, db)
