"""Sensitivity, subgroup, influence and publication-bias diagnostics.

These build on top of ``pool`` to give the analyses a referee will ask for:
leave-one-out and cumulative meta-analysis, subgroup comparison with a between-
group test, influence diagnostics (Baujat coordinates), and Duval & Tweedie's
trim-and-fill estimate of missing studies.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import stats

from .effects import Effect, back_transform
from .pooling import pool


def leave_one_out(effects: list[Effect], **pool_kwargs) -> list[dict]:
    """Re-pool with each study omitted in turn (sensitivity to a single study)."""
    if len(effects) < 3:
        return []
    out = []
    for i in range(len(effects)):
        subset = effects[:i] + effects[i + 1:]
        r = pool(subset, **pool_kwargs)
        nat = r.natural()
        out.append({
            "omitted": effects[i].label,
            "estimate": nat["estimate"],
            "ci_low": nat["ci_low"],
            "ci_high": nat["ci_high"],
            "i2": r.i2,
            "tau2": r.tau2,
            "p_value": r.p_value,
        })
    return out


def cumulative(effects: list[Effect], **pool_kwargs) -> list[dict]:
    """Cumulative meta-analysis: add studies one at a time (ordered by sort_key)."""
    if len(effects) < 2:
        return []
    if all(e.sort_key is not None for e in effects):
        order = sorted(range(len(effects)), key=lambda i: effects[i].sort_key)
    else:
        order = list(range(len(effects)))

    out, acc = [], []
    for idx in order:
        acc.append(effects[idx])
        kw = dict(pool_kwargs)
        if len(acc) < 2:
            kw["model"] = "fixed"  # a single study has no heterogeneity to model
        r = pool(acc, **kw)
        nat = r.natural()
        e = effects[idx]
        suffix = f" ({int(e.sort_key)})" if e.sort_key is not None and float(e.sort_key).is_integer() else ""
        out.append({
            "added": e.label + suffix,
            "k": len(acc),
            "estimate": nat["estimate"],
            "ci_low": nat["ci_low"],
            "ci_high": nat["ci_high"],
            "i2": r.i2,
            "p_value": r.p_value,
        })
    return out


def subgroup_analysis(effects: list[Effect], **pool_kwargs) -> dict | None:
    """Pool within each subgroup and test for a difference between subgroups."""
    groups: dict[str, list[Effect]] = {}
    for e in effects:
        groups.setdefault(e.subgroup or "(unspecified)", []).append(e)
    if len(groups) < 2:
        return None

    group_out, yis, vars_ = [], [], []
    for name, ge in groups.items():
        disp = pool(ge, **pool_kwargs)
        nat = disp.natural()
        # Model variance without the Knapp-Hartung inflation, for the between test.
        base = pool(ge, **{**pool_kwargs, "knapp_hartung": False})
        yis.append(base.estimate)
        vars_.append(base.se ** 2)
        group_out.append({
            "subgroup": name,
            "k": disp.k,
            "estimate": nat["estimate"],
            "ci_low": nat["ci_low"],
            "ci_high": nat["ci_high"],
            "i2": disp.i2,
            "tau2": disp.tau2,
        })

    yis = np.array(yis)
    wis = 1.0 / np.array(vars_)
    mu = float(np.sum(wis * yis) / np.sum(wis))
    q_between = float(np.sum(wis * (yis - mu) ** 2))
    df = len(group_out) - 1
    p = float(stats.chi2.sf(q_between, df)) if df > 0 else 1.0
    return {"groups": group_out, "q_between": q_between, "df": df, "p_value": p}


@dataclass
class InfluenceRow:
    label: str
    baujat_x: float        # contribution to overall heterogeneity
    baujat_y: float        # influence on the pooled estimate
    std_residual: float


def influence(effects: list[Effect], **pool_kwargs) -> list[dict]:
    """Per-study influence diagnostics, including Baujat-plot coordinates."""
    if len(effects) < 3:
        return []
    yi = np.array([e.yi for e in effects], dtype=float)
    vi = np.array([e.vi for e in effects], dtype=float)
    w = 1.0 / vi
    mu = float(np.sum(w * yi) / np.sum(w))

    full = pool(effects, **pool_kwargs)
    rows = []
    for i, e in enumerate(effects):
        subset = effects[:i] + effects[i + 1:]
        r = pool(subset, **pool_kwargs)
        baujat_x = float(w[i] * (yi[i] - mu) ** 2)              # heterogeneity contribution
        var_loo = r.se ** 2
        baujat_y = float((full.estimate - r.estimate) ** 2 / var_loo) if var_loo > 0 else 0.0
        std_res = float((yi[i] - mu) / np.sqrt(vi[i]))
        rows.append({
            "label": e.label,
            "baujat_x": baujat_x,
            "baujat_y": baujat_y,
            "std_residual": std_res,
        })
    return rows


def _fe_mean(yi: np.ndarray, vi: np.ndarray) -> float:
    w = 1.0 / vi
    return float(np.sum(w * yi) / np.sum(w))


def trim_and_fill(effects: list[Effect], *, side: str | None = None, **pool_kwargs) -> dict | None:
    """Duval & Tweedie trim-and-fill (L0 estimator) for publication bias.

    Iteratively estimates the number of studies missing due to small-study
    suppression, imputes their mirror images, and re-pools. Returns the number
    of imputed studies (k0), the side filled, and the adjusted estimate.
    """
    n = len(effects)
    if n < 3:
        return None
    yi = np.array([e.yi for e in effects], dtype=float)
    vi = np.array([e.vi for e in effects], dtype=float)

    # Decide which side is over-represented (we trim there, fill the opposite).
    beta0 = _fe_mean(yi, vi)
    if side in ("left", "right"):
        over_side = "right" if side == "left" else "left"
    else:
        centered0 = yi - beta0
        ranks0 = stats.rankdata(np.abs(centered0))
        t_right = float(np.sum(ranks0[centered0 > 0]))
        over_side = "right" if t_right > (n * (n + 1) / 4.0) else "left"
    fill_side = "left" if over_side == "right" else "right"
    sign = 1.0 if over_side == "right" else -1.0  # over-represented direction

    # Iterate the L0 estimator to a stable k0.
    k0 = 0
    beta = beta0
    for _ in range(100):
        order = np.argsort(sign * yi)            # ascending in the over-represented direction
        keep = order[: n - k0] if k0 > 0 else order
        beta = _fe_mean(yi[keep], vi[keep])
        centered = yi - beta
        ranks = stats.rankdata(np.abs(centered))
        signed = sign * centered
        t_over = float(np.sum(ranks[signed > 0]))
        l0 = (4.0 * t_over - n * (n + 1)) / (2.0 * n - 1.0)
        new_k0 = int(max(0, round(l0)))
        if new_k0 == k0:
            break
        k0 = new_k0
    k0 = min(k0, n - 1)

    observed = pool(effects, **pool_kwargs)
    obs_nat = observed.natural()
    if k0 <= 0:
        return {
            "k0": 0,
            "side": fill_side,
            "observed_estimate": obs_nat["estimate"],
            "observed_ci_low": obs_nat["ci_low"],
            "observed_ci_high": obs_nat["ci_high"],
            "adjusted_estimate": obs_nat["estimate"],
            "adjusted_ci_low": obs_nat["ci_low"],
            "adjusted_ci_high": obs_nat["ci_high"],
            "imputed": [],
        }

    # Impute: reflect the k0 most over-represented studies about the trimmed beta.
    order = np.argsort(sign * yi)
    extreme = order[-k0:]
    measure = effects[0].measure
    imputed = []
    filled = list(effects)
    for j in extreme:
        y_new = 2.0 * beta - yi[j]
        eff = Effect(label="(imputed)", yi=float(y_new), vi=float(vi[j]), measure=measure, note="trim-and-fill")
        filled.append(eff)
        imputed.append({"estimate": back_transform(measure, float(y_new)), "se": float(np.sqrt(vi[j]))})

    adjusted = pool(filled, **pool_kwargs)
    adj_nat = adjusted.natural()
    return {
        "k0": k0,
        "side": fill_side,
        "observed_estimate": obs_nat["estimate"],
        "observed_ci_low": obs_nat["ci_low"],
        "observed_ci_high": obs_nat["ci_high"],
        "adjusted_estimate": adj_nat["estimate"],
        "adjusted_ci_low": adj_nat["ci_low"],
        "adjusted_ci_high": adj_nat["ci_high"],
        "imputed": imputed,
    }
