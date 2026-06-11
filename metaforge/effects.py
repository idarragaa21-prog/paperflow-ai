"""Effect-size computation for meta-analysis.

Turns the data an analyst actually has — 2x2 count tables, continuous arm
summaries, or precomputed effects with a CI — into a (yi, vi) pair on the
analysis scale, where yi is the (log) effect and vi its sampling variance.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


# Measures analysed on the log scale (so the null effect is log(1) = 0).
LOG_SCALE_MEASURES = {"OR", "RR", "HR", "IRR", "PLOGIT"}
RATIO_MEASURES = LOG_SCALE_MEASURES


@dataclass
class Effect:
    """One study's effect on the analysis scale."""

    label: str
    yi: float          # effect on the analysis scale (log for ratio measures)
    vi: float          # sampling variance of yi
    measure: str
    note: str | None = None

    @property
    def sei(self) -> float:
        return math.sqrt(self.vi)

    @property
    def ci(self) -> tuple[float, float]:
        return (self.yi - 1.96 * self.sei, self.yi + 1.96 * self.sei)


def is_log_scale(measure: str) -> bool:
    return measure.upper() in LOG_SCALE_MEASURES


def _need(d: dict, *keys: str) -> bool:
    return all(d.get(k) is not None for k in keys)


def from_2x2(a: float, b: float, c: float, d: float, *, measure: str = "OR", label: str = "") -> Effect:
    """Effect from a 2x2 table.

    a = intervention events, b = intervention non-events,
    c = control events,      d = control non-events.

    A Haldane-Anscombe 0.5 continuity correction is applied to every cell when
    any cell is zero (the standard fix for an undefined log ratio).
    """
    measure = measure.upper()
    note = None
    if min(a, b, c, d) == 0:
        a, b, c, d = a + 0.5, b + 0.5, c + 0.5, d + 0.5
        note = "0.5 continuity correction (zero cell)"

    n1, n2 = a + b, c + d
    if measure == "RR":
        r1, r2 = a / n1, c / n2
        yi = math.log(r1 / r2)
        vi = (1.0 / a) - (1.0 / n1) + (1.0 / c) - (1.0 / n2)
    elif measure == "RD":
        r1, r2 = a / n1, c / n2
        yi = r1 - r2
        vi = (r1 * (1 - r1) / n1) + (r2 * (1 - r2) / n2)
    else:  # OR (default), also a robust fallback for HR/IRR given only counts
        yi = math.log((a * d) / (b * c))
        vi = (1.0 / a) + (1.0 / b) + (1.0 / c) + (1.0 / d)
    return Effect(label=label, yi=yi, vi=vi, measure=measure, note=note)


def smd_hedges_g(
    n1: float, m1: float, sd1: float, n2: float, m2: float, sd2: float, *, label: str = ""
) -> Effect:
    """Standardised mean difference (Hedges' g) with small-sample correction."""
    df = n1 + n2 - 2
    sp = math.sqrt((((n1 - 1) * sd1 ** 2) + ((n2 - 1) * sd2 ** 2)) / df)
    cohen_d = (m1 - m2) / sp
    j = 1.0 - (3.0 / (4.0 * df - 1.0))  # small-sample bias correction
    g = j * cohen_d
    vi = ((n1 + n2) / (n1 * n2)) + (g ** 2) / (2.0 * df)
    return Effect(label=label, yi=g, vi=vi, measure="SMD", note="Hedges' g")


def mean_difference(
    n1: float, m1: float, sd1: float, n2: float, m2: float, sd2: float, *, label: str = ""
) -> Effect:
    """Raw mean difference."""
    yi = m1 - m2
    vi = (sd1 ** 2 / n1) + (sd2 ** 2 / n2)
    return Effect(label=label, yi=yi, vi=vi, measure="MD", note=None)


def from_effect_and_ci(
    effect: float, ci_low: float, ci_high: float, *, measure: str = "OR", label: str = ""
) -> Effect:
    """Effect with a 95% CI (e.g. an adjusted HR from a paper)."""
    measure = measure.upper()
    if is_log_scale(measure):
        yi = math.log(effect)
        sei = (math.log(ci_high) - math.log(ci_low)) / (2 * 1.96)
    else:
        yi = effect
        sei = (ci_high - ci_low) / (2 * 1.96)
    return Effect(label=label, yi=yi, vi=sei ** 2, measure=measure, note="from effect + 95% CI")


def from_effect_and_se(effect: float, se: float, *, measure: str = "OR", label: str = "") -> Effect:
    measure = measure.upper()
    yi = math.log(effect) if is_log_scale(measure) else effect
    return Effect(label=label, yi=yi, vi=se ** 2, measure=measure, note="from effect + SE")


def from_yi_se(yi: float, se: float, *, measure: str = "GEN", label: str = "") -> Effect:
    """Generic inverse-variance: yi and its SE are already on the analysis scale."""
    return Effect(label=label, yi=yi, vi=se ** 2, measure=measure.upper())


def effect_from_row(row: dict) -> Effect:
    """Build an Effect from a flat dict (one CSV row), choosing the richest method available."""
    measure = str(row.get("effect_measure") or "OR").upper()
    label = str(row.get("study_label") or row.get("label") or "Study")

    def f(key: str) -> float | None:
        v = row.get(key)
        if v is None or v == "":
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    a, b, c, d = f("a_events"), f("b_non_events"), f("c_events"), f("d_non_events")
    if None not in (a, b, c, d):
        return from_2x2(a, b, c, d, measure=measure, label=label)

    n1, m1, sd1 = f("n_intervention"), f("mean_intervention"), f("sd_intervention")
    n2, m2, sd2 = f("n_control"), f("mean_control"), f("sd_control")
    if None not in (n1, m1, sd1, n2, m2, sd2):
        if measure == "MD":
            return mean_difference(n1, m1, sd1, n2, m2, sd2, label=label)
        return smd_hedges_g(n1, m1, sd1, n2, m2, sd2, label=label)

    yi, se = f("yi"), f("se")
    if yi is not None and se is not None:
        return from_yi_se(yi, se, measure=measure, label=label)

    effect = f("effect_value") or f("effect")
    se = f("effect_se") or f("se")
    lo, hi = f("ci_lower_95"), f("ci_upper_95")
    if effect is not None and se is not None:
        return from_effect_and_se(effect, se, measure=measure, label=label)
    if effect is not None and lo is not None and hi is not None:
        return from_effect_and_ci(effect, lo, hi, measure=measure, label=label)

    raise ValueError(f"Row '{label}' has no usable data (need 2x2 counts, arm summaries, or effect+SE/CI)")
