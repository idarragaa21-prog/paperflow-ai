from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from app.services.extraction_service import _candidate_spans, _extract_value


def _paper_stub():
    return SimpleNamespace(title="ACL review", authors="Smith", publication_year=2025)


def test_extract_country_prefers_explicit_study_context():
    text = "This multicenter trial was conducted in the United States among competitive athletes."

    country = _extract_value("country", _paper_stub(), text)

    assert country == "United States"


def test_extract_population_reads_structured_sentence():
    text = "Participants included 240 adults with chronic rotator cuff tears undergoing arthroscopic repair."

    population = _extract_value("population", _paper_stub(), text)

    assert population == "240 adults with chronic rotator cuff tears undergoing arthroscopic repair"


def test_candidate_spans_focus_on_matching_sentence_context():
    chunk = SimpleNamespace(
        id=uuid4(),
        page_number=4,
        locator={"block": 2},
        text=(
            "Background sentence that should not be carried into the quote. "
            "Participants included 240 adults with chronic rotator cuff tears undergoing arthroscopic repair at two hospitals. "
            "Follow-up lasted 24 months."
        ),
    )

    spans = _candidate_spans([chunk], field_name="population", value="240 adults with chronic rotator cuff tears")

    assert len(spans) == 1
    assert "240 adults with chronic rotator cuff tears" in spans[0]["quoted_text"]
    assert "Background sentence" not in spans[0]["quoted_text"]
