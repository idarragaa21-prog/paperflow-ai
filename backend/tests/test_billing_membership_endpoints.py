from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.membership import ProjectMembership
from app.models.project import Project
from app.models.user import User


class FakeScalarResult:
    def __init__(self, items=None):
        self._items = items or []

    def first(self):
        return self._items[0] if self._items else None

    def all(self):
        return list(self._items)

    def scalar_one_or_none(self):
        return self.first()


class FakeResult:
    def __init__(self, items=None):
        self._items = items or []

    def scalars(self):
        return FakeScalarResult(self._items)

    def all(self):
        return list(self._items)

    def scalar_one_or_none(self):
        return self._items[0] if self._items else None


class FakeSession:
    def __init__(self, *, users: list[User], project: Project, memberships: list[ProjectMembership] | None = None):
        self.users = {user.id: user for user in users}
        self.project = project
        self.memberships = memberships or []

    def add(self, obj):
        if isinstance(obj, ProjectMembership):
            if getattr(obj, "id", None) is None:
                obj.id = uuid.uuid4()
            if getattr(obj, "created_at", None) is None:
                obj.created_at = datetime.now(timezone.utc)
            existing = next((item for item in self.memberships if item.project_id == obj.project_id and item.user_id == obj.user_id), None)
            if existing is None:
                self.memberships.append(obj)
            else:
                existing.role = obj.role

    async def delete(self, obj):
        self.memberships = [item for item in self.memberships if item is not obj]

    async def flush(self):
        return None

    async def commit(self):
        return None

    async def refresh(self, obj):
        return None

    async def get(self, model, obj_id):
        if model is Project:
            return self.project if self.project.id == obj_id else None
        if model is User:
            return self.users.get(uuid.UUID(str(obj_id)))
        return None

    async def execute(self, stmt):
        sql = str(stmt)
        params = stmt.compile().params

        if "FROM users" in sql:
            email = next((value for key, value in params.items() if "email" in key), None)
            if email is None:
                return FakeResult(items=[])
            user = next((item for item in self.users.values() if item.email == email), None)
            return FakeResult(items=[user] if user else [])

        if "FROM project_memberships JOIN users" in sql:
            project_id = next((value for key, value in params.items() if "project_id" in key), None)
            rows = []
            for membership in self.memberships:
                if project_id is not None and membership.project_id != project_id:
                    continue
                user = self.users.get(membership.user_id)
                if user is not None:
                    rows.append((membership, user))
            return FakeResult(items=rows)

        if "FROM project_memberships" in sql:
            project_id = next((value for key, value in params.items() if "project_id" in key), None)
            user_id = next((value for key, value in params.items() if "user_id" in key), None)
            matches = [
                membership
                for membership in self.memberships
                if (project_id is None or membership.project_id == project_id)
                and (user_id is None or membership.user_id == user_id)
            ]
            return FakeResult(items=matches)

        return FakeResult(items=[])


def build_user(email: str, *, full_name: str | None = None) -> User:
    return User(
        id=uuid.uuid4(),
        email=email,
        password_hash="hashed",
        full_name=full_name,
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
async def test_billing_endpoints_return_summary_and_history(monkeypatch):
    from app.services.billing.usage_tracker import UsageTracker

    fake_user = build_user("owner@example.com", full_name="Owner")
    fake_project = Project(user_id=fake_user.id, title="Proyecto", description=None, clinical_area=None, runtime_mode="local_only")
    fake_project.id = uuid.uuid4()
    db = FakeSession(users=[fake_user], project=fake_project)

    async def fake_summary(self, user_id, period="month"):
        return {
            "period": period,
            "month": "2026-03",
            "tier": "free",
            "quota_calls": 10,
            "calls_used": 2,
            "quota_remaining": 8,
            "tokens_in": 1500,
            "tokens_out": 500,
            "total_tokens": 2000,
            "cost_usd": 0.018,
            "models": [{"model": "claude-sonnet-4-6", "calls": 2, "tokens_in": 1500, "tokens_out": 500, "total_tokens": 2000}],
            "recent": [],
        }

    async def fake_history(self, user_id, months=6):
        return {"months": [{"month": "2026-03", "calls": 2, "tokens_in": 1500, "tokens_out": 500, "total_tokens": 2000, "cost_usd": 0.018}]}

    monkeypatch.setattr(UsageTracker, "get_usage_summary", fake_summary, raising=True)
    monkeypatch.setattr(UsageTracker, "get_usage_history", fake_history, raising=True)

    client = await _authed_client(db, fake_user)
    try:
        usage = await client.get("/billing/usage")
        history = await client.get("/billing/history")
        assert usage.status_code == 200
        assert history.status_code == 200
        assert usage.json()["total_tokens"] == 2000
        assert history.json()["months"][0]["calls"] == 2
    finally:
        await client.aclose()
        app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_membership_endpoints_invite_list_update_and_delete():
    owner = build_user("owner@example.com", full_name="Owner")
    invited = build_user("editor@example.com", full_name="Editor")
    project = Project(user_id=owner.id, title="Proyecto", description=None, clinical_area=None, runtime_mode="local_only")
    project.id = uuid.uuid4()
    db = FakeSession(users=[owner, invited], project=project, memberships=[])

    client = await _authed_client(db, owner)
    try:
        listed = await client.get(f"/projects/{project.id}/members")
        assert listed.status_code == 200
        assert listed.json()[0]["email"] == owner.email
        assert listed.json()[0]["role"] == "owner"

        created = await client.post(
            f"/projects/{project.id}/members",
            json={"email": invited.email, "role": "editor"},
            headers={"X-CSRF-Token": "csrf-123"},
        )
        assert created.status_code == 200
        assert created.json()["role"] == "editor"

        patched = await client.patch(
            f"/projects/{project.id}/members/{invited.id}",
            json={"role": "viewer"},
            headers={"X-CSRF-Token": "csrf-123"},
        )
        assert patched.status_code == 200
        assert patched.json()["role"] == "viewer"

        deleted = await client.delete(
            f"/projects/{project.id}/members/{invited.id}",
            headers={"X-CSRF-Token": "csrf-123"},
        )
        assert deleted.status_code == 200
        assert deleted.json()["ok"] is True
    finally:
        await client.aclose()
        app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_membership_mutations_require_owner():
    owner = build_user("owner@example.com", full_name="Owner")
    viewer = build_user("viewer@example.com", full_name="Viewer")
    invited = build_user("editor@example.com", full_name="Editor")
    project = Project(user_id=owner.id, title="Proyecto", description=None, clinical_area=None, runtime_mode="local_only")
    project.id = uuid.uuid4()
    membership = ProjectMembership(project_id=project.id, user_id=viewer.id, role="viewer")
    membership.id = uuid.uuid4()
    membership.created_at = datetime.now(timezone.utc)
    db = FakeSession(users=[owner, viewer, invited], project=project, memberships=[membership])

    client = await _authed_client(db, viewer)
    try:
        created = await client.post(
            f"/projects/{project.id}/members",
            json={"email": invited.email, "role": "editor"},
            headers={"X-CSRF-Token": "csrf-123"},
        )
        assert created.status_code == 403
    finally:
        await client.aclose()
        app.dependency_overrides = {}
