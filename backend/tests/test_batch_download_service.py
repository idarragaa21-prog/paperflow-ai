from __future__ import annotations

import uuid

import httpx
import pytest

from app.services.batch_download import batch_download_papers


class FakePaper:
    def __init__(self, pmid=None, doi=None, content_hash=None):
        self.id = uuid.uuid4()
        self.pmid = pmid
        self.doi = doi
        self.content_hash = content_hash
        self.filename = "x.pdf"
        self.file_size_kb = 1


class FakeRepo:
    def __init__(self):
        self.by_pmid = {}
        self.by_doi = {}
        self.by_hash = {}
        self.created = []

    async def find_duplicate_by_identifiers(self, *, project_id, pmid, doi):
        if pmid and pmid in self.by_pmid:
            return self.by_pmid[pmid]
        if doi and doi in self.by_doi:
            return self.by_doi[doi]
        return None

    async def find_duplicate_by_hash(self, *, project_id, content_hash):
        return self.by_hash.get(content_hash)

    async def create_paper(self, paper):
        # mimic persistence
        if getattr(paper, "id", None) is None:
            paper.id = uuid.uuid4()
        self.created.append(paper)
        return paper


class FakeResolver:
    def __init__(self, url: str, source: str, fail: bool = False):
        self.url = url
        self.source = source
        self.fail = fail

    async def resolve_by_pmid(self, pmid, client):
        if self.fail:
            raise RuntimeError("not oa")
        return type("R", (), {"url_for_pdf": self.url, "source": self.source})

    async def resolve(self, doi, client):
        if self.fail:
            raise RuntimeError("not oa")
        return type("R", (), {"url_for_pdf": self.url, "source": self.source})


class FakeDownloader:
    def __init__(self, *, ok_url: str):
        self.europepmc = FakeResolver(ok_url, "europepmc")
        self.unpaywall = FakeResolver(ok_url, "unpaywall")


def _pdf_bytes() -> bytes:
    return b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"


@pytest.mark.asyncio
async def test_batch_download_dedup(monkeypatch):
    from app.services import batch_download as mod

    # avoid filesystem writes
    async def fake_save(*, data, project_id, suggested_filename=None):
        return {"filename": "x.pdf", "file_path": "papers/x.pdf", "size_kb": 1, "content_hash": "h"}

    monkeypatch.setattr(mod.storage_manager, "save_paper_bytes", fake_save)
    monkeypatch.setattr(mod.storage_manager, "validate_pdf", lambda b: True)

    repo = FakeRepo()
    existing = FakePaper(pmid="123")
    repo.by_pmid["123"] = existing

    downloader = FakeDownloader(ok_url="https://example.com/x.pdf")

    async def handler(request):
        return httpx.Response(200, content=_pdf_bytes())

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        res = await batch_download_papers(
            repo=repo,
            downloader=downloader,
            client=client,
            user=None,
            project_id=uuid.uuid4(),
            papers=[{"pmid": "123", "title": "T"}],
        )

    assert len(res.downloaded) == 0
    assert len(res.already_exists) == 1


@pytest.mark.asyncio
async def test_batch_download_not_oa(monkeypatch):
    from app.services import batch_download as mod

    async def fake_save(*, data, project_id, suggested_filename=None):
        return {"filename": "x.pdf", "file_path": "papers/x.pdf", "size_kb": 1, "content_hash": "h"}

    monkeypatch.setattr(mod.storage_manager, "save_paper_bytes", fake_save)
    monkeypatch.setattr(mod.storage_manager, "validate_pdf", lambda b: True)

    repo = FakeRepo()
    downloader = FakeDownloader(ok_url="https://example.com/x.pdf")

    async def handler(request):
        return httpx.Response(200, content=_pdf_bytes())

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        res = await batch_download_papers(
            repo=repo,
            downloader=downloader,
            client=client,
            user=None,
            project_id=uuid.uuid4(),
            papers=[{"title": "No IDs"}],
        )

    assert len(res.not_available) == 1


@pytest.mark.asyncio
async def test_batch_download_job_result_structure(monkeypatch):
    from app.services import batch_download as mod

    async def fake_save(*, data, project_id, suggested_filename=None):
        return {"filename": "x.pdf", "file_path": "papers/x.pdf", "size_kb": 1, "content_hash": "h"}

    monkeypatch.setattr(mod.storage_manager, "save_paper_bytes", fake_save)
    monkeypatch.setattr(mod.storage_manager, "validate_pdf", lambda b: True)

    repo = FakeRepo()
    downloader = FakeDownloader(ok_url="https://example.com/x.pdf")

    async def handler(request):
        return httpx.Response(200, content=_pdf_bytes())

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        res = await batch_download_papers(
            repo=repo,
            downloader=downloader,
            client=client,
            user=None,
            project_id=uuid.uuid4(),
            papers=[{"pmid": "999", "title": "T"}],
        )

    assert hasattr(res, "downloaded")
    assert hasattr(res, "already_exists")
    assert hasattr(res, "not_available")
    assert hasattr(res, "failed")
