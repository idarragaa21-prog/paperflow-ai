from __future__ import annotations

import types

import pytest

from app.services.chat_service import _generate_grounded_answer


@pytest.mark.asyncio
async def test_chat_blocks_when_grounding_is_insufficient():
    answer, confidence, claim_type, blocked_reason, grounding_score, dependency_error_code = await _generate_grounded_answer(
        question="what is the result",
        retrieved=[{"quoted_text": "Tiny snippet.", "final_score": 0.12}],
        route=types.SimpleNamespace(model="qwen2.5:7b", provider="ollama"),
        max_citations=3,
    )
    assert blocked_reason == "insufficient_grounding"
    assert confidence == 0.0
    assert grounding_score == 0.0
    assert claim_type == "dato"
    assert dependency_error_code is None
    assert "No hay soporte documental suficiente" in answer


@pytest.mark.asyncio
async def test_chat_calls_model_for_grounded_hits(monkeypatch):
    class FakeAdapter:
        async def complete(self, **kwargs):
            return types.SimpleNamespace(
                text='{"answer":"The intervention was supervised exercise therapy.","claim_type":"dato","confidence":0.82,"blocked_reason":null}'
            )

    monkeypatch.setattr("app.services.chat_service._adapter_for_route", lambda route: FakeAdapter())

    answer, confidence, claim_type, blocked_reason, grounding_score, dependency_error_code = await _generate_grounded_answer(
        question="what was the intervention",
        retrieved=[
            {
                "paper_id": "paper-1",
                "paper_chunk_id": "chunk-1",
                "page_number": 3,
                "locator": {"page": 3, "char_start": 10, "char_end": 64},
                "quoted_text": "The intervention group received supervised exercise therapy.",
                "final_score": 0.8,
            },
            {
                "paper_id": "paper-1",
                "paper_chunk_id": "chunk-2",
                "page_number": 4,
                "locator": {"page": 4, "char_start": 0, "char_end": 31},
                "quoted_text": "Comparator received usual care.",
                "final_score": 0.62,
            },
        ],
        route=types.SimpleNamespace(model="qwen2.5:7b", provider="ollama"),
        max_citations=2,
    )
    assert blocked_reason is None
    assert claim_type == "dato"
    assert grounding_score > 0.0
    assert confidence > 0.0
    assert dependency_error_code is None
    assert "supervised exercise therapy" in answer.lower()


@pytest.mark.asyncio
async def test_chat_surfaces_dependency_failure(monkeypatch):
    class FailingAdapter:
        async def complete(self, **kwargs):
            raise RuntimeError("ollama down")

    monkeypatch.setattr("app.services.chat_service._adapter_for_route", lambda route: FailingAdapter())

    answer, confidence, claim_type, blocked_reason, grounding_score, dependency_error_code = await _generate_grounded_answer(
        question="what was the intervention",
        retrieved=[
            {
                "paper_id": "paper-1",
                "paper_chunk_id": "chunk-1",
                "page_number": 3,
                "locator": {"page": 3, "char_start": 10, "char_end": 64},
                "quoted_text": "The intervention group received supervised exercise therapy.",
                "final_score": 0.8,
            },
            {
                "paper_id": "paper-1",
                "paper_chunk_id": "chunk-2",
                "page_number": 4,
                "locator": {"page": 4, "char_start": 0, "char_end": 31},
                "quoted_text": "Comparator received usual care.",
                "final_score": 0.62,
            },
        ],
        route=types.SimpleNamespace(model="qwen2.5:7b", provider="ollama"),
        max_citations=2,
    )
    assert blocked_reason is None
    assert dependency_error_code == "generation_unavailable"
    assert claim_type == "dato"
    assert confidence == 0.0
    assert grounding_score == 0.0
    assert "dependencia del lector" in answer.lower()
