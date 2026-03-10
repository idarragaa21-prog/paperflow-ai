from __future__ import annotations

import pytest

from app.schemas.search import SearchFilters
from app.services.federated_search import federated_search
from app.services.pubmed import pubmed_client


def test_pubmed_query_adds_publication_year_clause():
    filters = SearchFilters(year_from=2021, year_to=2026)
    query = pubmed_client._apply_filters_to_query("acl reconstruction graft choice", filters)
    assert '"2021"[Date - Publication]' in query
    assert '"2026"[Date - Publication]' in query
    assert "acl reconstruction graft choice" in query


@pytest.mark.asyncio
async def test_federated_search_filters_by_year_and_enriches_results(monkeypatch):
    filters = SearchFilters(year_from=2024, year_to=2026)

    async def fake_pubmed(query: str, max_results: int = 20, filters=None):
        assert filters.year_from == 2024
        return {
            "results": [
                {
                    "pmid": "100",
                    "doi": "10.1000/recent",
                    "title": "Recent repair trial",
                    "authors": ["A"],
                    "journal": "Journal",
                    "pub_year": 2025,
                    "abstract": "Useful abstract",
                    "is_open_access": True,
                    "oa_url": "https://example.org/recent.pdf",
                    "source": "pubmed",
                },
                {
                    "pmid": "101",
                    "doi": "10.1000/old",
                    "title": "Old paper",
                    "authors": ["B"],
                    "journal": "Journal",
                    "pub_year": 2018,
                    "abstract": "Old abstract",
                    "is_open_access": False,
                    "oa_url": None,
                    "source": "pubmed",
                },
            ],
            "query_translation": "translated",
        }

    async def fake_europe(query: str, max_results: int, filters=None):
        assert filters.year_from == 2024
        return [
            {
                "pmid": "202",
                "title": "No abstract but source",
                "authors": ["C"],
                "journal": "Journal",
                "pub_year": 2024,
                "abstract": None,
                "source": "europepmc",
                "is_open_access": False,
                "oa_url": None,
                "open_targets": [{"kind": "pubmed", "url": "https://pubmed.ncbi.nlm.nih.gov/202/", "label": "Abrir PubMed"}],
                "has_abstract": False,
                "can_save_pdf": False,
                "can_open_external": True,
                "content_state": "abstract_available",
            }
        ]

    async def fake_doaj(query: str, max_results: int):
        return [
            {
                "title": "Missing year record",
                "authors": ["D"],
                "journal": "Journal",
                "pub_year": None,
                "abstract": "No year means it should be filtered out",
                "source": "doaj",
                "is_open_access": True,
                "oa_url": "https://example.org/doaj.pdf",
            }
        ]

    monkeypatch.setattr("app.services.federated_search.pubmed_client.search_and_fetch", fake_pubmed)
    monkeypatch.setattr("app.services.federated_search._search_europe_pmc", fake_europe)
    monkeypatch.setattr("app.services.federated_search._search_doaj", fake_doaj)

    payload = await federated_search("rotator cuff augmentation", max_results=10, filters=filters)

    assert payload["count"] == 2
    assert payload["provider_status"]["doaj"] == "filtered_server_side"
    assert any("DOAJ se filtro por ano" in item for item in payload["warnings"])

    titles = {item["title"] for item in payload["results"]}
    assert "Recent repair trial" in titles
    assert "No abstract but source" in titles
    assert "Old paper" not in titles
    assert "Missing year record" not in titles

    recent = next(item for item in payload["results"] if item["title"] == "Recent repair trial")
    assert recent["content_state"] == "pdf_available"
    assert recent["has_abstract"] is True
    assert recent["can_save_pdf"] is True
    assert any(target["kind"] == "oa_pdf" for target in recent["open_targets"])
