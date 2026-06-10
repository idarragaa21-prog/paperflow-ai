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
from app.models.project import Project
from app.models.user import User
from app.services.meta_runs_service import _effect_from_2x2


@compiles(PGUUID, "sqlite")
def _uuid(_t, _c, **_k):
    return "TEXT"


@compiles(JSONB, "sqlite")
def _jsonb(_t, _c, **_k):
    return "TEXT"


@compiles(INET, "sqlite")
def _inet(_t, _c, **_k):
    return "TEXT"


@compiles(ARRAY, "sqlite")
def _array(_t, _c, **_k):
    return "TEXT"


_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
_session_maker = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with _session_maker() as session:
        yield session


@pytest_asyncio.fixture(scope="module", autouse=True)
async def setup_db():
    async with _engine.begin() as conn:
        import app.models  # noqa: F401

        await conn.run_sync(Base.metadata.create_all)
    try:
        yield
    finally:
        await _engine.dispose()


@pytest_asyncio.fixture
async def test_user() -> User:
    async with _session_maker() as session:
        user = User(
            id=uuid.uuid4(),
            email=f"manual-{uuid.uuid4().hex[:8]}@paperflow.example.com",
            full_name="Manual Analyst",
            password_hash=hash_password("pass12345"),
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest_asyncio.fixture
async def authed_client(test_user: User) -> AsyncGenerator[AsyncClient, None]:
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = lambda: test_user
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


def test_effect_from_2x2_matches_known_odds_ratio():
    # ARISTOTLE-like apixaban arm: OR ~ 0.79.
    result = _effect_from_2x2(212, 8908, 265, 8795, measure="OR")
    assert result is not None
    import math

    assert round(math.exp(result["log_effect"]), 2) == 0.79
    assert 0.08 < result["se"] < 0.11


def test_effect_from_2x2_applies_continuity_correction_for_zero_cell():
    result = _effect_from_2x2(0, 50, 8, 42, measure="OR")
    assert result is not None  # would divide by zero without the 0.5 correction


@pytest.mark.asyncio
class TestManualImportPipeline:
    async def test_import_to_meta_run_offline(self, authed_client: AsyncClient, test_user: User):
        async with _session_maker() as session:
            project = Project(user_id=test_user.id, title="Manual import project")
            session.add(project)
            await session.commit()
            await session.refresh(project)
        pid = str(project.id)

        # Import prepared 2x2 data — no LLM, no PDFs.
        studies = [
            {
                "study_label": f"Trial {i}",
                "year": 2010 + i,
                "effects": [
                    {
                        "outcome_name": "Stroke",
                        "arm_intervention": "DOAC",
                        "arm_control": "Warfarin",
                        "effect_measure": "OR",
                        "outcome_type": "binary",
                        "a_events": ev_e,
                        "b_non_events": 1000 - ev_e,
                        "c_events": ev_c,
                        "d_non_events": 1000 - ev_c,
                    }
                ],
            }
            for i, (ev_e, ev_c) in enumerate([(20, 28), (24, 30), (15, 22), (30, 34)])
        ]
        resp = await authed_client.post("/meta/studies/import", json={"project_id": pid, "studies": studies})
        assert resp.status_code == 200, resp.text
        assert resp.json()["imported_studies"] == 4

        # Build matrix from the imported studies.
        matrix_resp = await authed_client.post("/matrix/build", json={"project_id": pid})
        assert matrix_resp.status_code == 200, matrix_resp.text
        version_id = matrix_resp.json()["id"]
        assert matrix_resp.json()["summary"]["rows_total"] >= 4

        # Derive a binary random-effects dataset.
        derive_resp = await authed_client.post(
            "/datasets/derive",
            json={
                "project_id": pid,
                "matrix_version_id": version_id,
                "preset": "meta_binary_random",
                "title": "imported",
            },
        )
        assert derive_resp.status_code == 200, derive_resp.text
        dataset = derive_resp.json()
        assert dataset["row_count"] == 4

        # Run the meta-analysis fully offline (Python fallback).
        run_resp = await authed_client.post(
            "/meta/runs",
            json={
                "project_id": pid,
                "derived_dataset_id": dataset["id"],
                "preset": "meta_binary_random",
                "title": "pooled",
            },
        )
        assert run_resp.status_code == 200, run_resp.text
        run = run_resp.json()
        assert run["status"] == "completed"
        assert run["engine"] == "python-local-fallback"
        summary = run["summary"]
        assert summary["k"] == 4
        assert summary["estimate"] > 0  # pooled OR on the natural scale
        artifact_types = {a["artifact_type"] for a in run["artifacts"]}
        assert "effect_table_csv" in artifact_types
        assert any(t.startswith("figure_forest") for t in artifact_types)

    async def test_create_single_study_requires_project(self, authed_client: AsyncClient):
        resp = await authed_client.post("/meta/studies", json={"design": "RCT"})
        assert resp.status_code == 400
