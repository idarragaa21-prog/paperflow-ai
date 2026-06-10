from __future__ import annotations

import base64
import json
import math
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.core.storage import storage_manager
from app.models.matrix import MatrixRow, MatrixVersion
from app.models.meta_run import DerivedDataset, MetaRun, MetaRunArtifact


META_PRESETS = {
    "meta_binary_random",
    "meta_binary_fixed",
    "meta_continuous_md",
    "meta_continuous_smd",
    "meta_generic_iv",
    "meta_survival_hr",
    "meta_proportion",
    "meta_diag_accuracy",
    "risk_of_bias_summary",
    "publication_bias_suite",
}


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def _safe_log(value: float | None) -> float | None:
    if value is None or value <= 0:
        return None
    try:
        return float(math.log(value))
    except Exception:
        return None


def _derive_se_from_ci(ci_low: float | None, ci_high: float | None, *, log_scale: bool = True) -> float | None:
    if ci_low is None or ci_high is None:
        return None
    try:
        if log_scale:
            if ci_low <= 0 or ci_high <= 0:
                return None
            return float((math.log(ci_high) - math.log(ci_low)) / 3.92)
        return float((ci_high - ci_low) / 3.92)
    except Exception:
        return None


def _resolve_log_effect(data: dict[str, Any]) -> float | None:
    log_effect = _to_float(data.get("log_or")) or _to_float(data.get("log_effect"))
    if log_effect is not None:
        return log_effect
    candidate = (
        _to_float(data.get("effect_value"))
        or _to_float(data.get("or_value"))
        or _to_float(data.get("adjusted_or"))
        or _to_float(data.get("adjusted_rr"))
        or _to_float(data.get("adjusted_hr"))
    )
    return _safe_log(candidate)


def _resolve_se(data: dict[str, Any], *, log_scale: bool = True) -> float | None:
    se = _to_float(data.get("effect_se")) or _to_float(data.get("se_log_or")) or _to_float(data.get("se"))
    if se is not None:
        return se
    return _derive_se_from_ci(_to_float(data.get("ci_lower_95")), _to_float(data.get("ci_upper_95")), log_scale=log_scale)


def _covariates_as_json(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False)
    except Exception:
        return str(value)


def _base_dataset_row(*, row: MatrixRow, data: dict[str, Any], preset: str, effect_measure: str, outcome_type: str) -> dict[str, Any]:
    return {
        "preset": preset,
        "row_id": str(row.id),
        "row_key": row.row_key,
        "canonical_key": data.get("canonical_key"),
        "study_id": data.get("study_id"),
        "paper_id": data.get("paper_id"),
        "paper_title": data.get("paper_title"),
        "outcome_name": data.get("outcome_name"),
        "timepoint": data.get("timepoint"),
        "effect_measure": effect_measure,
        "outcome_type": outcome_type,
        "subgroup_label": data.get("subgroup_label"),
        "subgroup_level": data.get("subgroup_level"),
        "subgroup_order": _to_float(data.get("subgroup_order")),
        "sensitivity_flag": bool(data.get("sensitivity_flag") or False),
        "sensitivity_reason": data.get("sensitivity_reason"),
        "analysis_population": data.get("analysis_population"),
        "model_type": data.get("model_type"),
        "covariates_json": _covariates_as_json(data.get("covariates_json")),
        "risk_of_bias_overall": data.get("risk_of_bias_overall"),
        "confidence": _to_float(data.get("confidence")),
    }


