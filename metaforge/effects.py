"""Effect-size computation for meta-analysis.

Turns the data an analyst actually has — 2x2 count tables, continuous arm
summaries, person-time counts, single-group proportions/correlations, or a
precomputed effect with a CI — into a (yi, vi) pair on the analysis scale,
where yi is the (transformed) effect and vi its sampling variance.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

# --- Measure registry --------------------------------------------------------
# Ratio measures live on the log scale (null effect log(1) = 0, back-transform exp).
RATIO_MEASURES = {"OR", "RR", "HR", "IRR"}
# Proportions are analysed on the logit scale (back-transform = inverse logit).
LOGIT_MEASURES = {"PLOGIT"}
# Correlations are analysed on Fisher's z scale (back-transform = tanh).
Z_MEASURES = {"ZCOR"}
# Linear measures are analysed and reported on their own scale.
LINEAR_MEASURES = {"MD", "SMD", "RD", "GEN", "MEAN"}

ALL_MEASURES = RATIO_MEASURES | LOGIT_MEASURES | Z_MEASURES | LINEAR_MEASURES

# Measures for which a vertical "no effect" reference line is meaningful, and the
# value of that line on the analysis scale.
_NULL_ON_ANALYSIS_SCALE = {
    "OR": 0.0, "RR": 0.0, "HR": 0.0, "IRR": 0.0,  # log(1) = 0
    "RD": 0.0, "MD": 0.0, "SMD": 0.0, "GEN": 0.0,
    "ZCOR": 0.0,  # r = 0 -> z = 0
}

MEASURE_LABELS = {
    "OR": "Odds ratio", "RR": "Risk ratio", "HR": "Hazard ratio",
    "IRR": "Incidence rate ratio", "RD": "Risk difference",
    "MD": "Mean difference", "SMD": "Std. mean difference (Hedges' g)",
    "PLOGIT": "Proportion", "ZCOR": "Correlation", "GEN": "Effect", "MEAN": "Mean",
}


def measure_scale(measure: str) -> str:
    m = measure.upper()
    if m in RATIO_MEASURES:
        return "log"
    if m in LOGIT_MEASURES:
        return "logit"
    if m in Z_MEASURES:
        return "z"
    return "linear"


def is_log_scale(measure: str) -> bool:
    return measure.upper() in RATIO_MEASURES


def has_null_line(measure: str) -> bool:
    return measure.upper() in _NULL_ON_ANALYSIS_SCALE


def null_value(measure: str) -> float:
    return _NULL_ON_ANALYSIS_SCALE.get(measure.upper(), 0.0)


def back_transform(measure: str, x: float) -> float:
    """Map an analysis-scale value back to its reporting scale."""
    scale = measure_scale(measure)
    if scale == "log":
        return math.exp(x)
    if scale == "logit":
        return 1.0 / (1.0 + math.exp(-x))
    if scale == "z":
        return math.tanh(x)
    return x


def forward_transform(measure: str, value: float) -> float:
    """Map a reporting-scale value to the analysis scale (inverse of back_transform)."""
    scale = measure_scale(measure)
    if scale == "log":
        return math.log(value)
    if scale == "logit":
        return math.log(value / (1.0 - value))
    if scale == "z":
        return math.atanh(value)
    return value


@dataclass
class Effect:
    """One study's effect on the analysis scale."""

    label: str
    yi: float          # effect on the analysis scale
    vi: float          # sampling variance of yi
    measure: str
    subgroup: str | None = None
    sort_key: float | None = None      # e.g. publication year, for cumulative MA
    note: str | None = None
    n_total: float | None = None       # participants in the study, when known

    @property
    def sei(self) -> float:
        return math.sqrt(self.vi)

    @property
    def ci(self) -> tuple[float, float]:
        return (self.yi - 1.959963984540054 * self.sei, self.yi + 1.959963984540054 * self.sei)

    def natural(self) -> dict:
        lo, hi = self.ci
        return {
            "estimate": back_transform(self.measure, self.yi),
            "ci_low": back_transform(self.measure, lo),
            "ci_high": back_transform(self.measure, hi),
        }


