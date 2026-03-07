from __future__ import annotations

from app.services.meta_extractor.rob_defaults import generate_default_rob


def test_rob_defaults_rct():
    tool, rows = generate_default_rob("RCT")
    assert tool == "ROB2"
    assert len(rows) == 5
    assert rows[0].judgement == "unclear"


def test_rob_defaults_cohort():
    tool, rows = generate_default_rob("prospective cohort")
    assert tool == "NOS"
    assert len(rows) == 8


def test_rob_defaults_case_control():
    tool, rows = generate_default_rob("case-control")
    assert tool == "NOS"
    assert len(rows) == 8


def test_rob_defaults_diagnostic():
    tool, rows = generate_default_rob("diagnostic accuracy")
    assert tool == "QUADAS2"
    assert len(rows) == 4


def test_rob_defaults_unknown_fallbacks_to_rob2():
    tool, rows = generate_default_rob(None)
    assert tool == "ROB2"
    assert len(rows) == 5
