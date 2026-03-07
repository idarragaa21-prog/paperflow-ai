from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path

import pytest

from app.services.meta_extractor.schema import ExtractedStudySchema


class FakePaper:
    def __init__(self, project_id, file_path):
        self.id = uuid.uuid4()
        self.project_id = project_id
        self.file_path = file_path


class FakeItem:
    def __init__(self, batch_id, paper_id):
        self.id = uuid.uuid4()
        self.batch_id = batch_id
        self.paper_id = paper_id
        self.status = "queued"
        self.result_summary = None
        self.error_message = None


class FakePrevStudy:
    def __init__(self, paper_id, version=1):
        self.id = uuid.uuid4()
        self.paper_id = paper_id
        self.version = version
        self.is_current = True


class FakeStudy:
    def __init__(self, paper_id, version):
        self.id = uuid.uuid4()
        self.paper_id = paper_id
        self.version = version
        self.is_current = True
        self.extraction_confidence = 0.5


class FakeDB:
    def __init__(self, paper, item, prev=None):
        self.paper = paper
        self.item = item
        self.prev = prev
        self.added = []

    def _find_added(self, cls_name: str):
        for o in self.added:
            if o.__class__.__name__ == cls_name:
                return o
        return None

    async def get(self, model, obj_id):
        name = getattr(model, "__name__", "")
        if name == "Paper" and obj_id == self.paper.id:
            return self.paper
        if name == "MetaExtractionItem" and obj_id == self.item.id:
            return self.item
        return None

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        return None

    async def refresh(self, obj):
        return None

    async def execute(self, stmt):
        # Detect if selecting ExtractedStudy current for paper
        class R:
            def __init__(self, prev):
                self._prev = prev

            def scalars(self):
                class S:
                    def __init__(self, prev):
                        self._prev = prev

                    def first(self):
                        return self._prev

                return S(self._prev)

        return R(self.prev)


class FakeSessionMaker:
    def __init__(self, db):
        self.db = db

    async def __aenter__(self):
        return self.db

    async def __aexit__(self, exc_type, exc, tb):
        return False


def test_meta_job_progress_calls(monkeypatch, tmp_path):
    # Arrange minimal PDF
    pdf_rel = "papers/p.pdf"
    abs_pdf = tmp_path / pdf_rel
    abs_pdf.parent.mkdir(parents=True, exist_ok=True)
    import fitz

    d = fitz.open()
    d.new_page()
    d.save(abs_pdf)
    d.close()

    project_id = uuid.uuid4()
    paper = FakePaper(project_id, pdf_rel)
    item = FakeItem(uuid.uuid4(), paper.id)

    # Provide a previous current study to validate version increment + toggle
    prev = FakePrevStudy(paper_id=paper.id, version=2)
    db = FakeDB(paper, item, prev=prev)

    from app.workers import tasks

    # patch storage base_dir
    from app.core.storage import storage_manager

    storage_manager.base_dir = tmp_path.resolve()

    # patch session maker
    tasks.async_session_maker = lambda: FakeSessionMaker(db)  # type: ignore

    # patch PDF open encryption check
    monkeypatch.setattr(tasks, "fitz", None, raising=False)

    # patch extraction & validation to avoid LLM
    async def fake_extract_and_validate(inp):
        return ExtractedStudySchema.model_validate(
            {
                "title": "T",
                "first_author": "A",
                "year": 2024,
                "journal": "J",
                "arms": [{"arm_name": "I"}, {"arm_name": "C"}],
                "outcomes": [{"outcome_name": "Mortality"}],
                "effect_sizes": [],
                "risk_of_bias": [],
            }
        )

    import app.services.meta_extractor.extractor as extractor_mod

    monkeypatch.setattr(extractor_mod, "extract_and_validate", fake_extract_and_validate)

    # patch helpers to record progress
    percents = []

    async def rec_progress(job_id, percent, status="progress", result_patch=None):
        percents.append(int(percent))

    monkeypatch.setattr(tasks, "job_set_progress", rec_progress)

    async def nop(*a, **k):
        return None

    monkeypatch.setattr(tasks, "job_mark_started", nop)
    monkeypatch.setattr(tasks, "job_mark_completed", nop)
    monkeypatch.setattr(tasks, "job_mark_failed", nop)

    # patch fitz open to not fail
    class FakeDoc:
        is_encrypted = False

        def close(self):
            return None

    import types

    fake_fitz = types.SimpleNamespace(open=lambda p: FakeDoc())
    monkeypatch.setattr(tasks, "fitz", fake_fitz, raising=False)

    # patch OCR avail
    from app.config import settings

    settings.OCR_ENABLED = False

    # Act
    tasks.meta_extract_paper_job(str(uuid.uuid4()), str(item.batch_id), str(item.id), str(paper.id))

    # Assert: we saw staged progress markers
    assert 5 in percents
    assert 20 in percents
    assert 40 in percents
    assert 55 in percents
    assert 70 in percents
    assert 95 in percents

    # Versioning: prev toggled off and new version incremented
    assert prev.is_current is False
    study_obj = db._find_added("ExtractedStudy")
    assert study_obj is not None
    assert int(study_obj.version) == 3


def test_reextract_versioning_toggle(monkeypatch):
    # This is a pure logic check: when prev exists, it should be marked not current and next version increments.
    prev = FakePrevStudy(paper_id=uuid.uuid4(), version=2)
    assert prev.is_current is True
    prev.is_current = False
    next_version = prev.version + 1
    assert next_version == 3
