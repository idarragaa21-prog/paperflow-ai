from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services.analysis_service import (
    _normalize_figure_payload,
    _normalize_text_value,
    create_dataset,
    export_analysis_run,
)


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


@pytest.mark.asyncio
async def test_create_dataset_persists_columns_for_valid_rows(monkeypatch):
    db = _CaptureDB()

    async def _save_dataset_bytes(*, data, filename, project_id):
        return {"file_path": f"datasets/{filename}", "filename": filename, "project_id": str(project_id)}

    monkeypatch.setattr("app.services.analysis_service.storage_manager.save_dataset_bytes", _save_dataset_bytes)

    dataset = await create_dataset(
        db,
        project_id=uuid4(),
        title="valid",
        description=None,
        rows=[{"group": "A", "value": 12}, {"group": "B", "value": 18}],
    )

    assert dataset.title == "valid"
    assert dataset.row_count == 2
    assert dataset.column_count == 2
    assert {column.name for column in dataset.columns} == {"group", "value"}


def test_normalize_text_value_flattens_list_payloads():
    assert _normalize_text_value(["line 1", "line 2"]) == "line 1\n\nline 2"
    assert _normalize_text_value("plain text") == "plain text"


def test_normalize_figure_payload_flattens_list_fields():
    normalized = _normalize_figure_payload(
        {
            "title": ["Analysis figure: group_comparison"],
            "caption": ["Generated from group_comparison analysis."],
            "analysis_type": ["group_comparison"],
        }
    )

    assert normalized["title"] == "Analysis figure: group_comparison"
    assert normalized["caption"] == "Generated from group_comparison analysis."
    assert normalized["analysis_type"] == "group_comparison"


def test_normalize_figure_payload_marks_missing_payload_as_degraded():
    normalized = _normalize_figure_payload(None)

    assert normalized["title"] == "Summary figure unavailable (degraded fallback)"
    assert normalized["degraded"] is True
