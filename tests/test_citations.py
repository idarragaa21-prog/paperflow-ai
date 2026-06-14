from fastapi.testclient import TestClient

from metaforge.api import app
from metaforge.citations import parse_references, to_bibtex, to_ris
from metaforge.zotero import _creators, _item

client = TestClient(app)

RECS = [{"title": "Metformin and CRC", "authors": "Smith J, Doe A", "journal": "BMJ",
         "year": "2021", "doi": "10.1/x", "pmid": "123", "abstract": "Cohort.",
         "doi_url": "https://doi.org/10.1/x"}]


def test_to_ris_structure():
    ris = to_ris(RECS)
    assert "TY  - JOUR" in ris and "TI  - Metformin and CRC" in ris
    assert "AU  - Smith J" in ris and "AU  - Doe A" in ris
    assert "DO  - 10.1/x" in ris and ris.rstrip().endswith("ER  -")


def test_to_bibtex_structure():
    bib = to_bibtex(RECS)
    assert bib.startswith("@article{Smith2021")
    assert "author = {Smith J and Doe A}" in bib


def test_ris_roundtrip():
    back = parse_references(to_ris(RECS))
    assert len(back) == 1
    assert back[0]["title"] == "Metformin and CRC"
    assert back[0]["doi"] == "10.1/x"
    assert "Smith J" in back[0]["authors"]


def test_bibtex_roundtrip_autodetect():
    back = parse_references(to_bibtex(RECS))
    assert len(back) == 1 and back[0]["year"] == "2021"


def test_zotero_creators_and_item():
    cr = _creators("Smith J, García M")
    assert cr[0] == {"creatorType": "author", "lastName": "Smith", "firstName": "J"}
    item = _item(RECS[0], "K1")
    assert item["itemType"] == "journalArticle"
    assert item["DOI"] == "10.1/x"
    assert "PMID: 123" in item["extra"]
    assert item["collections"] == ["K1"]


def test_api_citations_export_and_import():
    r = client.post("/citations/export", json={"records": RECS, "format": "ris"})
    assert r.status_code == 200 and "research-info-systems" in r.headers["content-type"]
    b = client.post("/citations/export", json={"records": RECS, "format": "bibtex"})
    assert b.status_code == 200 and "bibtex" in b.headers["content-type"]
    imp = client.post("/citations/import", json={"text": r.text})
    assert imp.status_code == 200 and imp.json()["count"] == 1


def test_api_zotero_push_missing_creds():
    r = client.post("/zotero/push", json={"records": RECS, "api_key": "", "user_id": ""})
    assert r.status_code == 400


def test_zotero_item_omits_collections_without_key():
    assert "collections" not in _item(RECS[0])


def test_api_zotero_local_status_and_push():
    # No Zotero desktop in the test environment -> not available, push fails cleanly.
    st = client.get("/zotero/local-status")
    assert st.status_code == 200 and st.json()["available"] is False
    r = client.post("/zotero/local-push", json={"records": RECS})
    assert r.status_code == 400