def _coerce_dataset_rows(rows: list[MatrixRow], *, preset: str) -> tuple[list[dict[str, Any]], list[str]]:
    dataset_rows: list[dict[str, Any]] = []
    validation_warnings: list[str] = []

    for row in rows:
        if row.row_kind != "effect":
            continue

        data = row.data_json or {}
        effect_measure = str(data.get("effect_measure") or row.effect_measure or "").upper()
        outcome_type = str(data.get("outcome_type") or "").lower()
        base = _base_dataset_row(
            row=row,
            data=data,
            preset=preset,
            effect_measure=effect_measure,
            outcome_type=outcome_type,
        )

        if preset in {"meta_binary_random", "meta_binary_fixed"}:
            if effect_measure not in {"OR", "RR", "HR"} and outcome_type != "binary":
                continue
            a = _to_float(data.get("a_events"))
            b = _to_float(data.get("b_non_events"))
            c = _to_float(data.get("c_events"))
            d = _to_float(data.get("d_non_events"))
            log_effect = _resolve_log_effect(data)
            se = _resolve_se(data, log_scale=True)
            n_e = (a + b) if (a is not None and b is not None) else None
            n_c = (c + d) if (c is not None and d is not None) else None
            if (a is None or b is None or c is None or d is None) and (log_effect is None or se is None):
                validation_warnings.append(f"{row.row_key}: missing binary counts and log effect/SE")
                continue
            dataset_rows.append(
                {
                    **base,
                    "a_events": a,
                    "b_non_events": b,
                    "c_events": c,
                    "d_non_events": d,
                    "event_e": a,
                    "n_e": n_e,
                    "event_c": c,
                    "n_c": n_c,
                    "effect_value": _to_float(data.get("effect_value")) or _to_float(data.get("or_value")),
                    "log_effect": log_effect,
                    "se": se,
                    "ci_lower_95": _to_float(data.get("ci_lower_95")),
                    "ci_upper_95": _to_float(data.get("ci_upper_95")),
                }
            )
            continue

        if preset in {"meta_continuous_md", "meta_continuous_smd"}:
            if effect_measure not in {"MD", "SMD"} and outcome_type != "continuous":
                continue
            n_i = _to_float(data.get("n_intervention"))
            n_c = _to_float(data.get("n_control"))
            mean_i = _to_float(data.get("mean_intervention"))
            mean_c = _to_float(data.get("mean_control"))
            sd_i = _to_float(data.get("sd_intervention"))
            sd_c = _to_float(data.get("sd_control"))
            effect_value = _to_float(data.get("effect_value"))
            se = _resolve_se(data, log_scale=False)

            if effect_value is None and all(v is not None for v in (mean_i, mean_c)):
                raw_diff = float(mean_i - mean_c)
                if preset == "meta_continuous_smd":
                    if all(v is not None for v in (n_i, n_c, sd_i, sd_c)) and n_i > 1 and n_c > 1:
                        pooled_sd = math.sqrt((((n_i - 1) * (sd_i**2)) + ((n_c - 1) * (sd_c**2))) / max((n_i + n_c - 2), 1))
                        effect_value = (raw_diff / pooled_sd) if pooled_sd > 0 else None
                    else:
                        effect_value = None
                else:
                    effect_value = raw_diff

            if se is None and all(v is not None for v in (n_i, n_c, sd_i, sd_c)) and n_i > 0 and n_c > 0:
                se = math.sqrt((sd_i**2 / n_i) + (sd_c**2 / n_c))

            if effect_value is None or se is None:
                validation_warnings.append(f"{row.row_key}: missing continuous effect value/SE")
                continue

            dataset_rows.append(
                {
                    **base,
                    "n_intervention": n_i,
                    "n_control": n_c,
                    "mean_intervention": mean_i,
                    "sd_intervention": sd_i,
                    "mean_control": mean_c,
                    "sd_control": sd_c,
                    "effect_value": effect_value,
                    "log_effect": effect_value,
                    "se": se,
                    "ci_lower_95": _to_float(data.get("ci_lower_95")),
                    "ci_upper_95": _to_float(data.get("ci_upper_95")),
                }
            )
            continue

        if preset == "meta_generic_iv":
            log_effect = _resolve_log_effect(data)
            se = _resolve_se(data, log_scale=True)
            if log_effect is None or se is None:
                validation_warnings.append(f"{row.row_key}: missing generic inverse-variance effect/SE")
                continue
            dataset_rows.append(
                {
                    **base,
                    "effect_value": _to_float(data.get("effect_value")),
                    "log_effect": log_effect,
                    "se": se,
                    "ci_lower_95": _to_float(data.get("ci_lower_95")),
                    "ci_upper_95": _to_float(data.get("ci_upper_95")),
                }
            )
            continue

        if preset == "meta_survival_hr":
            if effect_measure not in {"HR"} and outcome_type not in {"time_to_event", "time-to-event", "survival"}:
                continue
            hr = _to_float(data.get("adjusted_hr")) or _to_float(data.get("effect_value"))
            log_effect = _resolve_log_effect(data)
            if log_effect is None:
                log_effect = _safe_log(hr)
            se = _resolve_se(data, log_scale=True)
            if log_effect is None or se is None:
                validation_warnings.append(f"{row.row_key}: missing survival HR/log-effect/SE")
                continue
            dataset_rows.append(
                {
                    **base,
                    "effect_value": hr,
                    "log_effect": log_effect,
                    "se": se,
                    "followup_time": _to_float(data.get("followup_time")),
                    "followup_unit": data.get("followup_unit"),
                    "person_time_intervention": _to_float(data.get("person_time_intervention")),
                    "person_time_control": _to_float(data.get("person_time_control")),
                    "ci_lower_95": _to_float(data.get("ci_lower_95")),
                    "ci_upper_95": _to_float(data.get("ci_upper_95")),
                }
            )
            continue

        if preset == "meta_proportion":
            if effect_measure not in {"PROPORTION", "PLOGIT"} and outcome_type != "proportion":
                continue
            events = _to_float(data.get("events_total")) or _to_float(data.get("a_events"))
            total = _to_float(data.get("total_n"))
            if total is None:
                a = _to_float(data.get("a_events"))
                b = _to_float(data.get("b_non_events"))
                if a is not None and b is not None:
                    total = a + b
            if events is None or total is None or total <= 0:
                validation_warnings.append(f"{row.row_key}: missing events/total for proportion analysis")
                continue
            proportion = events / total
            se = _to_float(data.get("effect_se"))
            if se is None:
                se = math.sqrt((proportion * (1 - proportion)) / total)
            dataset_rows.append(
                {
                    **base,
                    "events_total": events,
                    "total_n": total,
                    "effect_value": proportion,
                    "proportion": proportion,
                    "log_effect": _safe_log(proportion if proportion > 0 else None),
                    "se": se,
                }
            )
            continue

        if preset == "meta_diag_accuracy":
            tp = _to_float(data.get("tp")) or _to_float(data.get("a_events"))
            fp = _to_float(data.get("fp")) or _to_float(data.get("c_events"))
            fn = _to_float(data.get("fn")) or _to_float(data.get("b_non_events"))
            tn = _to_float(data.get("tn")) or _to_float(data.get("d_non_events"))
            sensitivity_value = _to_float(data.get("sensitivity_value"))
            specificity_value = _to_float(data.get("specificity_value"))
            if all(v is not None for v in (tp, fp, fn, tn)):
                sensitivity_value = sensitivity_value if sensitivity_value is not None else (tp / (tp + fn) if (tp + fn) > 0 else None)
                specificity_value = specificity_value if specificity_value is not None else (tn / (tn + fp) if (tn + fp) > 0 else None)
            if sensitivity_value is None or specificity_value is None:
                validation_warnings.append(f"{row.row_key}: missing diagnostic TP/FP/FN/TN or sensitivity/specificity")
                continue
            dataset_rows.append(
                {
                    **base,
                    "tp": tp,
                    "fp": fp,
                    "fn": fn,
                    "tn": tn,
                    "sensitivity": sensitivity_value,
                    "specificity": specificity_value,
                    "effect_value": sensitivity_value,
                    "log_effect": _safe_log(sensitivity_value),
                    "se": _to_float(data.get("effect_se")),
                }
            )
            continue

        if preset == "risk_of_bias_summary":
            if not data.get("risk_of_bias_overall"):
                continue
            dataset_rows.append(
                {
                    **base,
                    "risk_of_bias_overall": data.get("risk_of_bias_overall"),
                    "effect_value": _to_float(data.get("effect_value")),
                }
            )
            continue

        if preset == "publication_bias_suite":
            log_effect = _resolve_log_effect(data)
            se = _resolve_se(data, log_scale=True)
            if log_effect is None or se is None:
                validation_warnings.append(f"{row.row_key}: missing log effect/SE for publication-bias diagnostics")
                continue
            dataset_rows.append(
                {
                    **base,
                    "effect_value": _to_float(data.get("effect_value")),
                    "log_effect": log_effect,
                    "se": se,
                    "ci_lower_95": _to_float(data.get("ci_lower_95")),
                    "ci_upper_95": _to_float(data.get("ci_upper_95")),
                }
            )

    return dataset_rows, validation_warnings


