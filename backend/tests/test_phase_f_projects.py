from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace
import uuid

import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient

from app.api.projects import router as projects_router
from app.api.screening import router as screening_router
from app.middleware.csrf import CSRFMiddleware
from app.models.membership import ProjectMembership
from app.models.paper import Paper
from app.models.project import Project

OWNER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
EDITOR_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
REVIEWER_ID = uuid.UUID("00000000-0000-0000-0000-000000000003")
VIEWER_ID = uuid.UUID("00000000-0000-0000-0000-000000000004")


class FakeScalar:
    def __init__(self, items=None, scalar_value=None):
        self._items = items or []
        self._scalar_value = scalar_value

    def all(self):
        return list(self._items)

    def first(self):
        return self._items[0] if self._items else None

    def scalar_one_or_none(self):
        return self._scalar_value


class FakeResult:
    def __init__(self, *, items=None, scalar_value=None):
        self._items = items or []
        self._scalar_value = scalar_value

    def scalars(self):
        return FakeScalar(items=self._items, scalar_value=self._scalar_value)

    def all(self):
        return list(self._items)

    def scalar(self):
        return self._scalar_value

    def scalar_one_or_none(self):
        return self._scalar_value


class FakeSession:
    def __init__(self):
        self.projects: list[Project] = []
        self.memberships: list[ProjectMembership] = []
        self.papers: list[SimpleNamespace] = []
        self._clock = datetime(2026, 1, 1, 8, 0, 0)

    def _next_timestamp(self) -> datetime:
        self._clock = self._clock + timedelta(seconds=1)
        return self._clock

    def _param(self, params: dict[str, object], prefix: str):
        for key, value in params.items():
            if prefix in key:
                return value
        return None

    def add(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()
        if getattr(obj, "created_at", None) is None:
            obj.created_at = self._next_timestamp()

        if isinstance(obj, Project):
            if obj not in self.projects:
                self.projects.append(obj)
            return

        if isinstance(obj, ProjectMembership):
            if obj.project_id is None and getattr(obj, "project", None) is not None:
                obj.project_id = obj.project.id
            existing = next((item for item in self.memberships if item.id == obj.id), None)
            if existing is None:
                self.memberships.append(obj)
            return

        if isinstance(obj, Paper):
            paper = SimpleNamespace(
                id=obj.id,
                project_id=obj.project_id,
                title=obj.title,
                authors=obj.authors,
                journal=obj.journal,
                publication_year=obj.publication_year,
                doi=obj.doi,
                pmid=obj.pmid,
                filename=obj.filename,
                language=obj.language,
                source_provider=obj.source_provider,
                source_type=obj.source_type,
                is_open_access=obj.is_open_access,
                oa_url=obj.oa_url,
                favorite=obj.favorite,
                is_processed=obj.is_processed,
                processing_status=obj.processing_status,
                processing_warnings=obj.processing_warnings,
                created_at=obj.created_at or self._next_timestamp(),
            )
            self.papers.append(paper)

    async def commit(self):
        return None

    async def refresh(self, obj):
        return None

    async def flush(self):
        return None

    async def delete(self, obj):
        if isinstance(obj, ProjectMembership):
            self.memberships = [item for item in self.memberships if item.id != obj.id]

    async def get(self, model, obj_id):
        if model is Project:
            return next((item for item in self.projects if item.id == obj_id), None)
        if model is ProjectMembership:
            return next((item for item in self.memberships if item.id == obj_id), None)
        return None

    async def execute(self, stmt):
        sql = str(stmt)
        params = stmt.compile().params

        if "FROM project_memberships" in sql:
            if "count(" in sql.lower():
                project_id = self._param(params, "project_id")
                role = self._param(params, "role")
                count = sum(
                    1
                    for item in self.memberships
                    if (project_id is None or item.project_id == project_id) and (role is None or item.role == role)
                )
                return FakeResult(scalar_value=count)

            project_id = self._param(params, "project_id")
            user_id = self._param(params, "user_id")
            items = [
                item
                for item in self.memberships
                if (project_id is None or item.project_id == project_id) and (user_id is None or item.user_id == user_id)
            ]
            items.sort(key=lambda item: item.created_at or datetime.min)
            return FakeResult(items=items)

        if "JOIN project_memberships" in sql and "FROM projects" in sql:
            user_id = self._param(params, "user_id")
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
            rows.sort(key=lambda row: row[0].created_at or datetime.min, reverse=True)
            return FakeResult(items=rows)

        if "FROM papers" in sql:
            project_id = self._param(params, "project_id")
            year = self._param(params, "publication_year")
            processing_status = self._param(params, "processing_status")
            open_access = self._param(params, "is_open_access")
            favorite = self._param(params, "favorite")
            items = [paper for paper in self.papers if project_id is None or paper.project_id == project_id]
            if year is not None:
                items = [paper for paper in items if paper.publication_year == year]
            if processing_status is not None:
                items = [paper for paper in items if paper.processing_status == processing_status]
            if open_access is not None:
                items = [paper for paper in items if paper.is_open_access == open_access]
            if favorite is not None:
                items = [paper for paper in items if paper.favorite == favorite]
            items.sort(key=lambda item: (item.created_at or datetime.min, item.id), reverse=True)
            if "count(" in sql.lower():
                return FakeResult(scalar_value=len(items))
            return FakeResult(items=items)

        return FakeResult(items=[])


def seed_project(db: FakeSession) -> Project:
    project = Project(user_id=OWNER_ID, title="PaperFlow", description="Workspace", clinical_area=None, runtime_mode="local_only")
    project.archived = False
    db.add(project)
    db.add(ProjectMembership(project_id=project.id, user_id=OWNER_ID, role="owner"))
    db.add(ProjectMembership(project_id=project.id, user_id=EDITOR_ID, role="editor"))
    db.add(ProjectMembership(project_id=project.id, user_id=REVIEWER_ID, role="reviewer"))
    db.add(ProjectMembership(project_id=project.id, user_id=VIEWER_ID, role="viewer"))

    paper = Paper(
        project_id=project.id,
        title="Grounded Evidence",
        authors="Smith",
        journal="Journal",
        publication_year=2024,
        doi="10.1000/demo",
        pmid="12345",
        filename="grounded.pdf",
        language="en",
        source_provider="pubmed",
        source_type="search",
        is_open_access=True,
        oa_url="https://example.test/paper",
        favorite=False,
        is_processed=True,
        processing_status="parsed",
        processing_warnings=[],
    )
    db.add(paper)
    return project


def build_test_app(db: FakeSession) -> FastAPI:
    from app.api import deps

    app = FastAPI()
    app.add_middleware(CSRFMiddleware)
    app.include_router(projects_router)
    app.include_router(screening_router)

    async def get_db_override():
        yield db

    async def fake_user(request: Request, db=None):
        user_header = request.headers.get("X-Test-User", str(OWNER_ID))
        return SimpleNamespace(id=uuid.UUID(user_header), is_active=True)

    app.dependency_overrides[deps.get_db] = get_db_override
    app.dependency_overrides[deps.get_current_user] = fake_user
    return app


def auth_headers(user_id: uuid.UUID, *, csrf: bool = False) -> dict[str, str]:
    headers = {"X-Test-User": str(user_id)}
    if csrf:
        headers["X-CSRF-Token"] = "abc"
    return headers


@pytest.mark.asyncio
async def test_create_and_list_projects():
    from app.api import deps

    app = FastAPI()
    app.add_middleware(CSRFMiddleware)
    app.include_router(projects_router)

    db = FakeSession()

    async def get_db_override():
        yield db

    async def fake_user(request: Request, db=None):
        return SimpleNamespace(id=OWNER_ID, is_active=True)

    app.dependency_overrides[deps.get_db] = get_db_override
    app.dependency_overrides[deps.get_current_user] = fake_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.cookies.set("csrf_token", "abc")
        ac.cookies.set("access_token", "x")

        create_response = await ac.post(
            "/projects",
            json={"title": "Orto", "description": None, "clinical_area": None},
            headers={"X-CSRF-Token": "abc"},
        )
        assert create_response.status_code == 200

        list_response = await ac.get("/projects")
        assert list_response.status_code == 200
        items = list_response.json()
        assert len(items) == 1
        assert items[0]["title"] == "Orto"
        assert items[0]["role"] == "owner"


@pytest.mark.asyncio
async def test_owner_can_create_patch_and_delete_membership():
    db = FakeSession()
    project = seed_project(db)
    app = build_test_app(db)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.cookies.set("csrf_token", "abc")
        ac.cookies.set("access_token", "x")

        create_response = await ac.post(
            f"/projects/{project.id}/members",
            json={"user_id": "00000000-0000-0000-0000-000000000099", "role": "viewer"},
            headers=auth_headers(OWNER_ID, csrf=True),
        )
        assert create_response.status_code == 200
        created = create_response.json()
        assert created["role"] == "viewer"

        patch_response = await ac.patch(
            f"/projects/{project.id}/members/{created['id']}",
            json={"role": "editor"},
            headers=auth_headers(OWNER_ID, csrf=True),
        )
        assert patch_response.status_code == 200
        assert patch_response.json()["role"] == "editor"

        delete_response = await ac.delete(
            f"/projects/{project.id}/members/{created['id']}",
            headers=auth_headers(OWNER_ID, csrf=True),
        )
        assert delete_response.status_code == 200
        assert delete_response.json() == {"ok": True}
        assert all(str(item.id) != created["id"] for item in db.memberships)


@pytest.mark.asyncio
async def test_last_owner_cannot_be_removed():
    db = FakeSession()
    project = seed_project(db)
    app = build_test_app(db)
    owner_membership = next(item for item in db.memberships if item.project_id == project.id and item.user_id == OWNER_ID)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.cookies.set("csrf_token", "abc")
        ac.cookies.set("access_token", "x")

        response = await ac.delete(
            f"/projects/{project.id}/members/{owner_membership.id}",
            headers=auth_headers(OWNER_ID, csrf=True),
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Cannot remove the last owner"


@pytest.mark.asyncio
async def test_viewer_can_read_members_and_library_but_cannot_mutate():
    db = FakeSession()
    project = seed_project(db)
    app = build_test_app(db)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.cookies.set("csrf_token", "abc")
        ac.cookies.set("access_token", "x")

        members_response = await ac.get(f"/projects/{project.id}/members", headers=auth_headers(VIEWER_ID))
        assert members_response.status_code == 200
        assert len(members_response.json()) == 4

        library_response = await ac.get(f"/projects/{project.id}/library", headers=auth_headers(VIEWER_ID))
        assert library_response.status_code == 200
        body = library_response.json()
        assert body["total_count"] == 1
        assert len(body["items"]) == 1
        assert body["items"][0]["title"] == "Grounded Evidence"

        update_response = await ac.patch(
            f"/projects/{project.id}",
            json={"title": "Viewer should fail"},
            headers=auth_headers(VIEWER_ID, csrf=True),
        )
        assert update_response.status_code == 403

        create_member_response = await ac.post(
            f"/projects/{project.id}/members",
            json={"user_id": "00000000-0000-0000-0000-000000000101", "role": "viewer"},
            headers=auth_headers(VIEWER_ID, csrf=True),
        )
        assert create_member_response.status_code == 403


@pytest.mark.asyncio
async def test_editor_can_update_project_but_cannot_manage_members():
    db = FakeSession()
    project = seed_project(db)
    app = build_test_app(db)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.cookies.set("csrf_token", "abc")
        ac.cookies.set("access_token", "x")

        update_response = await ac.patch(
            f"/projects/{project.id}",
            json={"title": "Editor updated title"},
            headers=auth_headers(EDITOR_ID, csrf=True),
        )
        assert update_response.status_code == 200
        assert update_response.json()["title"] == "Editor updated title"

        create_member_response = await ac.post(
            f"/projects/{project.id}/members",
            json={"user_id": "00000000-0000-0000-0000-000000000102", "role": "viewer"},
            headers=auth_headers(EDITOR_ID, csrf=True),
        )
        assert create_member_response.status_code == 403


@pytest.mark.asyncio
async def test_reviewer_can_comment_but_cannot_edit_project_or_memberships():
    db = FakeSession()
    project = seed_project(db)
    app = build_test_app(db)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.cookies.set("csrf_token", "abc")
        ac.cookies.set("access_token", "x")

        comment_response = await ac.post(
            "/screening/comments",
            json={
                "project_id": str(project.id),
                "body": "Review note",
                "target_type": "draft",
                "target_id": str(project.id),
            },
            headers=auth_headers(REVIEWER_ID, csrf=True),
        )
        assert comment_response.status_code == 200
        assert comment_response.json()["body"] == "Review note"

        update_response = await ac.patch(
            f"/projects/{project.id}",
            json={"title": "Reviewer should fail"},
            headers=auth_headers(REVIEWER_ID, csrf=True),
        )
        assert update_response.status_code == 403

        create_member_response = await ac.post(
            f"/projects/{project.id}/members",
            json={"user_id": "00000000-0000-0000-0000-000000000103", "role": "viewer"},
            headers=auth_headers(REVIEWER_ID, csrf=True),
        )
        assert create_member_response.status_code == 403
