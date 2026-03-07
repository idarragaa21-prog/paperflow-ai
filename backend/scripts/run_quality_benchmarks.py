from __future__ import annotations

import json
from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.quality_benchmarks import (
    assert_chat_thresholds,
    assert_extraction_thresholds,
    evaluate_chat_cases,
    evaluate_extraction_cases,
    load_json_cases,
)


def main() -> int:
    repo_root = BACKEND_ROOT.parent
    benchmark_root = repo_root / "benchmarks"
    chat_cases = load_json_cases(benchmark_root / "chat_cases.json")
    extraction_cases = load_json_cases(benchmark_root / "extraction_cases.json")

    chat_metrics = evaluate_chat_cases(chat_cases)
    extraction_metrics = evaluate_extraction_cases(extraction_cases)

    print(
        json.dumps(
            {
                "chat": chat_metrics,
                "extraction": extraction_metrics,
            },
            indent=2,
            ensure_ascii=False,
        )
    )

    assert_chat_thresholds(chat_metrics)
    assert_extraction_thresholds(extraction_metrics)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
