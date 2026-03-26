from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token
from app.core.storage import storage_manager
from app.main import app
from app.models.paper import Paper


def _valid_pdf_bytes() -> bytes:
    # Minimal bytes that satisfy magic + %%EOF check.
    return b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


class FakeProject:
    def __init__(self, project_id: str, user_id: str):
        self.id = uuid.UUID(project_id)
        self.user_id = uuid.UUID(user_id)


class FakeDB:
    def __init__(self):
        self.added = []

    def add(self, obj):
        if getattr(obj, "id", None) is None:
            try:
                obj.id = uuid.uuid4()
            except Exception:
                pass
        self.added.append(obj)
        return None

    async def commit(self):
        return None

    async def execute(self, stmt):
        del stmt

        class _Result:
            def __init__(self, items):
                self._items = items

            def scalars(self):
                return self

            def first(self):
                return self._items[-1] if self._items else None

        audit_entries = [obj for obj in self.added if obj.__class__.__name__ == "AuditLog"]
        return _Result(audit_entries)


class FakeRepo:
    def __init__(self, user_id: str, project_id: str):
        self._user_id = uuid.UUID(user_id)
        self._project_id = uuid.UUID(project_id)
        self._papers: dict[uuid.UUID, Paper] = {}
        self.db = FakeDB()  # for audit helper

    def seed_paper(self, paper: Paper) -> None:
        if paper.id is None:
            paper.id = uuid.uuid4()
        self._papers[paper.id] = paper

    async def get_project(self, project_id):
        if uuid.UUID(str(project_id)) != self._project_id:
            return None
        return FakeProject(str(self._project_id), str(self._user_id))

    async def get_paper(self, paper_id):
        return self._papers.get(uuid.UUID(str(paper_id)))

    async def find_duplicate_by_identifiers(self, *, project_id, pmid, doi):
        for p in self._papers.values():
            if p.project_id != uuid.UUID(str(project_id)):
                continue
            if pmid and p.pmid == pmid:
                return p
            if doi and p.doi == doi:
                return p
        return None

    async def find_duplicate_by_hash(self, *, project_id, content_hash):
        for p in self._papers.values():
            if p.project_id == uuid.UUID(str(project_id)) and p.content_hash == content_hash:
                return p
        return None

    async def create_paper(self, paper: Paper) -> Paper:
        if paper.id is None:
            paper.id = uuid.uuid4()
        self._papers[paper.id] = paper
        return paper

    async def delete_paper(self, paper: Paper) -> None:
        self._papers.pop(paper.id, None)


class FakeDownloader:
    async def download_open_access_pdf(self, *, doi, pmid, oa_url=None, pmcid=None, client):
        del doi, pmid, oa_url, pmcid, client
        raise AssertionError("downloader should not be called")


class SuccessfulDownloader:
    async def download_open_access_pdf(self, *, doi, pmid, oa_url=None, pmcid=None, client):
        del pmid, oa_url, pmcid, client
        return type(
            "DownloadResult",
            (),
            {
                "pdf_bytes": _valid_pdf_bytes(),
                "source": "unpaywall",
                "resolved_url": "https://cdn.example.org/paper.pdf",
                "oa_url": "https://oa.example.org/paper.pdf",
                "landing_url": f"https://doi.org/{doi or '10.1000/test'}",
                "used_fallback": True,
            },
        )()


@pytest.mark.asyncio
async def test_validate_pdf_ok():
    assert storage_manager.validate_pdf(_valid_pdf_bytes()) is True


@pytest.mark.asyncio
async def test_validate_pdf_fail():
    assert storage_manager.validate_pdf(b"<html>nope</html>") is False
    assert storage_manager.validate_pdf(b"%PDF-1.4\n...missing eof") is False


