from __future__ import annotations

from types import MethodType

import pytest

from app.services.pubmed import PubMedClient


def test_collect_efetch_enrichment_returns_warning_for_invalid_xml():
    client = PubMedClient.__new__(PubMedClient)

    abstracts, pub_types, warnings = client._collect_efetch_enrichment("<PubmedArticleSet>")

    assert abstracts == {}
    assert pub_types == {}
    assert warnings == ["PubMed abstract enrichment unavailable; continuing with metadata-only results."]


@pytest.mark.asyncio
async def test_search_and_fetch_warns_when_efetch_enrichment_fails():
    client = PubMedClient.__new__(PubMedClient)

    async def fake_esearch(self, query: str, retmax: int = 20):
        del query, retmax
        return {"esearchresult": {"idlist": ["123"], "querytranslation": "acl graft"}}

    async def fake_esummary(self, pmids: list[str]):
        assert pmids == ["123"]
        return {
            "result": {
                "123": {
                    "title": "ACL graft review",
                    "fulljournalname": "Sports Med",
                    "pubdate": "2025 Jan",
                    "authors": [{"name": "Smith J"}],
                    "articleids": [{"idtype": "doi", "value": "10.1000/acl"}],
                }
            }
        }

    async def fake_efetch_xml(self, pmids: list[str]):
        del pmids
        raise RuntimeError("boom")

    client.esearch = MethodType(fake_esearch, client)
    client.esummary = MethodType(fake_esummary, client)
    client.efetch_xml = MethodType(fake_efetch_xml, client)

    payload = await client.search_and_fetch("acl graft", max_results=5)

    assert payload["query_translation"] == "acl graft"
    assert payload["warnings"] == ["PubMed abstract enrichment unavailable; continuing with metadata-only results."]
    assert payload["results"][0]["title"] == "ACL graft review"
    assert payload["results"][0]["abstract"] is None
