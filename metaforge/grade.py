"""GRADE certainty-of-evidence assessment.

Rates the certainty of the pooled evidence (High / Moderate / Low / Very low)
following GRADE: a starting level by design, downgraded for risk of bias,
inconsistency, indirectness, imprecision and publication bias, and (for
observational evidence) upgraded for large effect, dose-response or plausible
confounding. MetaForge auto-suggests the downgrades from the analysis; the user
can override every judgement.
"""
from __future__ import annotations

from .rob import domains_for

DOWNGRADE_DOMAINS = ["risk_of_bias", "inconsistency", "indirectness", "imprecision", "publication_bias"]
UPGRADE_DOMAINS = ["large_effect", "dose_response", "confounding"]

_DOWN = {"none": 0, "serious": -1, "very_serious": -2}
_UP = {"none": 0, "yes": 1, "large": 1, "very_large": 2}

_LEVELS = {4: "Alta", 3: "Moderada", 2: "Baja", 1: "Muy baja"}
DOMAIN_LABELS_ES = {
    "risk_of_bias": "Riesgo de sesgo",
    "inconsistency": "Inconsistencia",
    "indirectness": "Evidencia indirecta",
    "imprecision": "Imprecisión",
    "publication_bias": "Sesgo de publicación",
    "large_effect": "Magnitud del efecto",
    "dose_response": "Gradiente dosis-respuesta",
    "confounding": "Confusión residual",
}


def certainty_label(level: int) -> str:
    level = max(1, min(4, int(level)))
    return _LEVELS[level]


def _rob_high_fraction(rob: dict | None) -> tuple[float, int]:
    if not rob:
        return 0.0, 0
    tool = rob.get("tool", "rob2")
    codes = list(domains_for(tool).keys())
    ratings = rob.get("ratings", {})
    studies = rob.get("studies", list(ratings.keys()))
    order = ["na", "low", "some", "high", "critical"]
    high = 0
    for st in studies:
        row = ratings.get(st, {})
        worst = "na"
        for c in codes:
            r = row.get(c, "na")
            if order.index(r) > order.index(worst):
                worst = r
        if worst in ("high", "critical"):
            high += 1
    n = len(studies) or 1
    return high / n, high


def compute_certainty(design: str, downgrades: dict, upgrades: dict | None = None) -> dict:
    start = 4 if design == "rct" else 2
    total = start
    for d in DOWNGRADE_DOMAINS:
        total += _DOWN.get(downgrades.get(d, "none"), 0)
    if design != "rct" and upgrades:
        for u in UPGRADE_DOMAINS:
            total += _UP.get(upgrades.get(u, "none"), 0)
    level = max(1, min(4, total))
    return {"level": level, "label": certainty_label(level), "start": start}


def auto_grade(result: dict, *, design: str = "rct", rob: dict | None = None) -> dict:
    h = result["heterogeneity"]
    p = result["pooled"]
    log_scale = result.get("log_scale", False)
    null = 1.0 if log_scale else 0.0

    domains: dict[str, dict] = {}

    # Risk of bias (from the RoB assessment, if provided).
    frac, n_high = _rob_high_fraction(rob)
    if rob and rob.get("ratings"):
        if frac >= 0.5:
            domains["risk_of_bias"] = {"rating": "serious", "reason": f"{n_high} estudio(s) con riesgo alto/crítico (≥50%)."}
        else:
            domains["risk_of_bias"] = {"rating": "none", "reason": "Mayoría de estudios sin riesgo alto."}
    else:
        domains["risk_of_bias"] = {"rating": "none", "reason": "No evaluado (completa el riesgo de sesgo)."}

    # Inconsistency (heterogeneity).
    i2 = h["i2"]
    if i2 >= 75:
        domains["inconsistency"] = {"rating": "serious", "reason": f"Heterogeneidad alta (I²={i2:.0f}%)."}
    elif i2 >= 50:
        domains["inconsistency"] = {"rating": "serious", "reason": f"Heterogeneidad sustancial (I²={i2:.0f}%)."}
    else:
        domains["inconsistency"] = {"rating": "none", "reason": f"Heterogeneidad baja (I²={i2:.0f}%)."}

    # Indirectness — cannot be inferred from the numbers.
    domains["indirectness"] = {"rating": "none", "reason": "Juicio del revisor (PICO vs pregunta)."}

    # Imprecision: downgrade only when the 95% CI crosses the null; otherwise flag
    # a small evidence base for the reviewer to judge (optimal information size).
    crosses = p["ci_low"] < null < p["ci_high"]
    if crosses:
        domains["imprecision"] = {"rating": "serious", "reason": "El IC 95% cruza el valor nulo."}
    elif result["k"] < 5:
        domains["imprecision"] = {"rating": "none", "reason": f"IC no cruza el nulo; valore el tamaño de información óptimo (k={result['k']})."}
    else:
        domains["imprecision"] = {"rating": "none", "reason": "Estimación precisa; IC no cruza el nulo."}

    # Publication bias (Egger).
    egger = result.get("egger")
    if egger and result["k"] >= 10 and egger["p_value"] < 0.10:
        domains["publication_bias"] = {"rating": "serious", "reason": f"Asimetría del funnel (Egger p={egger['p_value']:.3f})."}
    elif egger and result["k"] < 10:
        domains["publication_bias"] = {"rating": "none", "reason": "No evaluable con fiabilidad (k<10)."}
    else:
        domains["publication_bias"] = {"rating": "none", "reason": "Sin asimetría evidente."}

    downgrades = {d: domains[d]["rating"] for d in DOWNGRADE_DOMAINS}
    upgrades = {u: "none" for u in UPGRADE_DOMAINS}
    certainty = compute_certainty(design, downgrades, upgrades)
    return {
        "design": design,
        "domains": domains,
        "upgrades": upgrades,
        "certainty": certainty,
        "summary": _summary_text(result, certainty),
    }


def grade_from_judgements(result: dict, design: str, downgrades: dict, upgrades: dict | None = None) -> dict:
    certainty = compute_certainty(design, downgrades, upgrades)
    return {"design": design, "certainty": certainty, "summary": _summary_text(result, certainty)}


def _summary_text(result: dict, certainty: dict) -> str:
    p = result["pooled"]
    m = result["measure"]
    return (
        f"Certeza de la evidencia: {certainty['label'].upper()} (⊕ nivel {certainty['level']}/4). "
        f"Efecto combinado {m} = {p['estimate']:.2f} (IC 95% {p['ci_low']:.2f}–{p['ci_high']:.2f}) "
        f"a partir de {result['k']} estudios."
    )
