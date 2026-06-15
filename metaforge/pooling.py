"""Pooling: fixed-effect and random-effects meta-analysis.

Random-effects supports DerSimonian-Laird, Paule-Mandel and REML estimators of
tau^2, plus the Knapp-Hartung variance adjustment and a Higgins prediction
interval — the toolkit an expert needs for a publishable synthesis.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy import stats

from .effects import Effect, back_transform, is_log_scale


@dataclass
class PoolResult:
    measure: str
    log_scale: bool
    model: str
    tau2_method: str
    k: int
    estimate: float            # analysis scale
    se: float
    ci_low: float
    ci_high: float
    z_or_t: float
    p_value: float
    tau2: float
    i2: float
    h2: float
    q: float
    q_df: int
    q_p: float
    pi_low: float | None       # prediction interval (analysis scale)
    pi_high: float | None
    knapp_hartung: bool
    weights_pct: list[float] = field(default_factory=list)

    def _bt(self, v: float | None) -> float | None:
        if v is None:
            return None
        return float(back_transform(self.measure, v))

    def natural(self) -> dict:
        """Estimates back-transformed to the reporting scale (e.g. OR rather than logOR)."""
        return {
            "estimate": self._bt(self.estimate),
            "ci_low": self._bt(self.ci_low),
            "ci_high": self._bt(self.ci_high),
            "pi_low": self._bt(self.pi_low),
            "pi_high": self._bt(self.pi_high),
        }


def _tau2_dl(yi: np.ndarray, vi: np.ndarray) -> float:
    w = 1.0 / vi
    mu = np.sum(w * yi) / np.sum(w)
    q = float(np.sum(w * (yi - mu) ** 2))
    df = len(yi) - 1
    c = float(np.sum(w) - np.sum(w ** 2) / np.sum(w))
    return max(0.0, (q - df) / c) if c > 0 else 0.0


def _tau2_paule_mandel(yi: np.ndarray, vi: np.ndarray, *, max_iter: int = 100) -> float:
    k = len(yi)
    tau2 = _tau2_dl(yi, vi)
    for _ in range(max_iter):
        w = 1.0 / (vi + tau2)
        mu = np.sum(w * yi) / np.sum(w)
        f = np.sum(w * (yi - mu) ** 2) - (k - 1)
        deriv = -np.sum(w ** 2 * (yi - mu) ** 2)
        if abs(deriv) < 1e-12:
            break
        new = tau2 - f / deriv
        new = max(0.0, float(new))
        if abs(new - tau2) < 1e-8:
            tau2 = new
            break
        tau2 = new
    return tau2


def _tau2_reml(yi: np.ndarray, vi: np.ndarray, *, max_iter: int = 200) -> float:
    tau2 = _tau2_dl(yi, vi)
    for _ in range(max_iter):
        w = 1.0 / (vi + tau2)
        sw = np.sum(w)
        mu = np.sum(w * yi) / sw
        # REML estimating equation (Viechtbauer 2005).
        num = np.sum(w ** 2 * ((yi - mu) ** 2 - vi)) + (1.0 / sw) * np.sum(w ** 2)
        den = np.sum(w ** 2)
        new = max(0.0, float(num / den)) if den > 0 else 0.0
        if abs(new - tau2) < 1e-9:
            tau2 = new
            break
        tau2 = new
    return tau2


_TAU2_ESTIMATORS = {"DL": _tau2_dl, "PM": _tau2_paule_mandel, "REML": _tau2_reml}


def pool(
    effects: list[Effect],
    *,
    model: str = "random",
    tau2_method: str = "REML",
    knapp_hartung: bool = True,
    prediction_interval: bool = True,
) -> PoolResult:
    """Pool a list of effects.

    model: "random" or "fixed". tau2_method: "REML" | "DL" | "PM".
    knapp_hartung applies the t-based Knapp-Hartung adjustment (random model).
    """
    if not effects:
        raise ValueError("No effects to pool")
    yi = np.array([e.yi for e in effects], dtype=float)
    vi = np.array([e.vi for e in effects], dtype=float)
    k = len(effects)
    measure = effects[0].measure
    log_scale = is_log_scale(measure)

    # Cochran's Q and heterogeneity (always from fixed-effect weights).
    w_fe = 1.0 / vi
    mu_fe = float(np.sum(w_fe * yi) / np.sum(w_fe))
    q = float(np.sum(w_fe * (yi - mu_fe) ** 2))
    q_df = k - 1
    q_p = float(stats.chi2.sf(q, q_df)) if q_df > 0 else 1.0
    i2 = max(0.0, (q - q_df) / q) * 100.0 if q > 0 else 0.0
    h2 = (q / q_df) if q_df > 0 else 1.0

    if model == "fixed":
        tau2 = 0.0
        tau2_method = "none"
    else:
        estimator = _TAU2_ESTIMATORS.get(tau2_method.upper())
        if estimator is None:
            raise ValueError(f"Unknown tau2 method: {tau2_method}")
        tau2 = estimator(yi, vi)

    w = 1.0 / (vi + tau2)
    sw = float(np.sum(w))
    estimate = float(np.sum(w * yi) / sw)
    var = 1.0 / sw
    weights_pct = list((w / sw) * 100.0)

    use_t = knapp_hartung and model == "random" and k > 1
    if use_t:
        # Knapp-Hartung: scale the variance by the weighted residual and use t_{k-1}.
        q_gen = float(np.sum(w * (yi - estimate) ** 2) / (k - 1))
        se = float(np.sqrt(q_gen * var))
        crit = float(stats.t.ppf(0.975, k - 1))
        stat = estimate / se if se > 0 else 0.0
        p_value = float(2 * stats.t.sf(abs(stat), k - 1))
    else:
        se = float(np.sqrt(var))
        crit = 1.959963984540054
        stat = estimate / se if se > 0 else 0.0
        p_value = float(2 * stats.norm.sf(abs(stat)))

    ci_low = estimate - crit * se
    ci_high = estimate + crit * se

    pi_low = pi_high = None
    if prediction_interval and model == "random" and k >= 3:
        t_pi = float(stats.t.ppf(0.975, k - 2))
        sd_pi = float(np.sqrt(tau2 + var))
        pi_low = estimate - t_pi * sd_pi
        pi_high = estimate + t_pi * sd_pi

    return PoolResult(
        measure=measure,
        log_scale=log_scale,
        model=model,
        tau2_method=tau2_method,
        k=k,
        estimate=estimate,
        se=se,
        ci_low=ci_low,
        ci_high=ci_high,
        z_or_t=stat,
        p_value=p_value,
        tau2=tau2,
        i2=i2,
        h2=h2,
        q=q,
        q_df=q_df,
        q_p=q_p,
        pi_low=pi_low,
        pi_high=pi_high,
        knapp_hartung=use_t,
        weights_pct=weights_pct,
    )


@dataclass
class EggerResult:
    intercept: float
    se: float
    t: float
    p_value: float
    k: int
    note: str


def egger_test(effects: list[Effect]) -> EggerResult:
    """Egger's regression test for funnel-plot asymmetry (small-study effects)."""
    k = len(effects)
    yi = np.array([e.yi for e in effects], dtype=float)
    sei = np.array([e.sei for e in effects], dtype=float)
    # Regress standardised effect (yi/sei) on precision (1/sei); test the intercept.
    y = yi / sei
    x = 1.0 / sei
    # Egger's test is undefined when every study has the same precision (e.g. all
    # studies share one sample size, common for correlations/proportions).
    if np.allclose(x, x[0]):
        return EggerResult(intercept=0.0, se=0.0, t=0.0, p_value=1.0, k=k,
                           note="No evaluable: todos los estudios tienen el mismo error estándar.")
    res = stats.linregress(x, y)
    note = "" if k >= 10 else "k < 10: low power, interpret with caution"
    return EggerResult(
        intercept=float(res.intercept),
        se=float(res.intercept_stderr),
        t=float(res.intercept / res.intercept_stderr) if res.intercept_stderr else 0.0,
        p_value=float(2 * stats.t.sf(abs(res.intercept / res.intercept_stderr), k - 2))
        if (k > 2 and res.intercept_stderr) else 1.0,
        k=k,
        note=note,
    )
