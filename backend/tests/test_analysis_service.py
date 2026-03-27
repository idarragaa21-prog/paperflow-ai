from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services.analysis_service import create_dataset, export_analysis_run


class _FakeScalarResult:
    def __init__(self, item):
        self._item = item

    def first(self):
        return self._item


class _FakeExecuteResult:
    def __init__(self, item):
        self._item = item

    def scalars(self):
        return _FakeScalarResult(self._item)


class _FakeDB:
    def __init__(self, run):
        self._run = run

    async def execute(self, stmt):
        return _FakeExecuteResult(self._run)


class _CaptureDB:
    def __init__(self):
        self.added = []
        self.flushed = False
        self.committed = False

    def add(self, item):
        self.added.append(item)

    async def flush(self):
        self.flushed = True

    async def commit(self):
        self.committed = True

    async def execute(self, stmt):
        dataset = next(item for item in self.added if getattr(item, "__class__", type("", (), {})).__name__ == "Dataset")
        dataset.columns = [item for item in self.added if getattr(item, "__class__", type("", (), {})).__name__ == "DatasetColumn"]
        return _FakeExecuteResult(dataset)


@pytest.mark.asyncio
async def test_export_analysis_run_reads_persisted_artifact(monkeypatch):
    artifact = SimpleNamespace(
        artifact_type="report_html",
        filename="report.html",
        file_path="artifacts/report.html",
        mime_type="text/html",
        metadata_json={"format": "html"},
    )
    run = SimpleNamespace(id=uuid4(), status="completed", artifacts=[artifact])
    db = _FakeDB(run)

    monkeypatch.setattr("app.services.analysis_service.storage_manager.read_bytes", lambda path: b"<html>ok</html>")

    data, mime_type, filename = await export_analysis_run(db, run=run, fmt="html")

    assert data == b"<html>ok</html>"
    assert mime_type == "text/html"
    assert filename == "report.html"


@pytest.mark.asyncio
async def test_export_analysis_run_requires_completed_status():
    run = SimpleNamespace(id=uuid4(), status="running", artifacts=[])
    db = _FakeDB(run)

    with pytest.raises(ValueError, match="not completed"):
        await export_analysis_run(db, run=run, fmt="html")


@pytest.mark.asyncio
async def test_export_analysis_run_fails_when_artifact_missing():
    run = SimpleNamespace(id=uuid4(), status="completed", artifacts=[])
    db = _FakeDB(run)

    with pytest.raises(ValueError, match="No persisted html artifact found"):
        await export_analysis_run(db, run=run, fmt="html")


@pytest.mark.asyncio
async def test_export_analysis_run_fails_when_storage_object_is_missing(monkeypatch):
    artifact = SimpleNamespace(
        artifact_type="report_pdf",
        filename="report.pdf",
        file_path="artifacts/report.pdf",
        mime_type="application/pdf",
        metadata_json={"format": "pdf"},
    )
    run = SimpleNamespace(id=uuid4(), status="completed", artifacts=[artifact])
    db = _FakeDB(run)

    def _missing(path):
        raise FileNotFoundError(path)

    monkeypatch.setattr("app.services.analysis_service.storage_manager.read_bytes", _missing)

    with pytest.raises(ValueError, match="missing from storage"):
        await export_analysis_run(db, run=run, fmt="pdf")


@pytest.mark.asyncio
async def test_create_dataset_rejects_empty_rows():
    db = _CaptureDB()

    with pytest.raises(ValueError, match="cannot be empty"):
        await create_dataset(
            db,
            project_id=uuid4(),
            title="empty",
            description=None,
            rows=[],
        )