@pytest.mark.asyncio
async def test_dedup_by_hash(monkeypatch):
    # Upload the same content twice -> second should be duplicate.
    from app.api import deps
    from app.api.papers import get_repo

    user_id = "00000000-0000-0000-0000-000000000000"
    project_id = "11111111-1111-1111-1111-111111111111"

    repo = FakeRepo(user_id, project_id)

    async def repo_override():
        return repo

    async def fake_get_db():
        yield None

    app.dependency_overrides[get_repo] = repo_override

    # Bypass DB dep used by get_current_user
    app.dependency_overrides[deps.get_db] = fake_get_db

    # Monkeypatch get_current_user to return a fake user
    class U:
        id = uuid.UUID(user_id)
        is_active = True

    async def fake_user(request=None, db=None):
        return U()

    app.dependency_overrides[deps.get_current_user] = fake_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.cookies.set("csrf_token", "abc")
        ac.cookies.set("access_token", create_access_token(user_id))

        files = {"file": ("a.pdf", _valid_pdf_bytes(), "application/pdf")}
        data = {"project_id": project_id}

        r1 = await ac.post("/papers/upload", data=data, files=files, headers={"X-CSRF-Token": "abc"})
        assert r1.status_code == 200
        assert r1.json()["duplicate"] is False

        r2 = await ac.post("/papers/upload", data=data, files=files, headers={"X-CSRF-Token": "abc"})
        assert r2.status_code == 200
        assert r2.json()["duplicate"] is True

    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_download_returns_duplicate_when_exists(monkeypatch):
    from app.api import deps
    from app.api.papers import get_downloader, get_repo

    user_id = "00000000-0000-0000-0000-000000000000"
    project_id = "11111111-1111-1111-1111-111111111111"

    repo = FakeRepo(user_id, project_id)
    existing = Paper(
        project_id=uuid.UUID(project_id),
        title="Existing",
        authors=None,
        doi="10.1000/test",
        pmid=None,
        pmcid=None,
        filename="x.pdf",
        file_path="papers/x.pdf",
        file_size_kb=1,
        content_hash="abc",
    )
    repo.seed_paper(existing)

    async def repo_override():
        return repo

    async def downloader_override():
        return FakeDownloader()

    async def fake_get_db():
        yield None

    app.dependency_overrides[get_repo] = repo_override
    app.dependency_overrides[get_downloader] = downloader_override
    app.dependency_overrides[deps.get_db] = fake_get_db

    class U:
        id = uuid.UUID(user_id)
        is_active = True

    async def fake_user(request=None, db=None):
        return U()

    app.dependency_overrides[deps.get_current_user] = fake_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.cookies.set("csrf_token", "abc")
        ac.cookies.set("access_token", create_access_token(user_id))

        resp = await ac.post(
            "/papers/download",
            json={"project_id": project_id, "doi": "10.1000/test", "title": "X"},
            headers={"X-CSRF-Token": "abc"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["duplicate"] is True
        assert body["id"] == str(existing.id)

    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_download_persists_trace_in_response(monkeypatch):
    from app.api import deps
    from app.api.papers import get_downloader, get_repo

    user_id = "00000000-0000-0000-0000-000000000000"
    project_id = "11111111-1111-1111-1111-111111111111"

    repo = FakeRepo(user_id, project_id)

    async def repo_override():
        return repo

    async def downloader_override():
        return SuccessfulDownloader()

    async def fake_get_db():
        yield None

    app.dependency_overrides[get_repo] = repo_override
    app.dependency_overrides[get_downloader] = downloader_override
    app.dependency_overrides[deps.get_db] = fake_get_db

    class U:
        id = uuid.UUID(user_id)
        is_active = True

    async def fake_user(request=None, db=None):
        del request, db
        return U()

    app.dependency_overrides[deps.get_current_user] = fake_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.cookies.set("csrf_token", "abc")
        ac.cookies.set("access_token", create_access_token(user_id))

        resp = await ac.post(
            "/papers/download",
            json={"project_id": project_id, "doi": "10.1000/test", "title": "Traceable paper"},
            headers={"X-CSRF-Token": "abc"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["download_trace"]["source_provider"] == "unpaywall"
        assert body["download_trace"]["resolved_url"] == "https://cdn.example.org/paper.pdf"
        assert body["download_trace"]["landing_url"] == "https://doi.org/10.1000/test"
        assert body["download_trace"]["used_fallback"] is True
        assert body["download_trace"]["final_status"] == "downloaded"

        detail = await ac.get(f"/papers/{body['id']}")
        assert detail.status_code == 200
        assert detail.json()["download_trace"]["resolved_url"] == "https://cdn.example.org/paper.pdf"

    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_upload_duplicate_by_hash(monkeypatch):
    from app.api import deps
    from app.api.papers import get_repo

    user_id = "00000000-0000-0000-0000-000000000000"
    project_id = "11111111-1111-1111-1111-111111111111"

    repo = FakeRepo(user_id, project_id)

    # Seed existing with same hash
    h = storage_manager._calculate_hash(_valid_pdf_bytes())
    existing = Paper(
        project_id=uuid.UUID(project_id),
        title="Existing",
        authors=None,
        doi=None,
        pmid=None,
        pmcid=None,
        filename="x.pdf",
        file_path="papers/x.pdf",
        file_size_kb=1,
        content_hash=h,
    )
    repo.seed_paper(existing)

    async def repo_override():
        return repo

    async def fake_get_db():
        yield None

    app.dependency_overrides[get_repo] = repo_override
    app.dependency_overrides[deps.get_db] = fake_get_db

    class U:
        id = uuid.UUID(user_id)
        is_active = True

    async def fake_user(request=None, db=None):
        return U()

    app.dependency_overrides[deps.get_current_user] = fake_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.cookies.set("csrf_token", "abc")
        ac.cookies.set("access_token", create_access_token(user_id))

        files = {"file": ("a.pdf", _valid_pdf_bytes(), "application/pdf")}
        data = {"project_id": project_id}

        resp = await ac.post("/papers/upload", data=data, files=files, headers={"X-CSRF-Token": "abc"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["duplicate"] is True
        assert body["id"] == str(existing.id)

    app.dependency_overrides = {}
