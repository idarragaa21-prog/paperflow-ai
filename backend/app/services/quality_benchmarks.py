from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

STRICT_CHAT_THRESHOLDS = {
    "hit_at_5": 0.85,
    "citation_precision": 0.90,
    "blocked_answer_correctness": 0.90,
    "unsupported_answer_rate": 0.02,
}

EXTRACTION_THRESHOLDS = {
    "exact_fields": {
        "doi": 0.95,
        "year": 0.95,
        "title": 0.95,
    },
    "partial_fields": {
        "design": 0.85,
        "population": 0.85,
        "sample": 0.85,
        "outcomes": 0.85,
        "results": 0.85,
    },
    "unsupported_extraction_rate": 0.03,
}


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    lowered = value.strip().lower()
    lowered = re.sub(r"[^a-z0-9]+", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered).strip()
    return lowered


def _token_set(value: str | None) -> set[str]:
    normalized = normalize_text(value)
    return {token for token in normalized.split() if token}


def partial_match_score(predicted: str | None, gold: str | None) -> float:
    predicted_tokens = _token_set(predicted)
    gold_tokens = _token_set(gold)
    if not predicted_tokens or not gold_tokens:
        return 0.0
    overlap = len(predicted_tokens & gold_tokens)
    union = len(predicted_tokens | gold_tokens) or 1
    containment = overlap / max(len(gold_tokens), 1)
    jaccard = overlap / union
    return max(containment, jaccard)


def evaluate_chat_cases(cases: list[dict[str, Any]], *, k: int = 5) -> dict[str, Any]:
    answerable_cases = [case for case in cases if not bool(case.get("expected_blocked"))]
    blocked_correct = 0
    unsupported = 0
    hit_count = 0
    citation_precision_scores: list[float] = []

    for case in cases:
        predicted_blocked = bool(case.get("blocked_reason")) or not bool(case.get("grounded", True))
        if predicted_blocked == bool(case.get("expected_blocked")):
            blocked_correct += 1

    for case in answerable_cases:
        retrieved = [str(item) for item in case.get("retrieved_chunk_ids", [])]
        gold_retrieved = {str(item) for item in case.get("gold_chunk_ids", [])}
        predicted_citations = [str(item) for item in case.get("predicted_citation_ids", [])]
        gold_citations = {str(item) for item in case.get("gold_citation_ids", [])}
        grounded = bool(case.get("grounded", True))

        if any(item in gold_retrieved for item in retrieved[:k]):
            hit_count += 1

        if predicted_citations:
            matched = sum(1 for item in predicted_citations if item in gold_citations)
            citation_precision_scores.append(matched / len(predicted_citations))
        else:
            citation_precision_scores.append(0.0)

        if grounded and not any(item in gold_citations for item in predicted_citations):
            unsupported += 1

    answerable_total = max(len(answerable_cases), 1)
    return {
        "case_count": len(cases),
        "answerable_case_count": len(answerable_cases),
        "blocked_case_count": len(cases) - len(answerable_cases),
        "hit_at_5": hit_count / answerable_total,
        "citation_precision": sum(citation_precision_scores) / max(len(citation_precision_scores), 1),
        "blocked_answer_correctness": blocked_correct / max(len(cases), 1),
        "unsupported_answer_rate": unsupported / answerable_total,
    }


def evaluate_extraction_cases(cases: list[dict[str, Any]]) -> dict[str, Any]:
    per_field: dict[str, dict[str, float]] = {}
    unsupported_predictions = 0
    supported_predictions = 0
    calibration_errors: list[float] = []

    for case in cases:
        for field_name, payload in (case.get("fields") or {}).items():
            stats = per_field.setdefault(
                field_name,
                {
                    "total": 0,
                    "exact_matches": 0,
                    "partial_matches": 0,
                    "unsupported_predictions": 0,
                },
            )
            predicted = payload.get("predicted")
            gold = payload.get("gold")
            has_locator = bool(payload.get("has_locator", False))
            confidence = payload.get("confidence")

            stats["total"] += 1
            if normalize_text(predicted) == normalize_text(gold):
                stats["exact_matches"] += 1
                stats["partial_matches"] += 1
                exact = 1.0
            else:
                exact = 0.0
                if partial_match_score(predicted, gold) >= 0.6:
                    stats["partial_matches"] += 1

            if predicted:
                supported_predictions += 1
                if not has_locator:
                    stats["unsupported_predictions"] += 1
                    unsupported_predictions += 1

            if confidence is not None:
                calibration_errors.append(abs(float(confidence) - exact))

    normalized_fields: dict[str, dict[str, float]] = {}
    for field_name, stats in per_field.items():
        total = max(int(stats["total"]), 1)
        normalized_fields[field_name] = {
            "total": total,
            "exact_match_rate": float(stats["exact_matches"]) / total,
            "partial_match_rate": float(stats["partial_matches"]) / total,
            "unsupported_rate": float(stats["unsupported_predictions"]) / total,
        }

    return {
        "field_metrics": normalized_fields,
        "unsupported_extraction_rate": unsupported_predictions / max(supported_predictions, 1),
        "mean_calibration_error": sum(calibration_errors) / max(len(calibration_errors), 1),
        "record_count": len(cases),
    }


def assert_chat_thresholds(metrics: dict[str, Any]) -> None:
    failures = []
    for key, threshold in STRICT_CHAT_THRESHOLDS.items():
        value = float(metrics.get(key) or 0.0)
        if key == "unsupported_answer_rate":
            if value > threshold:
                failures.append(f"{key}={value:.3f} > {threshold:.3f}")
        elif value < threshold:
            failures.append(f"{key}={value:.3f} < {threshold:.3f}")
    if failures:
        raise ValueError("Chat quality benchmark failed: " + ", ".join(failures))


def assert_extraction_thresholds(metrics: dict[str, Any]) -> None:
    failures = []
    field_metrics = metrics.get("field_metrics") or {}
    for field_name, threshold in EXTRACTION_THRESHOLDS["exact_fields"].items():
        rate = float((field_metrics.get(field_name) or {}).get("exact_match_rate") or 0.0)
        if rate < threshold:
            failures.append(f"{field_name}.exact={rate:.3f} < {threshold:.3f}")
    for field_name, threshold in EXTRACTION_THRESHOLDS["partial_fields"].items():
        rate = float((field_metrics.get(field_name) or {}).get("partial_match_rate") or 0.0)
        if rate < threshold:
            failures.append(f"{field_name}.partial={rate:.3f} < {threshold:.3f}")
    unsupported_rate = float(metrics.get("unsupported_extraction_rate") or 0.0)
    if unsupported_rate > EXTRACTION_THRESHOLDS["unsupported_extraction_rate"]:
        failures.append(
            "unsupported_extraction_rate="
            f"{unsupported_rate:.3f} > {EXTRACTION_THRESHOLDS['unsupported_extraction_rate']:.3f}"
        )
    if failures:
        raise ValueError("Extraction quality benchmark failed: " + ", ".join(failures))


def load_json_cases(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))
