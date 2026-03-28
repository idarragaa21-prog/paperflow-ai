from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.draft import Draft, DraftSection
from app.models.project import Project
from app.models.user import User


class FakeScalarResult:
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
        return FakeScalarResult(self._items)


class FakeSession:
    def __init__(self, *, project: Project, draft: Draft):
        self.project = project
        self.draft = draft

    def add(self, obj):
        if isinstance(obj, DraftSection) and getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()
        return None

    async def commit(self):
        return None

    async def refresh(self, obj, attribute_names=None):
        return None

    async def get(self, model, obj_id):
        if model is Project and self.project.id == obj_id:
            return self.project
        return None

    async def execute(self, stmt):
        sql = str(stmt)
        params = stmt.compile().params
        if "FROM drafts" in sql:
            draft_id = next((value for key, value in params.items() if "id" in key), None)
            if draft_id is None or self.draft.id == draft_id:
                return FakeResult([self.draft])
        return FakeResult([])


def build_user(email: str) -> User:
    return User(
        id=uuid.uuid4(),
        email=email,
        password_hash="hashed",
        full_name="Owner",
        is_active=True,
    )


async def _authed_client(db: FakeSession, user: User):
    from app.api import deps

    async def get_db_override():
        yield db

    async def get_current_user_override(request=None, db=None):
        return user

    app.dependency_overrides[deps.get_db] = get_db_override
    app.dependency_overrides[deps.get_current_user] = get_current_user_override

    transport = ASGITransport(app=app)
    client = AsyncClient(transport=transport, base_url="http://test")
    client.cookies.set("access_token", "token")
    client.cookies.set("csrf_token", "csrf-123")
    return client


@pytest.mark.asyncio
async def test_enhance_draft_with_clinical_adds_section_and_bumps_version(monkeypatch):
    import app.services.clinical.generator as clinical_generator

    owner = build_user("owner@example.com")
    project = Project(user_id=owner.id, title="ACL Project", description=None, clinical_area=None, runtime_mode="local_only")
    project.id = uuid.uuid4()

    intro = DraftSection(
        id=uuid.uuid4(),
        draft_id=uuid.uuid4(),
        heading="Introduction",
        position=0,
        content="Existing synthesis about ACL reconstruction outcomes and rehabilitation.",
        generated_with_model=None,
        confidence=0.5,
    )
    draft = Draft(project_id=project.id, title="ACL Reconstruction Outcomes", status="draft", version=2)
    draft.id = intro.draft_id
    draft.sections = [intro]

    db = FakeSession(project=project, draft=draft)

    async def fake_generate_clinical_sheet(*, db, sheet, progress_cb=None):
        assert sheet.topic == "ACL Reconstruction Outcomes"
        assert "Introduction" in str(sheet.input_params.get("context") or "")
        return {
            "content_markdown": "## Executive summary\n\nEvidence-backed synthesis.",
            "format_version": "clinical_pro_v1",
            "llm_model": "claude-sonnet-4-6",
            "warnings": ["Used project evidence"],
            "sources_used": {"papers": [{"paper_id": "paper-1"}]},
        }

    monkeypatch.setattr(clinical_generator, "generate_clinical_sheet", fake_generate_clinical_sheet, raising=True)

    client = await _authed_client(db, owner)
    try:
        response = await client.post(
            f"/drafts/{draft.id}/enhance-with-clinical",
            headers={"X-CSRF-Token": "csrf-123"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["version"] == 3
        assert any(section["heading"] == "Clinical evidence enrichment" for section in body["sections"])
        enriched = next(section for section in body["sections"] if section["heading"] == "Clinical evidence enrichment")
        assert "Evidence-backed synthesis" in enriched["content"]
        assert draft.metadata_json["clinical_enrichment"]["format_version"] == "clinical_pro_v1"
    finally:
        await client.aclose()
        app.dependency_overrides = {}
