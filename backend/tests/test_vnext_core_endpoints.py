from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import ARRAY
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID as PGUUID
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_current_user, get_db
from app.core.security import hash_password
from app.database import Base
from app.main import app
from app.models.meta_extractor import ExtractedEffectSize, ExtractedStudy
from app.models.paper import Paper
from app.models.project import Project
from app.models.user import User

pytestmark = pytest.mark.asyncio


@compiles(PGUUID, "sqlite")
def _compile_uuid_sqlite(_type, _compiler, **_kw):
    return "TEXT"


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(_type, _compiler, **_kw):
    return "TEXT"


@compiles(INET, "sqlite")
def _compile_inet_sqlite(_type, _compiler, **_kw):
    return "TEXT"


@compiles(ARRAY, "sqlite")
def _compile_array_sqlite(_type, _compiler, **_kw):
    return "TEXT"


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
_session_maker = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


async def _init_db() -> None:
    async with _engine.begin() as conn:
        import app.models  # noqa: F401

        await conn.run_sync(Base.metadata.create_all)


async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with _session_maker() as session:
        yield session


@pytest_asyncio.fixture(scope="module", autouse=True)
async def setup_db():
    await _init_db()
    try:
        yield
    finally:
        await _engine.dispose()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with _session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(),
        email=f"vnext-{uuid.uuid4().hex[:8]}@paperflow.example.com",
        full_name="vNext User",
        password_hash=hash_password("pass12345"),
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def authed_client(test_user: User) -> AsyncGenerator[AsyncClient, None]:
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = lambda: test_user
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
class TestVNextCoreFlow:
    async def test_extraction_matrix_to_meta_run_pipeline(self, db_session: AsyncSession, authed_client: AsyncClient, test_user: User, monkeypatch):
        # Mock R engine response to simulate successful run
        import app.services.meta_runs_service
        import httpx
        from typing import Any

        class DummyResponse:
            def raise_for_status(self):
                pass
            def json(self):
                return {
                    "summary": {"rows": 1, "preset": "meta_binary_random", "supports_publication": True},
                    "script": "print('hello world')",
                    "engine_version": "1.0",
                    "figure_artifacts": {
                        "figure_forest": {
                            "png_base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
                        },
                        "forest": {
                            "png_base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
                        }
                    }
                }

        class DummyAsyncClient:
            def __init__(self, *args, **kwargs):
                pass
            async def __aenter__(self):
                return self
            async def __aexit__(self, exc_type, exc, tb):
                pass
            async def post(self, url: str, json: dict[str, Any] | None = None):
                return DummyResponse()

        monkeypatch.setattr(app.services.meta_runs_service.httpx, "AsyncClient", DummyAsyncClient)

        project = Project(user_id=test_user.id, title="vNext pipeline project")
        db_session.add(project)
        await db_session.flush()

        paper = Paper(
            project_id=project.id,
            title="Binary outcome trial",
            authors="Author A; Author B",
            abstract_text="Intervention reduced events versus control.",
            filename="trial.pdf",
            file_path="papers/trial.pdf",
            content_hash="hash-vnext-trial",
            pmid="12345678",
            doi="10.1000/vnext",
            processing_status="ready",
            is_processed=True,
        )
        db_session.add(paper)
        await db_session.flush()

        study = ExtractedStudy(
            project_id=project.id,
            paper_id=paper.id,
            version=1,
            is_current=True,
            study_json={"design": "randomized"},
            extraction_confidence=0.88,
        )
        db_session.add(study)
        await db_session.flush()

        effect = ExtractedEffectSize(
            extracted_study_id=study.id,
            outcome_name="Mortality",
            timepoint="12 months",
            arm_intervention="Drug",
            arm_control="Placebo",
            effect_measure="OR",
            a_events=10,
            b_non_events=90,
            c_events=20,
            d_non_events=80,
            or_value=0.44,
            log_or=-0.82,
            se_log_or=0.21,
            ci_lower_95=0.25,
            ci_upper_95=0.76,
            confidence=0.81,
            raw_extracted_value="OR 0.44 (95% CI 0.25-0.76)",
            source_page=3,
            source_locator={"page": 3, "bbox": [0, 0, 1, 1]},
        )
        db_session.add(effect)
        await db_session.commit()

        matrix_resp = await authed_client.post("/matrix/build", json={"project_id": str(project.id)})
        assert matrix_resp.status_code == 200
        matrix_data = matrix_resp.json()
        assert matrix_data["summary"]["rows_total"] >= 2
        version_id = matrix_data["id"]

        derive_resp = await authed_client.post(
            "/datasets/derive",
            json={
                "project_id": str(project.id),
                "matrix_version_id": version_id,
                "preset": "meta_binary_random",
                "title": "binary_derived",
            },
        )
        assert derive_resp.status_code == 200
        dataset_data = derive_resp.json()
        assert dataset_data["row_count"] >= 1

        run_resp = await authed_client.post(
            "/meta/runs",
            json={
                "project_id": str(project.id),
                "derived_dataset_id": dataset_data["id"],
                "preset": "meta_binary_random",
                "title": "binary run",
            },
        )
        assert run_resp.status_code == 200
        run_data = run_resp.json()
        assert run_data["status"] == "completed"
        artifact_types = {item["artifact_type"] for item in run_data["artifacts"]}
        assert "effect_table_csv" in artifact_types
        assert "script_r" in artifact_types
        assert any(item in artifact_types for item in {"session_info", "session_info_txt"})
        assert any("summary" in item for item in artifact_types)
        assert any("forest_png" in item for item in artifact_types)

        first_artifact_id = run_data["artifacts"][0]["id"]
        artifact_resp = await authed_client.get(f"/artifacts/{first_artifact_id}/download")
        assert artifact_resp.status_code == 200
        assert artifact_resp.content

    async def test_clinical_consults_and_writing_grounded_flow(self, db_session: AsyncSession, authed_client: AsyncClient, test_user: User):
        project = Project(user_id=test_user.id, title="vNext writing project")
        db_session.add(project)
        await db_session.flush()

        paper = Paper(
            project_id=project.id,
            title="Aspirin for secondary prevention",
            authors="Doe J",
            abstract_text="Aspirin reduced recurrent ischemic events in high-risk populations.",
            filename="aspirin.pdf",
            file_path="papers/aspirin.pdf",
            content_hash="hash-vnext-aspirin",
            pmid="23456789",
            processing_status="ready",
            is_processed=True,
        )
        db_session.add(paper)
        await db_session.commit()

        consult_resp = await authed_client.post(
            "/clinical/consults",
            json={
                "project_id": str(project.id),
                "question": "Should we use aspirin for secondary prevention after ischemic stroke?",
                "mode": "brief",
                "use_project_library": True,
                "use_pubmed": False,
            },
        )
        assert consult_resp.status_code == 200
        consult_data = consult_resp.json()
        assert consult_data["mode"] == "brief"
        assert len(consult_data["sources"]) >= 1

        doc_resp = await authed_client.post(
            "/writing/documents",
            json={
                "project_id": str(project.id),
                "title": "Stroke manuscript",
                "mode": "meta_analysis",
            },
        )
        assert doc_resp.status_code == 200
        doc_data = doc_resp.json()
        assert doc_data["mode"] == "meta_analysis"

        generate_resp = await authed_client.post(f"/writing/documents/{doc_data['id']}/sections/results")
        assert generate_resp.status_code == 200
        generated_doc = generate_resp.json()
        results_section = next(item for item in generated_doc["sections"] if item["section_key"] == "results")
        assert "Grounded section generated" in results_section["content_markdown"]

        citations_resp = await authed_client.post(f"/writing/documents/{doc_data['id']}/citations/resolve")
        assert citations_resp.status_code == 200
        citations_data = citations_resp.json()
        assert citations_data["count"] >= 1
