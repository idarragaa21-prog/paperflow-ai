from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace
import uuid

import pytest

from app.models.membership import ProjectMembership
from app.models.project import Project
from app.services.permissions import get_project_membership, list_accessible_projects, role_allows

OWNER_ID = uuid.UUID("10000000-0000-0000-0000-000000000001")
USER_ID = uuid.UUID("10000000-0000-0000-0000-000000000002")


class FakeScalar:
    def __init__(self, items=None):
        self._items = items or []

    def all(self):
        return list(self._items)

    def first(self):
        return self._items[0] if self._items else None


class FakeResult:
    def __init__(self, items=None):
        self._items = items or []

    def scalars(self):
        return FakeScalar(items=self._items)

    def all(self):
        return list(self._items)


class FakeSession:
    def __init__(self, *, projects=None, memberships=None):
        self.projects = projects or []
        self.memberships = memberships or []
        self._clock = datetime(2026, 1, 1, 9, 0, 0)

    def _next_timestamp(self) -> datetime:
        self._clock = self._clock + timedelta(seconds=1)
        return self._clock

    def add(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()
        if getattr(obj, "created_at", None) is None:
            obj.created_at = self._next_timestamp()
        if isinstance(obj, ProjectMembership) and obj not in self.memberships:
            self.memberships.append(obj)

    async def flush(self):
        return None

    async def get(self, model, obj_id):
        if model is Project:
            return next((project for project in self.projects if project.id == obj_id), None)
        return None

    async def execute(self, stmt):
        sql = str(stmt)
        params = stmt.compile().params

        if "FROM project_memberships" in sql and "JOIN" not in sql:
            project_id = next((value for key, value in params.items() if "project_id" in key), None)
            user_id = next((value for key, value in params.items() if "user_id" in key), None)
            items = [
                membership
                for membership in self.memberships
                if (project_id is None or membership.project_id == project_id) and (user_id is None or membership.user_id == user_id)
            ]
            return FakeResult(items=items)

        if "JOIN project_memberships" in sql and "FROM projects" in sql:
            user_id = next((value for key, value in params.items() if "user_id" in key), None)
            rows: list[tuple[Project, str | None]] = []
            for project in self.projects:
                if project.user_id == user_id:
                    rows.append((project, None))
            for membership in self.memberships:
                if membership.user_id != user_id:
                    continue
                project = next((item for item in self.projects if item.id == membership.project_id), None)
                if project is not None:
                    rows.append((project, membership.role))
            return FakeResult(items=rows)

        return FakeResult(items=[])


def make_project(*, owner_id: uuid.UUID, title: str) -> Project:
    project = Project(user_id=owner_id, title=title, description=None, clinical_area=None, runtime_mode="local_only")
    project.id = uuid.uuid4()
    project.created_at = datetime(2026, 1, 1, 10, 0, 0)
    return project


def make_membership(project_id: uuid.UUID, user_id: uuid.UUID, role: str) -> ProjectMembership:
    membership = ProjectMembership(project_id=project_id, user_id=user_id, role=role)
    membership.id = uuid.uuid4()
    membership.created_at = datetime(2026, 1, 1, 10, 1, 0)
    return membership


def test_role_allows_orders_roles_correctly():
    assert role_allows("owner", "viewer") is True
    assert role_allows("editor", "reviewer") is True
    assert role_allows("reviewer", "editor") is False
    assert role_allows("viewer", "owner") is False


@pytest.mark.asyncio
async def test_get_project_membership_falls_back_to_owner_membership():
    project = make_project(owner_id=OWNER_ID, title="Owner fallback")
    db = FakeSession(projects=[project], memberships=[])

    found_project, membership = await get_project_membership(db, project_id=project.id, user_id=OWNER_ID)

    assert found_project is project
    assert membership is not None
    assert membership.role == "owner"
    assert len(db.memberships) == 1
    assert db.memberships[0].user_id == OWNER_ID


@pytest.mark.asyncio
async def test_list_accessible_projects_prefers_highest_role_per_project():
    owned_project = make_project(owner_id=USER_ID, title="Owned")
    shared_project = make_project(owner_id=OWNER_ID, title="Shared")
    shared_project.created_at = datetime(2026, 1, 1, 11, 0, 0)

    memberships = [
        make_membership(shared_project.id, USER_ID, "viewer"),
        make_membership(shared_project.id, USER_ID, "editor"),
    ]
    db = FakeSession(projects=[owned_project, shared_project], memberships=memberships)
    user = SimpleNamespace(id=USER_ID)

    accessible = await list_accessible_projects(db, user=user)
    roles_by_project = {project.title: role for project, role in accessible}

    assert roles_by_project["Owned"] == "owner"
    assert roles_by_project["Shared"] == "editor"
    assert len(accessible) == 2
