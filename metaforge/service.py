"""High-level analysis orchestration: rows -> effects -> pooled result + plots."""
from __future__ import annotations

from dataclasses import asdict

from .csvio import parse_csv
from .effects import Effect, effect_from_row, is_log_scale
from .plots import forest_svg, funnel_svg
from .pooling import egger_test, pool


def effects_from_rows(rows: list[dict]) -> list[Effect]:
    effects: list[Effect] = []
    errors: list[str] = []
    for row in rows:
        try:
            effects.append(effect_from_row(row))
        except ValueError as exc:
            errors.append(str(exc))
    if not effects:
        raise ValueError("No usable rows. " + (" ".join(errors) if errors else ""))
    return effects


def analyze(
    rows: list[dict],
    *,
    model: str = "random",
    tau2_method: str = "REML",
    knapp_hartung: bool = True,
    favours_low: str = "intervention",
    favours_high: str = "control",
) -> dict:
    effects = effects_from_rows(rows)
    result = pool(effects, model=model, tau2_method=tau2_method, knapp_hartung=knapp_hartung)
    natural = result.natural()

    egger = None
    if len(effects) >= 3:
        e = egger_test(effects)
        egger = asdict(e)

    studies = [
        {
            "label": e.label,
            "measure": e.measure,
            "yi": e.yi,
            "se": e.sei,
            "estimate": (float(__import__("math").exp(e.yi)) if is_log_scale(e.measure) else e.yi),
            "ci_low": (float(__import__("math").exp(e.ci[0])) if is_log_scale(e.measure) else e.ci[0]),
            "ci_high": (float(__import__("math").exp(e.ci[1])) if is_log_scale(e.measure) else e.ci[1]),
            "weight_pct": result.weights_pct[i],
            "note": e.note,
        }
        for i, e in enumerate(effects)
    ]

    return {
        "measure": result.measure,
        "log_scale": result.log_scale,
        "model": result.model,
        "tau2_method": result.tau2_method,
        "knapp_hartung": result.knapp_hartung,
        "k": result.k,
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
        "studies": studies,
        "forest_svg": forest_svg(effects, result, favours_low=favours_low, favours_high=favours_high),
        "funnel_svg": funnel_svg(effects, result),
    }


def analyze_csv(text: str, **kwargs) -> dict:
    return analyze(parse_csv(text), **kwargs)
