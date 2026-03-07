from __future__ import annotations

import math
from typing import Tuple

from app.services.meta_extractor.schema import ExtractedStudySchema


def quality_gate(extracted: ExtractedStudySchema) -> Tuple[ExtractedStudySchema, list[str]]:
    warnings: list[str] = []

    # 1) If 2x2 complete -> compute OR + log OR + SE
    for es in extracted.effect_sizes:
        if all(v is not None for v in [es.a_events, es.b_non_events, es.c_events, es.d_non_events]):
            a = max(int(es.a_events or 0), 0)
            b = max(int(es.b_non_events or 0), 0)
            c = max(int(es.c_events or 0), 0)
            d = max(int(es.d_non_events or 0), 0)
            denom = max(b * c, 1)
            calculated_or = (a * d) / denom

            if es.or_value is not None and abs(calculated_or - float(es.or_value)) > 0.1:
                warnings.append(
                    f"OR mismatch for {es.outcome_name}: calculated={calculated_or:.3f}, reported={es.or_value}"
                )

            if es.or_value is None:
                es.or_value = float(calculated_or)

            if es.log_or is None:
                es.log_or = math.log(max(calculated_or, 0.001))

            if es.se_log_or is None:
                es.se_log_or = math.sqrt(1 / max(a, 1) + 1 / max(b, 1) + 1 / max(c, 1) + 1 / max(d, 1))

            if es.ci_lower_95 is None or es.ci_upper_95 is None:
                # Only compute if log_or and se are available
                if es.log_or is not None and es.se_log_or is not None:
                    es.ci_lower_95 = math.exp(es.log_or - 1.96 * es.se_log_or)
                    es.ci_upper_95 = math.exp(es.log_or + 1.96 * es.se_log_or)

    # 2) If adjusted and also has raw counts -> warn
    for es in extracted.effect_sizes:
        if es.is_adjusted and es.a_events is not None:
            warnings.append(
                f"Study reports both adjusted OR and raw 2x2 for {es.outcome_name}. Verify manually."
            )

    # 3) n_randomized >= n_analyzed
    for arm in extracted.arms:
        if arm.n_randomized and arm.n_analyzed and arm.n_analyzed > arm.n_randomized:
            warnings.append(
                f"Arm '{arm.arm_name}': n_analyzed ({arm.n_analyzed}) > n_randomized ({arm.n_randomized})"
            )

    # 4) global confidence based on completeness if unset
    if extracted.extraction_confidence == 0.0:
        d = extracted.model_dump()
        filled = sum(1 for _, v in d.items() if v not in (None, [], ""))
        total = max(len(d), 1)
        extracted.extraction_confidence = round(filled / total, 2)

    return extracted, warnings
