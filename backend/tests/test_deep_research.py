from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_search_papers_pubmed_uses_search_and_fetch(monkeypatch):
    from app.services import deep_research
    import app.services.pubmed as pubmed_module

    class FakePubMedClient:
        async def search_and_fetch(self, *, query: str, max_results: int = 20):
            assert query == "hombro flotante"
            assert max_results == 5
            return {
                "results": [
                    {
                        "pmid": "33417757",
                        "doi": None,
                        "title": "Functional results of floating shoulder treatment",
                        "authors": ["Garcia J", "Perez L"],
                        "journal": "Acta Ortop Mex",
                        "pub_year": 2020,
                        "abstract": "Clinical outcomes were favorable.",
                        "is_open_access": True,
                        "oa_url": "https://example.org/paper.pdf",
                    }
                ]
            }

    monkeypatch.setattr(pubmed_module, "PubMedClient", FakePubMedClient, raising=True)

    papers = await deep_research.search_papers_pubmed("hombro flotante", max_results=5)

    assert len(papers) == 1
    assert papers[0]["pmid"] == "33417757"
    assert papers[0]["authors"] == "Garcia J, Perez L"
    assert papers[0]["year"] == "2020"
    assert papers[0]["has_full_text"] is True
    assert papers[0]["oa_url"] == "https://example.org/paper.pdf"


@pytest.mark.asyncio
async def test_generate_deep_research_report_returns_papers_for_pubmed(monkeypatch):
    from app.services import deep_research

    async def fake_search(query: str, max_results: int = 20):
        return [
            {
                "pmid": "33417757",
                "doi": None,
                "title": "Floating shoulder treatment",
                "authors": "Garcia J, Perez L",
                "journal": "Acta Ortop Mex",
                "year": "2020",
                "abstract": "Clinical outcomes were favorable.",
                "source": "pubmed",
            }
        ]

    async def fake_generate(section_prompt: str, papers_context: str, query: str):
        return f"Section for {query}"

    monkeypatch.setattr(deep_research, "search_papers_pubmed", fake_search, raising=True)
    monkeypatch.setattr(deep_research, "_generate_section", fake_generate, raising=True)

    report = await deep_research.generate_deep_research_report("hombro flotante", max_papers=5)

    assert report["status"] == "completed"
    assert report["papers_analyzed"] == 1
    assert report["papers"][0]["title"] == "Floating shoulder treatment"
    assert len(report["sections"]) == len(deep_research.REPORT_SECTIONS)


@pytest.mark.asyncio
async def test_generate_section_falls_back_to_ollama_when_primary_chat_fails(monkeypatch):
    from app.services import deep_research
    import app.services.llm.factory as llm_factory
    import app.services.llm.provider_adapters as provider_adapters

    class BrokenProvider:
        async def chat(self, **kwargs):
            raise RuntimeError("HTTP 404 Not Found")

    class FakeOllamaAdapter:
        def __init__(self, model_name: str, base_url: str | None = None):
            self.model_name = model_name
            self.base_url = base_url

        async def complete(self, prompt: str, system: str = "", temperature: float = 0.3, max_tokens: int = 4096, json_mode: bool = False):
            class Response:
                text = "Recovered section from Ollama"

            assert "floating shoulder" in prompt.lower()
            return Response()

    monkeypatch.setattr(llm_factory, "llm_provider", lambda: BrokenProvider(), raising=True)
    monkeypatch.setattr(provider_adapters, "OllamaAdapter", FakeOllamaAdapter, raising=True)

    content = await deep_research._generate_section(
        "Explain findings for '{query}'",
        "paper context",
        "floating shoulder",
    )

    assert content == "Recovered section from Ollama"