def _run_payload_summary(*, preset: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "preset": preset,
        "rows": len(rows),
        "columns": list(rows[0].keys()) if rows else [],
        "supports_publication": True,
        "note": "Run created from derived dataset rows with reproducible inputs.",
    }


# Presets analysed on the log scale (ratio measures, logit-transformed proportions).
_LOG_SCALE_PRESETS = {
    "meta_binary_random",
    "meta_binary_fixed",
    "meta_generic_iv",
    "meta_survival_hr",
    "meta_proportion",
    "publication_bias_suite",
}


def _normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _study_label(row: dict[str, Any], index: int) -> str:
    label = row.get("paper_title") or row.get("study_id") or row.get("row_key") or f"Study {index + 1}"
    text = str(label).strip()
    return (text[:48] + "…") if len(text) > 49 else text


def _extract_effect_points(rows: list[dict[str, Any]], *, log_scale: bool) -> list[dict[str, Any]]:
    """Coerce derived dataset rows into (label, yi, sei, ci) tuples for pooling."""
    points: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        yi = _to_float(row.get("log_effect"))
        if yi is None:
            yi = _to_float(row.get("effect_value"))
        sei = _to_float(row.get("se"))
        if yi is None or sei is None or sei <= 0:
            continue
        ci_low = _to_float(row.get("ci_lower_95"))
        ci_high = _to_float(row.get("ci_upper_95"))
        if log_scale:
            lo = math.log(ci_low) if (ci_low is not None and ci_low > 0) else yi - 1.96 * sei
            hi = math.log(ci_high) if (ci_high is not None and ci_high > 0) else yi + 1.96 * sei
        else:
            lo = ci_low if ci_low is not None else yi - 1.96 * sei
            hi = ci_high if ci_high is not None else yi + 1.96 * sei
        points.append({"label": _study_label(row, index), "yi": yi, "sei": sei, "lo": lo, "hi": hi})
    return points


