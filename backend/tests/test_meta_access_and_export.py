from __future__ import annotations

import uuid
from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.meta import router as meta_router
from app.services.meta_extractor.export_service import build_export_payload, create_meta_export


class _FakeScalar:
    def __init__(self, items):
        self._items = items

    def all(self):
        return self._items

    def first(self):
        return self._items[0] if self._items else None


class _FakeExecuteResult:
    def __init__(self, items):
        self._items = items

    def scalars(self):
        return _FakeScalar(self._items)

    def all(self):
        return self._items


class _MetaSession:
    def __init__(self, *, batches=None):
        self.batches = batches or []
        self.added = []

    async def execute(self, stmt):
        stmt_text = str(stmt)
        if "meta_extraction_batches" in stmt_text:
            return _FakeExecuteResult(self.batches)
        return _FakeExecuteResult([])

    async def get(self, model, obj_id):
        name = getattr(model, "__name__", "")
        if name == "MetaExport":
            return None
        for batch in self.batches:
            if getattr(batch, "id", None) == obj_id:
                return batch
        return None

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        return None

    async def refresh(self, obj):
        return None


def _meta_app(db: _MetaSession, *, user_id: uuid.UUID) -> FastAPI:
    from app.api import deps

    app = FastAPI()
    app.include_router(meta_router)

    async def get_db_override():
        yield db

    class U:
        id = user_id
        is_active = True

    async def fake_user(request=None, db=None):
        del request, db
        return U()

    app.dependency_overrides[deps.get_db] = get_db_override
    app.dependency_overrides[deps.get_current_user] = fake_user
    return app