# --- Builders ----------------------------------------------------------------
def from_2x2(a, b, c, d, *, measure="OR", label="", **meta) -> Effect:
    """Effect from a 2x2 table.

    a = intervention events, b = intervention non-events,
    c = control events,      d = control non-events.

    A Haldane-Anscombe 0.5 continuity correction is applied to every cell when
    any cell is zero (the standard fix for an undefined log ratio).
    """
    measure = measure.upper()
    for name, val in (("a", a), ("b", b), ("c", c), ("d", d)):
        if val < 0:
            raise ValueError(f"2x2 cell '{name}' must be >= 0")
    n_total = a + b + c + d        # participants (before any continuity correction)
    note = None
    if min(a, b, c, d) == 0 and measure != "RD":
        a, b, c, d = a + 0.5, b + 0.5, c + 0.5, d + 0.5
        note = "0.5 continuity correction (zero cell)"

    n1, n2 = a + b, c + d
    if n1 == 0 or n2 == 0:
        raise ValueError("Each arm of a 2x2 table must have at least one participant")
    if measure == "RR":
        yi = math.log((a / n1) / (c / n2))
        vi = (1.0 / a) - (1.0 / n1) + (1.0 / c) - (1.0 / n2)
    elif measure == "RD":
        r1, r2 = a / n1, c / n2
        yi = r1 - r2
        vi = (r1 * (1 - r1) / n1) + (r2 * (1 - r2) / n2)
    else:  # OR (default); also a robust fallback for HR given only counts
        yi = math.log((a * d) / (b * c))
        vi = (1.0 / a) + (1.0 / b) + (1.0 / c) + (1.0 / d)
    return Effect(label=label, yi=yi, vi=vi, measure=measure, note=note, n_total=n_total, **meta)


def irr_from_person_time(a, t1, c, t2, *, label="", **meta) -> Effect:
    """Incidence rate ratio from event counts and person-time."""
    if t1 <= 0 or t2 <= 0:
        raise ValueError("Person-time must be positive")
    note = None
    if a == 0 or c == 0:
        a, c = a + 0.5, c + 0.5
        note = "0.5 continuity correction (zero events)"
    yi = math.log((a / t1) / (c / t2))
    vi = (1.0 / a) + (1.0 / c)
    return Effect(label=label, yi=yi, vi=vi, measure="IRR", note=note, **meta)


def smd_hedges_g(n1, m1, sd1, n2, m2, sd2, *, label="", **meta) -> Effect:
    """Standardised mean difference (Hedges' g) with small-sample correction."""
    if n1 < 2 or n2 < 2:
        raise ValueError("SMD needs n >= 2 in each arm")
    df = n1 + n2 - 2
    sp = math.sqrt((((n1 - 1) * sd1 ** 2) + ((n2 - 1) * sd2 ** 2)) / df)
    if sp == 0:
        raise ValueError("Pooled SD is zero; cannot standardise")
    cohen_d = (m1 - m2) / sp
    j = 1.0 - (3.0 / (4.0 * df - 1.0))  # small-sample bias correction
    g = j * cohen_d
    vi = ((n1 + n2) / (n1 * n2)) + (g ** 2) / (2.0 * df)
    return Effect(label=label, yi=g, vi=vi, measure="SMD", note="Hedges' g", n_total=n1 + n2, **meta)


def mean_difference(n1, m1, sd1, n2, m2, sd2, *, label="", **meta) -> Effect:
    """Raw mean difference."""
    yi = m1 - m2
    vi = (sd1 ** 2 / n1) + (sd2 ** 2 / n2)
    return Effect(label=label, yi=yi, vi=vi, measure="MD", n_total=n1 + n2, **meta)


def proportion_logit(events, n, *, label="", **meta) -> Effect:
    """Single-group proportion on the logit scale (prevalence meta-analysis)."""
    if n <= 0:
        raise ValueError("Sample size must be positive")
    if events < 0 or events > n:
        raise ValueError("events must be between 0 and n")
    note = None
    e, nn = events, n
    if e == 0 or e == n:
        e, nn = e + 0.5, n + 1.0
        note = "0.5 correction (boundary proportion)"
    p = e / nn
    yi = math.log(p / (1 - p))
    vi = 1.0 / (nn * p) + 1.0 / (nn * (1 - p))
    return Effect(label=label, yi=yi, vi=vi, measure="PLOGIT", note=note, n_total=n, **meta)


def correlation_z(r, n, *, label="", **meta) -> Effect:
    """Correlation on Fisher's z scale."""
    if n < 4:
        raise ValueError("Correlation meta-analysis needs n >= 4")
    if not -1 < r < 1:
        raise ValueError("Correlation must be in (-1, 1)")
    yi = math.atanh(r)
    vi = 1.0 / (n - 3)
    return Effect(label=label, yi=yi, vi=vi, measure="ZCOR", **meta)