def _pool_effects(points: list[dict[str, Any]], *, random_effects: bool) -> dict[str, Any]:
    """Inverse-variance pooling with DerSimonian-Laird random-effects estimate."""
    k = len(points)
    weights_fe = [1.0 / (p["sei"] ** 2) for p in points]
    sum_w = sum(weights_fe)
    est_fe = sum(w * p["yi"] for w, p in zip(weights_fe, points)) / sum_w
    q = sum(w * (p["yi"] - est_fe) ** 2 for w, p in zip(weights_fe, points))
    df = k - 1

    tau2 = 0.0
    if random_effects and df > 0:
        c = sum_w - (sum(w ** 2 for w in weights_fe) / sum_w)
        tau2 = max(0.0, (q - df) / c) if c > 0 else 0.0

    weights = [1.0 / (p["sei"] ** 2 + tau2) for p in points]
    sum_w_re = sum(weights)
    est = sum(w * p["yi"] for w, p in zip(weights, points)) / sum_w_re
    se = math.sqrt(1.0 / sum_w_re)
    ci_low = est - 1.96 * se
    ci_high = est + 1.96 * se
    z = est / se if se > 0 else 0.0
    p_value = 2.0 * (1.0 - _normal_cdf(abs(z)))
    i2 = max(0.0, (q - df) / q) * 100.0 if q > 0 else 0.0

    return {
        "k": k,
        "estimate": est,
        "se": se,
        "ci_low": ci_low,
        "ci_high": ci_high,
        "z": z,
        "p_value": p_value,
        "q": q,
        "df": df,
        "i2": i2,
        "tau2": tau2,
        "model": "random-effects (DL)" if (random_effects and df > 0) else "fixed-effect",
    }


