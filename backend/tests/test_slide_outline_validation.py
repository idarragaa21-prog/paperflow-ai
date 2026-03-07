import pytest

from app.services.slide_generator import validate_outline


def test_validate_outline_requires_takeaway_and_citations_for_content():
    o = {
        "title": "x",
        "slides": [
            {"type": "content", "title": "A", "bullets": ["b1"]},
        ],
    }
    errs = validate_outline(o)
    assert any("missing takeaway" in e for e in errs)
    assert any("missing citations" in e for e in errs)


def test_validate_outline_evidence_table_requires_table():
    o = {
        "title": "x",
        "slides": [
            {"type": "evidence_table", "title": "T", "takeaway": "ok", "citations": ["PMID:1"], "table": {"headers": ["a"], "rows": []}},
        ],
    }
    errs = validate_outline(o)
    assert any("table.headers" in e for e in errs)
    assert any("table.rows" in e for e in errs)