def from_effect_and_ci(effect, ci_low, ci_high, *, measure="OR", label="", **meta) -> Effect:
    """Effect with a 95% CI (e.g. an adjusted HR from a paper)."""
    measure = measure.upper()
    yi = forward_transform(measure, effect)
    hi = forward_transform(measure, ci_high)
    lo = forward_transform(measure, ci_low)
    sei = (hi - lo) / (2 * 1.959963984540054)
    return Effect(label=label, yi=yi, vi=sei ** 2, measure=measure, note="from effect + 95% CI", **meta)


def from_effect_and_se(effect, se, *, measure="OR", label="", **meta) -> Effect:
    measure = measure.upper()
    yi = forward_transform(measure, effect)
    return Effect(label=label, yi=yi, vi=se ** 2, measure=measure, note="from effect + SE", **meta)


def from_yi_se(yi, se, *, measure="GEN", label="", **meta) -> Effect:
    """Generic inverse-variance: yi and its SE are already on the analysis scale."""
    return Effect(label=label, yi=yi, vi=se ** 2, measure=measure.upper(), **meta)


def _meta_from_row(row: dict) -> dict:
    sub = row.get("subgroup") or row.get("group")
    yr = row.get("year") or row.get("sort_key")
    sort_key = None
    if yr not in (None, ""):
        try:
            sort_key = float(yr)
        except (TypeError, ValueError):
            sort_key = None
    return {"subgroup": (str(sub).strip() if sub not in (None, "") else None), "sort_key": sort_key}


def effect_from_row(row: dict) -> Effect:
    """Build an Effect from a flat dict (one CSV row), choosing the richest method available."""
    measure = str(row.get("effect_measure") or "OR").upper()
    if measure not in ALL_MEASURES:
        raise ValueError(f"Unknown effect_measure '{measure}'. Supported: {', '.join(sorted(ALL_MEASURES))}")
    label = str(row.get("study_label") or row.get("label") or "Study")
    meta = _meta_from_row(row)

    def f(key: str):
        v = row.get(key)
        if v is None or v == "":
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    a, b, c, d = f("a_events"), f("b_non_events"), f("c_events"), f("d_non_events")
    if None not in (a, b, c, d):
        return from_2x2(a, b, c, d, measure=measure, label=label, **meta)

    ev_i, pt_i, ev_c, pt_c = f("events_intervention"), f("time_intervention"), f("events_control"), f("time_control")
    if None not in (ev_i, pt_i, ev_c, pt_c):
        return irr_from_person_time(ev_i, pt_i, ev_c, pt_c, label=label, **meta)

    n1, m1, sd1 = f("n_intervention"), f("mean_intervention"), f("sd_intervention")
    n2, m2, sd2 = f("n_control"), f("mean_control"), f("sd_control")
    if None not in (n1, m1, sd1, n2, m2, sd2):
        if measure == "MD":
            return mean_difference(n1, m1, sd1, n2, m2, sd2, label=label, **meta)
        return smd_hedges_g(n1, m1, sd1, n2, m2, sd2, label=label, **meta)

    events, n = f("events"), (f("n_total") if f("n_total") is not None else f("n"))
    if measure == "PLOGIT" and events is not None and n is not None:
        return proportion_logit(events, n, label=label, **meta)

    r = f("r") if f("r") is not None else f("correlation")
    if measure == "ZCOR" and r is not None and n is not None:
        return correlation_z(r, n, label=label, **meta)

    yi, se = f("yi"), f("se")
    if yi is not None and se is not None:
        return from_yi_se(yi, se, measure=measure, label=label, **meta)

    effect = f("effect_value") if f("effect_value") is not None else f("effect")
    se = f("effect_se") if f("effect_se") is not None else f("se")
    lo, hi = f("ci_lower_95"), f("ci_upper_95")
    if effect is not None and se is not None:
        return from_effect_and_se(effect, se, measure=measure, label=label, **meta)
    if effect is not None and lo is not None and hi is not None:
        return from_effect_and_ci(effect, lo, hi, measure=measure, label=label, **meta)

    raise ValueError(
        f"Row '{label}': no usable data. Provide 2x2 counts (a_events..d_non_events), "
        "person-time (events/time_intervention/control), arm summaries (n/mean/sd), "
        "events+n_total (PLOGIT), r+n_total (ZCOR), or effect+SE/CI."
    )
