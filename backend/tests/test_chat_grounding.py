from __future__ import annotations

from app.services.chat_service import _compose_grounded_answer


def test_chat_blocks_when_grounding_is_insufficient():
    answer, confidence, blocked_reason = _compose_grounded_answer(
        "what is the result",
        [{"quoted_text": "Tiny snippet.", "final_score": 0.12}],
        max_citations=3,
    )
    assert blocked_reason == "low_grounding"
    assert confidence < 0.2
    assert "Tiny snippet" in answer


def test_chat_returns_extractive_answer_for_grounded_hits():
    answer, confidence, blocked_reason = _compose_grounded_answer(
        "what is the intervention",
        [
            {"quoted_text": "The intervention group received supervised exercise therapy. Outcomes improved after 12 weeks.", "final_score": 0.6},
            {"quoted_text": "Participants in the comparator arm received usual care only. Pain scores remained higher.", "final_score": 0.55},
        ],
        max_citations=2,
    )
    assert blocked_reason is None
    assert confidence > 0.0
    assert "supervised exercise therapy" in answer.lower()
