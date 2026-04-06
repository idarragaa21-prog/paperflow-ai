from __future__ import annotations

import uuid
from datetime import datetime

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


class FakeScalar:
    def __init__(self, items=None):
        self._items = items or []

    def first(self):
        return self._items[0] if self._items else None

    def all(self):
        return list(self._items)


class FakeResult:
    def __init__(self, items=None):
        self._items = items or []

    def scalars(self):
        return FakeScalar(self._items)

    def all(self):
        return list(self._items)


class FakeProject:
    def __init__(self, project_id: uuid.UUID, user_id: uuid.UUID):
        self.id = project_id
        self.user_id = user_id


class FakeStudy:
    def __init__(self, study_id: uuid.UUID, project_id: uuid.UUID):
        self.id = study_id
        self.project_id = project_id
        self.paper_id = uuid.uuid4()
        self.batch_id = None
        self.version = 1
        self.is_current = True
        self.study_json = {}
        self.extraction_confidence = 0.5
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()


class FakeEffect:
    def __init__(self, effect_id: uuid.UUID, extracted_study_id: uuid.UUID):
        self.id = effect_id
        self.extracted_study_id = extracted_study_id
        self.manually_edited = False
        self.edited_at = None

        self.outcome_name = "Outcome"
        self.effect_measure = "OR"
        self.a_events = None
        self.b_non_events = None
        self.c_events = None
        self.d_non_events = None
        self.comments = None


class FakeSession:
    def __init__(self, project: FakeProject, study: FakeStudy, effects: dict[uuid.UUID, FakeEffect]):
        self._project = project
        self._study = study
        self._effects = effects

    async def get(self, model, obj_id):
        name = getattr(model, "__name__", "")
        if name == "Project":
            return self._project if obj_id == self._project.id else None
        if name == "ExtractedStudy":
            return self._study if obj_id == self._study.id else None
        if name == "ExtractedEffectSize":
            return self._effects.get(obj_id)
        return None

    async def commit(self):
        return None

    async def execute(self, stmt):
        sql = str(stmt)
        if "FROM project_memberships" in sql:
            return FakeResult([])
        if "FROM extracted_effect_sizes" in sql:
            return FakeResult(list(self._effects.values()))
        raise AssertionError(f"execute() should not be called with stmt: {sql}")


@pytest.mark.asyncio
async def test_patch_effects_batch_updates_multiple_rows():
    from app.api import deps

    user_id = uuid.UUID("00000000-0000-0000-0000-000000000000")
    project_id = uuid.uuid4()
    study_id = uuid.uuid4()

    project = FakeProject(project_id, user_id)
    study = FakeStudy(study_id, project_id)

    eff1_id = uuid.uuid4()
    eff2_id = uuid.uuid4()
    eff1 = FakeEffect(eff1_id, study_id)
    eff2 = FakeEffect(eff2_id, study_id)

    db = FakeSession(project=project, study=study, effects={eff1_id: eff1, eff2_id: eff2})

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
            f"/meta/studies/{study_id}/effects",
            json={
                "updates": [
                    {"id": str(eff1_id), "patch": {"a_events": 10, "b_non_events": 90, "comments": "edited1"}},
                    {"id": str(eff2_id), "patch": {"a_events": 1, "b_non_events": 9, "comments": "edited2"}},
                ]
            },
            headers={"X-CSRF-Token": "abc"},
        )
        assert r.status_code == 200
        assert r.json()["updated"] == 2

    assert eff1.a_events == 10
    assert eff1.b_non_events == 90
    assert eff1.comments == "edited1"
    assert eff1.manually_edited is True
    assert eff1.edited_at is not None

    assert eff2.a_events == 1
    assert eff2.b_non_events == 9
    assert eff2.comments == "edited2"
    assert eff2.manually_edited is True
    assert eff2.edited_at is not None

    app.dependency_overrides = {}
