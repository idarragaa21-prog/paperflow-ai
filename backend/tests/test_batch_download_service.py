from __future__ import annotations

import uuid

import httpx
import pytest

from app.services.batch_download import batch_download_papers
from app.services.paper_service import PaperServiceError


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


class FakeDownloader:
    def __init__(self, *, ok_url: str):
        self.ok_url = ok_url

    async def download_open_access_pdf(self, *, doi=None, pmid=None, pmcid=None, oa_url=None, client=None):
        if not oa_url and not doi and not pmid:
            raise PaperServiceError("not oa")
        del pmcid, client
        return type(
            "DownloadResult",
            (),
            {
                "pdf_bytes": _pdf_bytes(),
                "source": "europepmc",
                "resolved_url": oa_url or self.ok_url,
                "oa_url": oa_url or self.ok_url,
                "landing_url": "https://example.com/landing",
                "used_fallback": False,
            },
        )()


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
    assert res.already_exists[0]["final_status"] == "existing"


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
    assert res.not_available[0]["final_status"] == "unavailable"


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
    assert hasattr(res, "items")
