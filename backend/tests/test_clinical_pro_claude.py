from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from app.config import settings
from app.services.clinical.pro_pipeline import generate_clinical_pro_output


def _valid_pro_payload() -> dict:
    return {
        "title": "Manejo clínico de gonartrosis",
        "sections": [
            {
                "id": "summary",
                "title": "Resumen Ejecutivo",
                "content_markdown": "Conducta basada en evidencia.\n\nFuentes: PMID:123456",
            }
        ],
        "tables": [
            {
                "title": "Tratamiento por escenarios",
                "columns": ["Escenario", "Conducta", "Ref(s)"],
                "rows": [["Agudo", "Analgesia", "PMID:123456"]],
            }
        ],
        "charts": [
            {
                "title": "Figura conceptual",
                "type": "conceptual",
                "data": {"labels": ["A"], "values": [1]},
                "note": "Sin datos comparativos",
            }
        ],
        "mermaid": [{"title": "Algoritmo", "code": "flowchart TD\nA[Inicio]-->B[Evaluar]"}],
        "evidence_map": [
            {
                "question": "¿Analgesia inicial?",
                "conclusion": "Sí, individualizada.",
                "strength": "medium",
                "key_papers": ["PMID:123456"],
                "limitations": "Muestra pequeña",
            }
        ],
        "references_vancouver": ["1. Estudio PMID:123456."],
        "quality": {"evidence_strength": "medium", "gaps": []},
    }


@pytest.mark.asyncio
async def test_generate_clinical_pro_uses_claude_when_configured(monkeypatch):
    from app.services.llm import claude as claude_module
    from app.services.llm.openclaw import OpenClawProvider

    payload = _valid_pro_payload()
    responses = [
        json.dumps(payload, ensure_ascii=False),
        json.dumps({"issues": [], "summary": "ok"}, ensure_ascii=False),
        json.dumps(payload, ensure_ascii=False),
        json.dumps({"ok": True, "issues": [], "missing": []}, ensure_ascii=False),
    ]

    class FakeMessagesAPI:
        def __init__(self, queued: list[str]):
            self.queued = list(queued)
            self.calls: list[dict] = []

        async def create(self, **kwargs):
            self.calls.append(kwargs)
            content = self.queued.pop(0)
            return SimpleNamespace(
                model=kwargs["model"],
                content=[SimpleNamespace(text=content)],
                usage=SimpleNamespace(input_tokens=111, output_tokens=222),
            )

    class FakeAsyncAnthropic:
        last_instance = None

        def __init__(self, api_key: str):
            self.api_key = api_key
            self.messages = FakeMessagesAPI(responses)
            FakeAsyncAnthropic.last_instance = self

    monkeypatch.setattr(claude_module, "AsyncAnthropic", FakeAsyncAnthropic, raising=True)
    monkeypatch.setattr(settings, "CLINICAL_LLM_PROVIDER", "claude")
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "anthropic-test")
    monkeypatch.setattr(settings, "CLAUDE_MODEL", "claude-sonnet-4-6")

    async def fail_openclaw(self, **kwargs):
        raise AssertionError("OpenClaw no debe usarse cuando Claude está configurado")

    monkeypatch.setattr(OpenClawProvider, "chat", fail_openclaw, raising=True)

    out, usage, warnings = await generate_clinical_pro_output(
        topic="Gonartrosis",
        context=None,
        region=None,
        evidence_bundle={"project_papers": [], "pubmed_top25": [], "pubmed_core10": [], "oa_full_text": [], "local_books": []},
        objective="quick_review",
        focus="treatment",
        level="specialist",
        max_length="medium",
    )

    assert out.title == payload["title"]
    assert usage["provider"] == "claude"
    assert [p["name"] for p in usage["passes"]] == ["writer", "critic", "revise", "validate"]
    assert all(p["model"] == "claude-sonnet-4-6" for p in usage["passes"])
    assert warnings == []

    calls = FakeAsyncAnthropic.last_instance.messages.calls
    assert len(calls) == 4
    assert all(call["model"] == "claude-sonnet-4-6" for call in calls)


@pytest.mark.asyncio
async def test_generate_clinical_pro_falls_back_to_openai_when_anthropic_key_missing(monkeypatch):
    from app.services.llm.claude import ClaudeProvider
    from app.services.llm.openclaw import OpenClawProvider

    payload = _valid_pro_payload()
    responses = iter(
        [
            json.dumps(payload, ensure_ascii=False),
            json.dumps({"issues": [], "summary": "ok"}, ensure_ascii=False),
            json.dumps(payload, ensure_ascii=False),
            json.dumps({"ok": True, "issues": [], "missing": []}, ensure_ascii=False),
        ]
    )
    models_seen: list[str] = []

    monkeypatch.setattr(settings, "CLINICAL_LLM_PROVIDER", "claude")
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", None)
    monkeypatch.setattr(settings, "OPENCLAW_OPENAI_MODEL", "default")

    async def fake_openclaw_chat(self, *, model, system, user, temperature=0.0, max_tokens=0, timeout=None, retry=0):
        models_seen.append(model)
        return {
            "content": next(responses),
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
            "latency_ms": 1,
            "model": model,
        }

    async def fail_claude(self, **kwargs):
        raise AssertionError("Claude no debe llamarse sin ANTHROPIC_API_KEY")

    monkeypatch.setattr(OpenClawProvider, "chat", fake_openclaw_chat, raising=True)
    monkeypatch.setattr(ClaudeProvider, "chat", fail_claude, raising=True)

    out, usage, warnings = await generate_clinical_pro_output(
        topic="Gonartrosis",
        context=None,
        region=None,
        evidence_bundle={"project_papers": [], "pubmed_top25": [], "pubmed_core10": [], "oa_full_text": [], "local_books": []},
        objective="quick_review",
        focus="treatment",
        level="specialist",
        max_length="medium",
    )

    assert out.title == payload["title"]
    assert usage["provider"] == "openai"
    assert models_seen == ["gpt-4o", "gpt-4o", "gpt-4o", "gpt-4o"]
    assert any("fallback OpenAI" in warning for warning in warnings)
