"""High-level analysis orchestration: rows -> effects -> full result + plots."""
from __future__ import annotations

from dataclasses import asdict

from . import diagnostics as dg
from .csvio import parse_csv
from .effects import Effect, MEASURE_LABELS, effect_from_row
from .plots import baujat_svg, forest_svg, funnel_svg, loo_forest_svg
from .pooling import egger_test, pool


def effects_from_rows(rows: list[dict]) -> tuple[list[Effect], list[str]]:
    effects: list[Effect] = []
    errors: list[str] = []
    for row in rows:
        try:
            effects.append(effect_from_row(row))
        except ValueError as exc:
            errors.append(str(exc))
    if not effects:
        raise ValueError("No usable rows. " + (" ".join(errors) if errors else ""))
    measures = {e.measure for e in effects}
    if len(measures) > 1:
        raise ValueError(
            f"All studies must share one effect_measure; found {', '.join(sorted(measures))}. "
            "Run separate analyses per measure."
        )
    return effects, errors


def analyze(
    rows: list[dict],
    *,
    model: str = "random",
    tau2_method: str = "REML",
    knapp_hartung: bool = True,
    favours_low: str = "intervention",
    favours_high: str = "control",
) -> dict:
    effects, warnings = effects_from_rows(rows)
    pool_kwargs = dict(model=model, tau2_method=tau2_method, knapp_hartung=knapp_hartung)
    result = pool(effects, **pool_kwargs)
    natural = result.natural()

    studies = []
    for i, e in enumerate(effects):
        nat = e.natural()
        studies.append({
            "label": e.label,
            "subgroup": e.subgroup,
            "measure": e.measure,
            "yi": e.yi,
            "se": e.sei,
            "estimate": nat["estimate"],
            "ci_low": nat["ci_low"],
            "ci_high": nat["ci_high"],
            "weight_pct": result.weights_pct[i],
            "note": e.note,
        })

    egger = asdict(egger_test(effects)) if len(effects) >= 3 else None
    subgroups = dg.subgroup_analysis(effects, **pool_kwargs)
    loo = dg.leave_one_out(effects, **pool_kwargs)
    cumulative = dg.cumulative(effects, **pool_kwargs)
    influence = dg.influence(effects, **pool_kwargs)
    trim_fill = dg.trim_and_fill(effects, **pool_kwargs)

    return {
        "measure": result.measure,
        "measure_label": MEASURE_LABELS.get(result.measure, result.measure),
        "log_scale": result.log_scale,
        "model": result.model,
        "tau2_method": result.tau2_method,
        "knapp_hartung": result.knapp_hartung,
        "k": result.k,
        "warnings": warnings,
        "pooled": {
            "estimate": natural["estimate"],
            "ci_low": natural["ci_low"],
            "ci_high": natural["ci_high"],
            "estimate_analysis_scale": result.estimate,
            "se": result.se,
            "p_value": result.p_value,
            "pi_low": natural["pi_low"],
            "pi_high": natural["pi_high"],
        },
        "heterogeneity": {
            "i2": result.i2,
            "tau2": result.tau2,
            "h2": result.h2,
            "q": result.q,
            "q_df": result.q_df,
            "q_p": result.q_p,
        },
        "egger": egger,
        "subgroups": subgroups,
        "leave_one_out": loo,
        "cumulative": cumulative,
        "influence": influence,
        "trim_fill": trim_fill,
        "studies": studies,
        "forest_svg": forest_svg(effects, result, favours_low=favours_low, favours_high=favours_high),
        "funnel_svg": funnel_svg(effects, result, imputed=(trim_fill or {}).get("imputed")),
        "loo_forest_svg": loo_forest_svg(loo, result),
        "baujat_svg": baujat_svg(influence),
    }


def analyze_csv(text: str, **kwargs) -> dict:
    return analyze(parse_csv(text), **kwargs)