def _forest_svg(*, points: list[dict[str, Any]], pooled: dict[str, Any], null_value: float, log_scale: bool) -> str:
    """Render a minimal but valid forest-plot SVG from pooled effect points."""
    lows = [p["lo"] for p in points] + [pooled["ci_low"], null_value]
    highs = [p["hi"] for p in points] + [pooled["ci_high"], null_value]
    x_min, x_max = min(lows), max(highs)
    if x_max - x_min < 1e-9:
        x_min -= 1.0
        x_max += 1.0
    pad = (x_max - x_min) * 0.1
    x_min -= pad
    x_max += pad

    left, right = 250, 560
    row_h = 26
    top = 40
    height = top + (len(points) + 2) * row_h + 30

    def sx(value: float) -> float:
        return left + (value - x_min) / (x_max - x_min) * (right - left)

    def fmt(value: float) -> str:
        return f"{math.exp(value):.2f}" if log_scale else f"{value:.2f}"

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="600" height="{height}" '
        f'viewBox="0 0 600 {height}" font-family="Helvetica, Arial, sans-serif">',
        f'<rect width="600" height="{height}" fill="#ffffff"/>',
        '<text x="20" y="24" font-size="14" font-weight="700" fill="#111">Forest plot</text>',
        f'<line x1="{sx(null_value):.1f}" y1="{top}" x2="{sx(null_value):.1f}" y2="{top + (len(points) + 1) * row_h}" '
        'stroke="#999" stroke-dasharray="4 3"/>',
    ]
    for i, p in enumerate(points):
        y = top + i * row_h + row_h / 2
        parts.append(f'<text x="20" y="{y + 4:.1f}" font-size="12" fill="#222">{_xml_escape(p["label"])}</text>')
        parts.append(f'<line x1="{sx(p["lo"]):.1f}" y1="{y:.1f}" x2="{sx(p["hi"]):.1f}" y2="{y:.1f}" stroke="#3b5bdb" stroke-width="2"/>')
        parts.append(f'<rect x="{sx(p["yi"]) - 3:.1f}" y="{y - 3:.1f}" width="6" height="6" fill="#1c2d8c"/>')
        parts.append(f'<text x="{right + 8}" y="{y + 4:.1f}" font-size="11" fill="#444">{fmt(p["yi"])}</text>')

    yd = top + len(points) * row_h + row_h / 2
    cx, lo_x, hi_x = sx(pooled["estimate"]), sx(pooled["ci_low"]), sx(pooled["ci_high"])
    parts.append(f'<text x="20" y="{yd + 4:.1f}" font-size="12" font-weight="700" fill="#111">Pooled ({_xml_escape(pooled["model"])})</text>')
    parts.append(
        f'<polygon points="{lo_x:.1f},{yd:.1f} {cx:.1f},{yd - 6:.1f} {hi_x:.1f},{yd:.1f} {cx:.1f},{yd + 6:.1f}" '
        'fill="#c92a2a"/>'
    )
    parts.append(f'<text x="{right + 8}" y="{yd + 4:.1f}" font-size="11" font-weight="700" fill="#111">{fmt(pooled["estimate"])}</text>')
    parts.append(f'<text x="20" y="{height - 12}" font-size="10" fill="#666">Heterogeneity: I²={pooled["i2"]:.0f}%, τ²={pooled["tau2"]:.3f}, Q={pooled["q"]:.2f}</text>')
    parts.append("</svg>")
    return "".join(parts)


