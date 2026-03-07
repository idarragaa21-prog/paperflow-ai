from __future__ import annotations

from pathlib import Path

from app.services.quality_benchmarks import (
    assert_chat_thresholds,
    assert_extraction_thresholds,
    evaluate_chat_cases,
    evaluate_extraction_cases,
    load_json_cases,
)


def test_chat_quality_benchmark_meets_internal_rc_thresholds():
    repo_root = Path(__file__).resolve().parents[2]
    metrics = evaluate_chat_cases(load_json_cases(repo_root / "benchmarks" / "chat_cases.json"))
    assert metrics["hit_at_5"] >= 0.85
    assert metrics["citation_precision"] >= 0.90
    assert metrics["blocked_answer_correctness"] >= 0.90
    assert metrics["unsupported_answer_rate"] <= 0.02
    assert_chat_thresholds(metrics)


def test_extraction_quality_benchmark_meets_internal_rc_thresholds():
    repo_root = Path(__file__).resolve().parents[2]
    metrics = evaluate_extraction_cases(load_json_cases(repo_root / "benchmarks" / "extraction_cases.json"))
    assert metrics["field_metrics"]["doi"]["exact_match_rate"] >= 0.95
    assert metrics["field_metrics"]["year"]["exact_match_rate"] >= 0.95
    assert metrics["field_metrics"]["title"]["exact_match_rate"] >= 0.95
    assert metrics["field_metrics"]["design"]["partial_match_rate"] >= 0.85
    assert metrics["field_metrics"]["population"]["partial_match_rate"] >= 0.85
    assert metrics["field_metrics"]["sample"]["partial_match_rate"] >= 0.85
    assert metrics["field_metrics"]["outcomes"]["partial_match_rate"] >= 0.85
    assert metrics["field_metrics"]["results"]["partial_match_rate"] >= 0.85
    assert metrics["unsupported_extraction_rate"] <= 0.03
    assert_extraction_thresholds(metrics)
