from fastapi.testclient import TestClient

from metaforge.api import app
from metaforge.screen import screen_records
from metaforge.search import _parse_epmc, europepmc_query

client = TestClient(app)


def test_europepmc_query_strips_field_tags():
    q = europepmc_query('("Metformin"[Mesh] OR metformin[tiab]) AND colorectal[tiab]')
    assert "[Mesh]" not in q and "[tiab]" not in q
    assert "Metformin" in q and "colorectal" in q


def test_parse_record():
    rec = {
        "id": "123", "source": "MED", "pmid": "123", "doi": "10.1/x",
        "title": "A cohort study.", "abstractText": "We followed…",
        "authorString": "Smith J, Doe A", "pubYear": "2020",
        "journalInfo": {"journal": {"title": "BMJ"}},
        "isOpenAccess": "Y", "pubTypeList": {"pubType": ["Journal Article"]},
        "fullTextUrlList": {"fullTextUrl": [{"url": "http://x/p.pdf", "documentStyle": "pdf", "availability": "Open access"}]},
    }
    p = _parse_epmc(rec)
    assert p["title"] == "A cohort study"      # trailing dot stripped
    assert p["is_oa"] is True
    assert p["pdf_url"] == "http://x/p.pdf"
    assert p["doi_url"] == "https://doi.org/10.1/x"


def test_screen_local_fallback():
    recs = [{"id": "1", "title": "T", "abstract": "A"}]
    out = screen_records(recs, ["adultos"], ["animales"], mode="local")
    assert out["source"] == "local"
    assert out["decisions"][0]["decision"] == "maybe"


def test_api_search_empty_query():
    assert client.post("/search", json={"query": ""}).status_code == 400


def test_api_screen_local():
    r = client.post("/screen", json={"records": [{"id": "1", "title": "x", "abstract": "y"}],
                                     "inclusion": ["a"], "exclusion": ["b"], "mode": "local"})
    assert r.status_code == 200
    assert r.json()["decisions"][0]["decision"] == "maybe"


def test_live_search_tolerant():
    """Hits Europe PMC if the network allows; tolerates being offline."""
    r = client.post("/search", json={"query": "metformin colorectal cancer cohort", "page_size": 3})
    if r.status_code == 200:
        body = r.json()
        assert "records" in body and body["returned"] <= 3
    else:
        assert r.status_code == 400  # network blocked -> handled error