def _xml_escape(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _local_meta_script(*, preset: str, log_scale: bool, random_effects: bool) -> str:
    method = "DL" if random_effects else "FE"
    transf = "transf=exp, " if log_scale else ""
    return (
        "# Reproducible meta-analysis (metafor)\n"
        "library(metafor)\n"
        'dat <- read.csv("effect_table.csv")\n'
        f'res <- rma(yi = dat$log_effect, sei = dat$se, method = "{method}")  # preset: {preset}\n'
        f"summary(res)\n"
        f"forest(res, {transf}slab = dat$paper_title)\n"
        "funnel(res)\n"
    )


def _local_meta_fallback(*, preset: str, rows: list[dict[str, Any]], input_params: dict | None) -> dict[str, Any] | None:
    """Compute a meta-analysis in-process when the external R engine is unavailable.

    Returns a payload shaped like the R engine `/run-analysis` response so the
    downstream artifact pipeline is identical, or None when the preset cannot be
    pooled locally (e.g. risk-of-bias / diagnostic accuracy summaries).
    """
    if preset in {"risk_of_bias_summary", "meta_diag_accuracy"}:
        return None

    log_scale = preset in _LOG_SCALE_PRESETS
    random_effects = not preset.endswith("_fixed")
    points = _extract_effect_points(rows, log_scale=log_scale)
    if not points:
        return None

    pooled = _pool_effects(points, random_effects=random_effects)
    null_value = 0.0
    estimate_natural = math.exp(pooled["estimate"]) if log_scale else pooled["estimate"]
    ci_low_natural = math.exp(pooled["ci_low"]) if log_scale else pooled["ci_low"]
    ci_high_natural = math.exp(pooled["ci_high"]) if log_scale else pooled["ci_high"]

    summary = {
        "preset": preset,
        "model": pooled["model"],
        "k": pooled["k"],
        "rows": len(rows),
        "estimate": round(estimate_natural, 4),
        "estimate_log_scale": round(pooled["estimate"], 4) if log_scale else None,
        "ci_lower_95": round(ci_low_natural, 4),
        "ci_upper_95": round(ci_high_natural, 4),
        "se": round(pooled["se"], 4),
        "z": round(pooled["z"], 4),
        "p_value": round(pooled["p_value"], 4),
        "q_statistic": round(pooled["q"], 4),
        "i_squared": round(pooled["i2"], 2),
        "tau_squared": round(pooled["tau2"], 4),
        "scale": "log" if log_scale else "raw",
        "supports_publication": True,
        "engine": "python-local-fallback",
        "note": "Computed with the built-in Python meta-analysis engine (R engine unavailable).",
    }

    return {
        "summary": summary,
        "script": _local_meta_script(preset=preset, log_scale=log_scale, random_effects=random_effects),
        "engine_version": "python-local-fallback/1.0",
        "warnings": ["R engine unavailable; results computed with the built-in Python fallback engine."],
        "figure_artifacts": {
            "forest": {"svg": _forest_svg(points=points, pooled=pooled, null_value=null_value, log_scale=log_scale)},
        },
    }


def _decode_base64(payload: Any) -> bytes | None:
    if not isinstance(payload, str) or not payload:
        return None
    try:
        return base64.b64decode(payload, validate=True)
    except Exception:
        try:
            return base64.b64decode(payload)
        except Exception:
            return None


async def derive_dataset(
    db: AsyncSession,
    *,
    project_id: UUID,
    matrix_version: MatrixVersion,
    preset: str,
    title: str | None,
    build_params: dict | None,
    user_id: UUID | None,
) -> DerivedDataset:
    import pandas as pd

    if preset not in META_PRESETS:
        raise ValueError(f"Unsupported preset: {preset}")

    rows_stmt = (
        select(MatrixRow)
        .where(MatrixRow.matrix_version_id == matrix_version.id)
        .order_by(MatrixRow.sort_index.asc(), MatrixRow.created_at.asc())
    )
    rows = (await db.execute(rows_stmt)).scalars().all()
    dataset_rows, validation_warnings = _coerce_dataset_rows(rows, preset=preset)
    if not dataset_rows:
        warning_text = "; ".join(validation_warnings[:8]) if validation_warnings else "No effect rows matched this preset."
        raise ValueError(f"Dataset derivation failed for preset `{preset}`: {warning_text}")

    frame = pd.DataFrame(dataset_rows)
    csv_bytes = frame.to_csv(index=False).encode("utf-8")
    base_title = (title or f"{preset}_dataset").strip()
    saved = await storage_manager.save_dataset_bytes(
        data=csv_bytes,
        filename=f"{base_title}.csv",
        project_id=project_id,
    )

    dataset = DerivedDataset(
        project_id=project_id,
        matrix_version_id=matrix_version.id,
        created_by_user_id=user_id,
        title=base_title,
        preset=preset,
        status="ready",
        file_path=saved["file_path"],
        row_count=len(frame.index),
        column_count=len(frame.columns),
        schema_json={
            "columns": list(frame.columns),
            "preset_contract": preset,
            "validation_warnings": validation_warnings,
        },
        build_params={**(build_params or {}), "validation_warnings": validation_warnings},
        source_signature=matrix_version.source_signature,
    )
    db.add(dataset)
    await db.commit()
    await db.refresh(dataset)
    return dataset


async def get_derived_dataset(db: AsyncSession, *, dataset_id: UUID) -> DerivedDataset | None:
    return await db.get(DerivedDataset, dataset_id)


async def list_derived_datasets(db: AsyncSession, *, project_id: UUID) -> list[DerivedDataset]:
    q = await db.execute(
        select(DerivedDataset)
        .where(DerivedDataset.project_id == project_id)
        .order_by(DerivedDataset.created_at.desc())
    )
    return q.scalars().all()


def _preset_to_analysis_type(preset: str) -> str:
    if preset not in META_PRESETS:
        raise ValueError(f"Unsupported preset: {preset}")
    return preset


async def run_meta_analysis(
    db: AsyncSession,
    *,
    project_id: UUID,
    dataset: DerivedDataset,
    preset: str,
    title: str | None,
    input_params: dict | None,
    user_id: UUID | None,
) -> MetaRun:
    analysis_type = _preset_to_analysis_type(preset)
    if str(dataset.preset or "").strip() != preset:
        raise ValueError(
            f"Preset mismatch: dataset preset `{dataset.preset}` cannot run as `{preset}`. "
            "Derive a dataset with the same preset before running analysis."
        )

    run = MetaRun(
        project_id=project_id,
        matrix_version_id=dataset.matrix_version_id,
        derived_dataset_id=dataset.id,
        created_by_user_id=user_id,
        title=(title or f"{preset} run").strip(),
        preset=preset,
        status="running",
        input_params=input_params or {},
        runtime_json={},
        started_at=datetime.now(timezone.utc),
    )
    db.add(run)
    await db.flush()

    import pandas as pd

    with storage_manager.local_path(dataset.file_path, suffix=".csv") as local_path:
        frame = pd.read_csv(local_path)
    # Use JSON roundtrip to normalize pandas NaN/NaT into JSON-null values.
    rows = json.loads(frame.to_json(orient="records", date_format="iso"))

    response_data: dict[str, Any]
    warnings: list[str] = []
    engine_label = "r-engine"
    try:
        async with httpx.AsyncClient(timeout=40) as client:
            response = await client.post(
                f"{settings.R_ENGINE_URL}/run-analysis",
                json={
                    "analysis_type": analysis_type,
                    "input_params": input_params or {},
                    "rows": rows,
                },
            )
            response.raise_for_status()
            response_data = response.json()
    except Exception as exc:
        # Local-first fallback: when the external R engine is unreachable, compute
        # the meta-analysis in-process so the pipeline still produces real results.
        fallback = _local_meta_fallback(preset=preset, rows=rows, input_params=input_params)
        if fallback is None:
            run.status = "failed"
            run.summary_json = {
                "preset": preset,
                "rows": len(rows),
                "supports_publication": False,
                "note": "R engine execution failed and no local fallback is available for this preset.",
            }
            run.warnings = [f"R engine request failed: {exc}"]
            run.engine = "r-engine"
            run.engine_version = None
            run.runtime_json = {"preset": preset, "rows": len(rows), "supports_publication": False}
            run.completed_at = datetime.now(timezone.utc)
            await db.commit()
            stmt = select(MetaRun).where(MetaRun.id == run.id).options(selectinload(MetaRun.artifacts))
            hydrated = await db.execute(stmt)
            return hydrated.scalars().first()
        response_data = fallback
        engine_label = "python-local-fallback"
        warnings.append(f"R engine unavailable ({exc}); used built-in Python fallback engine.")

    summary = response_data.get("summary") or _run_payload_summary(preset=preset, rows=rows)
    warnings.extend(response_data.get("warnings") or [])
    script_text = str(response_data.get("script") or "")
    engine_version = str(response_data.get("engine_version") or "unknown")

    artifacts_to_create: list[tuple[str, str, bytes, str, dict[str, Any] | None]] = []

    summary_bytes = json.dumps(summary, ensure_ascii=False, indent=2).encode("utf-8")
    artifacts_to_create.append(("summary_json", f"{run.id}_summary.json", summary_bytes, "application/json", {"preset": preset}))

    effect_csv = frame.to_csv(index=False).encode("utf-8")
    artifacts_to_create.append(("effect_table_csv", f"{run.id}_effect_table.csv", effect_csv, "text/csv; charset=utf-8", {"preset": preset}))

    script_bytes = script_text.encode("utf-8")
    artifacts_to_create.append(("script_r", f"{run.id}_script.R", script_bytes, "text/x-r; charset=utf-8", {"preset": preset}))

    session_info = "\n".join(
        [
            f"engine_version: {engine_version}",
            f"preset: {preset}",
            f"generated_at: {datetime.now(timezone.utc).isoformat()}",
            f"warnings: {json.dumps(warnings, ensure_ascii=False)}",
        ]
    ).encode("utf-8")
    artifacts_to_create.append(("session_info", f"{run.id}_sessionInfo.txt", session_info, "text/plain; charset=utf-8", {"preset": preset}))

    figure_artifacts = response_data.get("figure_artifacts") or {}
    figure_kinds = ("forest", "funnel", "rob", "influence")
    for kind in figure_kinds:
        payload = figure_artifacts.get(kind) if isinstance(figure_artifacts, dict) else None
        svg_bytes: bytes | None = None
        png_bytes: bytes | None = None
        pdf_bytes: bytes | None = None

        if isinstance(payload, dict):
            svg_text = payload.get("svg")
            if isinstance(svg_text, str) and svg_text.strip():
                svg_bytes = svg_text.encode("utf-8")
            png_bytes = _decode_base64(payload.get("png_base64"))
            pdf_bytes = _decode_base64(payload.get("pdf_base64"))

        if svg_bytes is None and png_bytes is None and pdf_bytes is None:
            warnings.append(f"Figure `{kind}` was not generated by the R engine.")
            continue

        prefix = kind if kind == "rob" else f"figure_{kind}"
        if svg_bytes is not None:
            artifacts_to_create.append((f"{prefix}_svg", f"{run.id}_{kind}.svg", svg_bytes, "image/svg+xml", {"preset": preset, "figure": kind}))
        if png_bytes is not None:
            artifacts_to_create.append((f"{prefix}_png", f"{run.id}_{kind}.png", png_bytes, "image/png", {"preset": preset, "figure": kind}))
        if pdf_bytes is not None:
            artifacts_to_create.append((f"{prefix}_pdf", f"{run.id}_{kind}.pdf", pdf_bytes, "application/pdf", {"preset": preset, "figure": kind}))

    saved_lookup: dict[str, str] = {}
    for artifact_type, filename, payload, mime, metadata in artifacts_to_create:
        saved = await storage_manager.save_artifact_bytes(data=payload, filename=filename, project_id=project_id)
        saved_lookup[artifact_type] = saved["file_path"]
        db.add(
            MetaRunArtifact(
                meta_run_id=run.id,
                artifact_type=artifact_type,
                filename=saved["filename"],
                file_path=saved["file_path"],
                mime_type=mime,
                metadata_json=metadata,
            )
        )

    run.status = "completed"
    run.summary_json = summary
    run.warnings = warnings
    run.engine = engine_label
    run.engine_version = engine_version
    run.script_path = saved_lookup.get("script_r")
    run.session_info_path = saved_lookup.get("session_info")
    run.runtime_json = {
        "rows": len(rows),
        "artifact_types": [item[0] for item in artifacts_to_create],
        "preset": preset,
    }
    run.completed_at = datetime.now(timezone.utc)

    await db.commit()
    stmt = select(MetaRun).where(MetaRun.id == run.id).options(selectinload(MetaRun.artifacts))
    hydrated = await db.execute(stmt)
    return hydrated.scalars().first()


async def list_meta_runs(db: AsyncSession, *, project_id: UUID) -> list[MetaRun]:
    q = await db.execute(
        select(MetaRun)
        .where(MetaRun.project_id == project_id)
        .options(selectinload(MetaRun.artifacts))
        .order_by(MetaRun.created_at.desc())
    )
    return q.scalars().all()


async def get_meta_run(db: AsyncSession, *, run_id: UUID) -> MetaRun | None:
    q = await db.execute(
        select(MetaRun)
        .where(MetaRun.id == run_id)
        .options(selectinload(MetaRun.artifacts))
    )
    return q.scalars().first()


def serialize_dataset(dataset: DerivedDataset) -> dict[str, Any]:
    return {
        "id": str(dataset.id),
        "project_id": str(dataset.project_id),
        "matrix_version_id": str(dataset.matrix_version_id),
        "title": dataset.title,
        "preset": dataset.preset,
        "status": dataset.status,
        "row_count": dataset.row_count,
        "column_count": dataset.column_count,
        "file_path": dataset.file_path,
        "schema_json": dataset.schema_json or {},
        "build_params": dataset.build_params or {},
        "created_at": dataset.created_at.isoformat() if dataset.created_at else None,
    }


def serialize_meta_run(run: MetaRun) -> dict[str, Any]:
    return {
        "id": str(run.id),
        "project_id": str(run.project_id),
        "matrix_version_id": str(run.matrix_version_id) if run.matrix_version_id else None,
        "derived_dataset_id": str(run.derived_dataset_id) if run.derived_dataset_id else None,
        "title": run.title,
        "preset": run.preset,
        "status": run.status,
        "input_params": run.input_params or {},
        "summary": run.summary_json or {},
        "warnings": run.warnings or [],
        "engine": run.engine,
        "engine_version": run.engine_version,
        "script_path": run.script_path,
        "session_info_path": run.session_info_path,
        "runtime": run.runtime_json or {},
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "artifacts": [
            {
                "id": str(item.id),
                "artifact_type": item.artifact_type,
                "filename": item.filename,
                "file_path": item.file_path,
                "mime_type": item.mime_type,
                "metadata_json": item.metadata_json or {},
            }
            for item in run.artifacts
        ],
    }
