from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


class FakeBatch:
    def __init__(self, batch_id: uuid.UUID, user_id: uuid.UUID, project_id: uuid.UUID):
        self.id = batch_id
        self.user_id = user_id
        self.project_id = project_id
        self.title = None
        self.status = "created"
        self.created_at = datetime.utcnow()


class FakeProject:
    def __init__(self, project_id: uuid.UUID, user_id: uuid.UUID):
        self.id = project_id
        self.user_id = user_id


class FakeEffect:
    def __init__(self, effect_id: uuid.UUID, extracted_study_id: uuid.UUID):
        self.id = effect_id
        self.extracted_study_id = extracted_study_id
        self.manually_edited = False
        self.edited_at = None
        self.outcome_name = "Mortality"
        self.effect_measure = "OR"


class FakeROB:
    def __init__(self, rob_id: uuid.UUID, extracted_study_id: uuid.UUID):
        self.id = rob_id
        self.extracted_study_id = extracted_study_id
        self.manually_edited = False
        self.edited_at = None
        self.tool = "ROB2"
        self.domain = "randomization"
        self.judgement = "unclear"


class FakeStudy:
    def __init__(self, study_id: uuid.UUID, project_id: uuid.UUID, paper_id: uuid.UUID):
        self.id = study_id
        self.project_id = project_id
        self.paper_id = paper_id
        self.batch_id = None
        self.version = 1
        self.is_current = True
        self.study_json = {}
        self.extraction_confidence = 0.5
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()


@dataclass
class FakeSessionConfig:
    batch: FakeBatch | None = None
    project: FakeProject | None = None
    study: FakeStudy | None = None
    effect: FakeEffect | None = None
    rob: FakeROB | None = None


class FakeSession:
    def __init__(self, config: FakeSessionConfig):
        self._batch = config.batch
        self._project = config.project
        self._study = config.study
        self._effect = config.effect
        self._rob = config.rob

    async def get(self, model, obj_id):
        name = getattr(model, "__name__", "")
        if name == "MetaExtractionBatch":
            return self._batch if self._batch and obj_id == self._batch.id else None
        if name == "Project":
            return self._project if self._project and obj_id == self._project.id else None
        if name == "ExtractedStudy":
            return self._study if self._study and obj_id == self._study.id else None
        if name == "ExtractedEffectSize":
            return self._effect if self._effect and obj_id == self._effect.id else None
        if name == "ExtractedRiskOfBias":
            return self._rob if self._rob and obj_id == self._rob.id else None
        return None

    async def commit(self):
        return None

    async def execute(self, stmt):
        class R:
            def __init__(self):
                pass

            def scalars(self):
                class S:
                    def all(self):
                        return []

                return S()

            def first(self):
                return None

        return R()


@pytest.mark.asyncio
async def test_ownership_check_meta_batch_denies(monkeypatch):
    from app.api import deps

    # user A tries to access batch owned by user B -> 404
    user_a = uuid.UUID("00000000-0000-0000-0000-000000000000")
    user_b = uuid.UUID("11111111-1111-1111-1111-111111111111")
    project_id = uuid.uuid4()
    batch_id = uuid.uuid4()

    batch = FakeBatch(batch_id, user_b, project_id)
    project = FakeProject(project_id, user_b)

    db = FakeSession(config=FakeSessionConfig(batch=batch, project=project, study=None, effect=None, rob=None))

    async def get_db_override():
        yield db

    class U:
        id = user_a
        is_active = True

    async def fake_user(request=None, db=None):
        return U()

    app.dependency_overrides[deps.get_db] = get_db_override
    app.dependency_overrides[deps.get_current_user] = fake_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.cookies.set("csrf_token", "abc")
        ac.cookies.set("access_token", "x")
        r = await ac.get(f"/meta/batches/{batch_id}")
        assert r.status_code == 404

    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_patch_effect_marks_manually_edited(monkeypatch):
    from app.api import deps

    user_id = uuid.UUID("00000000-0000-0000-0000-000000000000")
    project_id = uuid.uuid4()
    study_id = uuid.uuid4()
    paper_id = uuid.uuid4()
    effect_id = uuid.uuid4()

    project = FakeProject(project_id, user_id)
    study = FakeStudy(study_id, project_id, paper_id)
    eff = FakeEffect(effect_id, study_id)

    db = FakeSession(config=FakeSessionConfig(batch=None, project=project, study=study, effect=eff, rob=None))

    async def get_db_override():
        yield db

    class U:
        id = user_id
        is_active = True

    async def fake_user(request=None, db=None):
        return U()

    app.dependency_overrides[deps.get_db] = get_db_override
    app.dependency_overrides[deps.get_current_user] = fake_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.cookies.set("csrf_token", "abc")
        ac.cookies.set("access_token", "x")
        r = await ac.patch(
            f"/meta/studies/{study_id}/effects/{effect_id}",
            json={"comments": "manual"},
            headers={"X-CSRF-Token": "abc"},
        )
        assert r.status_code == 200

    assert eff.manually_edited is True
    assert eff.edited_at is not None

    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_patch_rob_marks_manually_edited(monkeypatch):
    from app.api import deps

    user_id = uuid.UUID("00000000-0000-0000-0000-000000000000")
    project_id = uuid.uuid4()
    study_id = uuid.uuid4()
    paper_id = uuid.uuid4()
    rob_id = uuid.uuid4()

    project = FakeProject(project_id, user_id)
    study = FakeStudy(study_id, project_id, paper_id)
    rob = FakeROB(rob_id, study_id)

    db = FakeSession(config=FakeSessionConfig(batch=None, project=project, study=study, effect=None, rob=rob))

    async def get_db_override():
        yield db

    class U:
        id = user_id
        is_active = True

    async def fake_user(request=None, db=None):
        return U()

    app.dependency_overrides[deps.get_db] = get_db_override
    app.dependency_overrides[deps.get_current_user] = fake_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.cookies.set("csrf_token", "abc")
        ac.cookies.set("access_token", "x")
        r = await ac.patch(
            f"/meta/studies/{study_id}/rob/{rob_id}",
            json={"judgement": "high"},
            headers={"X-CSRF-Token": "abc"},
        )
        assert r.status_code == 200

    assert rob.manually_edited is True
    assert rob.edited_at is not None

    app.dependency_overrides = {}