@pytest.mark.asyncio
async def test_meta_batches_list_uses_project_rbac(monkeypatch):
    user_id = uuid.uuid4()
    project_id = uuid.uuid4()
    batch = SimpleNamespace(id=uuid.uuid4(), title="Batch", status="created", created_at=datetime.utcnow(), project_id=project_id)
    db = _MetaSession(batches=[batch])
    app = _meta_app(db, user_id=user_id)

    async def allow_access(db, *, project_id, user, required_role="viewer"):
        del db, user, required_role
        return SimpleNamespace(id=project_id, user_id=uuid.uuid4()), SimpleNamespace(role="reviewer")

    monkeypatch.setattr("app.api.meta.require_project_access", allow_access)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.cookies.set("csrf_token", "abc")
        ac.cookies.set("access_token", "x")
        response = await ac.get(f"/meta/batches?project_id={project_id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == str(batch.id)


@pytest.mark.asyncio
async def test_meta_export_endpoint_allows_editor(monkeypatch):
    user_id = uuid.uuid4()
    project_id = uuid.uuid4()
    db = _MetaSession()
    app = _meta_app(db, user_id=user_id)

    async def allow_access(db, *, project_id, user, required_role="viewer"):
        del db, user
        assert required_role == "editor"
        return SimpleNamespace(id=project_id, user_id=uuid.uuid4()), SimpleNamespace(role="editor")

    calls: list[dict[str, object]] = []

    class _FakeQueue:
        def enqueue(self, *args, **kwargs):
            calls.append({"args": args, "kwargs": kwargs})
            return SimpleNamespace(id="rq-meta-export")

    monkeypatch.setattr("app.api.meta.require_project_access", allow_access)
    monkeypatch.setattr("app.api.meta.get_job_queue", lambda name="documents": _FakeQueue())

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.cookies.set("csrf_token", "abc")
        ac.cookies.set("access_token", "x")
        response = await ac.post("/meta/export", json={"project_id": str(project_id)}, headers={"X-CSRF-Token": "abc"})
        assert response.status_code == 200
        assert response.json()["job_id"]
        assert db.added[-1].job_type == "meta_export_xlsx"
        assert calls[-1]["kwargs"]["args"][-1] == "xlsx"


@pytest.mark.asyncio
async def test_meta_export_endpoint_accepts_csv_bundle(monkeypatch):
    user_id = uuid.uuid4()
    project_id = uuid.uuid4()
    db = _MetaSession()
    app = _meta_app(db, user_id=user_id)

    calls: list[dict[str, object]] = []

    async def allow_access(db, *, project_id, user, required_role="viewer"):
        del db, user
        assert required_role == "editor"
        return SimpleNamespace(id=project_id, user_id=uuid.uuid4()), SimpleNamespace(role="editor")

    class _FakeQueue:
        def enqueue(self, *args, **kwargs):
            calls.append({"args": args, "kwargs": kwargs})
            return SimpleNamespace(id="rq-meta-export-csv")

    monkeypatch.setattr("app.api.meta.require_project_access", allow_access)
    monkeypatch.setattr("app.api.meta.get_job_queue", lambda name="documents": _FakeQueue())

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.cookies.set("csrf_token", "abc")
        ac.cookies.set("access_token", "x")
        response = await ac.post(
            "/meta/export",
            json={"project_id": str(project_id), "format": "csv"},
            headers={"X-CSRF-Token": "abc"},
        )
        assert response.status_code == 200
        assert response.json()["job_id"]
        assert db.added[-1].job_type == "meta_export_csv"
        assert calls[-1]["kwargs"]["args"][-1] == "csv"


class _ExportSession:
    async def execute(self, stmt):
        return _FakeExecuteResult([])

    def add(self, obj):
        del obj

    async def commit(self):
        return None

    async def refresh(self, obj):
        return None


class _PayloadSession:
    def __init__(self, *, studies, papers, effects, robs):
        self.studies = studies
        self.papers = papers
        self.effects = effects
        self.robs = robs

    async def execute(self, stmt):
        stmt_text = str(stmt)
        if "extracted_studies" in stmt_text:
            return _FakeExecuteResult(self.studies)
        if "FROM papers" in stmt_text:
            return _FakeExecuteResult(self.papers)
        if "extracted_effect_sizes" in stmt_text:
            return _FakeExecuteResult(self.effects)
        if "extracted_risk_of_bias" in stmt_text:
            return _FakeExecuteResult(self.robs)
        return _FakeExecuteResult([])


@pytest.mark.asyncio
async def test_create_meta_export_requires_extracted_studies():
    db = _ExportSession()
    with pytest.raises(ValueError, match="No extracted studies available for export"):
        await create_meta_export(db=db, project_id=uuid.uuid4(), batch_id=None)


@pytest.mark.asyncio
async def test_build_export_payload_includes_full_quantitative_and_qualitative_metadata():
    project_id = uuid.uuid4()
    paper_id = uuid.uuid4()
    study_id = uuid.uuid4()
    now = datetime.utcnow()

    study = SimpleNamespace(
        id=study_id,
        project_id=project_id,
        paper_id=paper_id,
        batch_id=None,
        extraction_confidence=0.91,
        created_at=now,
        updated_at=now,
        study_json={
            "citation_key": "smith2024",
            "title": "Shoulder instability trial",
            "first_author": "Smith",
            "year": 2024,
            "journal": "J Shoulder Res",
            "study_design": "RCT",
            "arms": [{"arm_name": "Surgery"}, {"arm_name": "Rehab"}],
            "outcomes": [{"outcome_name": "Pain", "outcome_type": "continuous"}],
            "effect_sizes": [
                {
                    "outcome_name": "Pain",
                    "timepoint": "6 months",
                    "arm_intervention": "Surgery",
                    "arm_control": "Rehab",
                    "effect_measure": "MD",
                    "mean_intervention": 3.2,
                    "sd_intervention": 1.1,
                    "mean_control": 7.4,
                    "sd_control": 1.4,
                    "mean_difference": -4.2,
                    "p_value": 0.03,
                    "n_intervention_for_outcome": 32,
                    "n_control_for_outcome": 30,
                    "page_number": 5,
                    "table_id": "p5-1",
                    "source_type": "table",
                    "extraction_confidence": 0.88,
                    "comments": "Primary endpoint",
                }
            ],
            "risk_of_bias": [
                {
                    "tool": "ROB2",
                    "domain_name": "randomization",
                    "judgement": "low",
                    "support_for_judgement": "Sequence generation described",
                }
            ],
            "_tables_raw": [{"table_id": "p5-1", "page": 5, "extracted_markdown": "Pain\t3.2\t7.4"}],
            "_images_ocr_raw": [{"image_id": "ocr-page-1", "page": 1, "ocr_text": "Shoulder dislocation outcomes"}],
            "_extraction_logs": [{"timestamp": now.isoformat(), "job_id": "job-1", "level": "warning", "message": "OCR used for figure legend"}],
            "_pages_used": [4, 5],
            "_tables_used": ["p5-1"],
            "_ocr_used": True,
        },
    )
    paper = SimpleNamespace(
        id=paper_id,
        title="Original PDF title",
        filename="shoulder.pdf",
        authors="Smith J; Doe A",
        doi="10.1000/test",
        pmid="12345",
        pmcid="PMC12345",
        journal="J Shoulder Res",
        publication_year=2024,
        source_provider="pubmed",
        oa_url="https://example.org/oa.pdf",
    )
    effect = SimpleNamespace(
        id=uuid.uuid4(),
        extracted_study_id=study_id,
        outcome_name="Pain",
        timepoint="6 months",
        arm_intervention="Surgery",
        arm_control="Rehab",
        effect_measure="MD",
        a_events=None,
        b_non_events=None,
        c_events=None,
        d_non_events=None,
        or_value=None,
        log_or=None,
        se_log_or=None,
        ci_lower_95=None,
        ci_upper_95=None,
        adjusted_or=None,
        adjusted_rr=None,
        adjusted_hr=None,
        adjustment_variables=None,
        is_adjusted=False,
        raw_extracted_value="3.2 vs 7.4",
        source_page=5,
        source_locator={"table_id": "p5-1"},
        source_type="table",
        confidence=0.95,
        comments="Manually confirmed",
        manually_edited=True,
        edited_at=now,
    )
    rob = SimpleNamespace(
        id=uuid.uuid4(),
        extracted_study_id=study_id,
        tool="ROB2",
        domain="randomization",
        judgement="low",
        support_text="Sequence generation described",
        manually_edited=False,
        edited_at=None,
        auto_generated=False,
    )
    db = _PayloadSession(studies=[study], papers=[paper], effects=[effect], robs=[rob])

    payload = await build_export_payload(db=db, project_id=project_id, batch_id=None)

    assert payload.studies[0]["paper_title"] == "Original PDF title"
    assert payload.studies[0]["raw_study_json"]
    assert payload.effects[0]["p_value"] == 0.03
    assert payload.effects[0]["mean_difference"] == -4.2
    assert payload.effects[0]["source_locator_json"] == '{"table_id": "p5-1"}'
    assert payload.effects[0]["manually_edited"] is True
    assert '"p_value": 0.03' in (payload.effects[0]["raw_effect_json"] or "")
    assert payload.rob[0]["raw_rob_json"]
    assert payload.tables_raw[0]["table_id"] == "p5-1"
    assert payload.images_ocr_raw[0]["ocr_text"] == "Shoulder dislocation outcomes"
    assert payload.logs[0]["message"] == "OCR used for figure legend"
