"""Mixed-effects meta-regression (moderator analysis).

Fits effect = b0 + b1·moderator with a DerSimonian-Laird estimate of the
residual between-study variance (tau^2), reports the slope with a Knapp-Hartung
t-test, the proportion of heterogeneity explained (R^2), and a bubble plot.
"""
from __future__ import annotations

import math

import numpy as np
from scipy import stats

from .effects import Effect, back_transform, has_null_line, is_log_scale, null_value
from .pooling import _tau2_dl


def _dl_residual_tau2(yi: np.ndarray, vi: np.ndarray, X: np.ndarray) -> float:
    """DerSimonian-Laird residual heterogeneity for a meta-regression."""
    k, p = X.shape
    w = 1.0 / vi
    W = np.diag(w)
    XtWX = X.T @ W @ X
    XtWX_inv = np.linalg.pinv(XtWX)
    beta = XtWX_inv @ X.T @ W @ yi
    resid = yi - X @ beta
    rss = float(resid.T @ W @ resid)
    # trace of the residual-making matrix P = W - W X (X'WX)^-1 X' W
    trace_P = float(np.trace(W) - np.trace(XtWX_inv @ (X.T @ (W @ W) @ X)))
    if trace_P <= 0:
        return 0.0
    return max(0.0, (rss - (k - p)) / trace_P)


def meta_regression(effects: list[Effect], x: list[float], *, knapp_hartung: bool = True) -> dict:
    yi = np.array([e.yi for e in effects], dtype=float)
    vi = np.array([e.vi for e in effects], dtype=float)
    xv = np.array(x, dtype=float)
    k = len(effects)
    if k < 3:
        raise ValueError("La meta-regresión necesita al menos 3 estudios.")
    if np.allclose(xv, xv[0]):
        raise ValueError("El moderador no varía entre estudios.")
    X = np.column_stack([np.ones(k), xv])
    p = X.shape[1]

    tau2 = _dl_residual_tau2(yi, vi, X)
    w = 1.0 / (vi + tau2)
    W = np.diag(w)
    XtWX_inv = np.linalg.pinv(X.T @ W @ X)
    beta = XtWX_inv @ X.T @ W @ yi
    cov = XtWX_inv
    resid = yi - X @ beta

    use_t = knapp_hartung and k > p
    if use_t:
        s2 = float(resid.T @ W @ resid) / (k - p)
        cov = XtWX_inv * s2
        crit = float(stats.t.ppf(0.975, k - p))
    se = np.sqrt(np.diag(cov))

    def _stat(i):
        b, s = float(beta[i]), float(se[i])
        z = b / s if s > 0 else 0.0
        pv = float(2 * stats.t.sf(abs(z), k - p)) if use_t else float(2 * stats.norm.sf(abs(z)))
        crit_i = crit if use_t else 1.959963984540054
        return {"estimate": b, "se": s, "stat": z, "p_value": pv,
                "ci_low": b - crit_i * s, "ci_high": b + crit_i * s}

    # R^2 (Raudenbush): heterogeneity explained vs intercept-only model.
    tau2_total = _tau2_dl(yi, vi)
    r2 = max(0.0, 1.0 - tau2 / tau2_total) * 100.0 if tau2_total > 0 else 0.0
    # residual heterogeneity test (Q_E)
    q_e = float(resid.T @ np.diag(1.0 / vi) @ resid)
    q_e_df = k - p
    q_e_p = float(stats.chi2.sf(q_e, q_e_df)) if q_e_df > 0 else 1.0

    return {
        "k": k, "knapp_hartung": use_t, "measure": effects[0].measure,
        "log_scale": is_log_scale(effects[0].measure),
        "intercept": _stat(0), "slope": _stat(1),
        "tau2_residual": tau2, "r2": r2,
        "qe": q_e, "qe_df": q_e_df, "qe_p": q_e_p,
    }


def bubble_svg(effects: list[Effect], x: list[float], reg: dict, moderator: str = "moderador") -> str:
    measure = reg["measure"]
    xv = np.array(x, dtype=float)
    yv = np.array([back_transform(measure, e.yi) for e in effects], dtype=float)
    tau2 = reg["tau2_residual"]
    w = np.array([1.0 / (e.vi + tau2) for e in effects])
    wmax = w.max() if len(w) else 1.0

    width, height = 520, 380
    pl, pr, pt, pb = 60, 24, 24, 50
    xmin, xmax = float(xv.min()), float(xv.max())
    if xmax - xmin < 1e-9:
        xmin, xmax = xmin - 1, xmax + 1
    xpad = (xmax - xmin) * 0.08
    xmin -= xpad; xmax += xpad
    ymin, ymax = float(yv.min()), float(yv.max())
    ypad = (ymax - ymin) * 0.12 or 1.0
    ymin -= ypad; ymax += ypad

    def sx(v): return pl + (v - xmin) / (xmax - xmin) * (width - pl - pr)
    def sy(v): return (height - pb) - (v - ymin) / (ymax - ymin) * (height - pt - pb)

    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" font-family="Helvetica, Arial, sans-serif">',
         f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
         '<text x="16" y="18" font-size="13" font-weight="700" fill="#111">Meta-regresión (bubble plot)</text>',
         f'<line x1="{pl}" y1="{pt}" x2="{pl}" y2="{height - pb}" stroke="#444"/>',
         f'<line x1="{pl}" y1="{height - pb}" x2="{width - pr}" y2="{height - pb}" stroke="#444"/>']
    # null reference line
    if has_null_line(measure):
        ny = back_transform(measure, null_value(measure))
        if ymin <= ny <= ymax:
            p.append(f'<line x1="{pl}" y1="{sy(ny):.1f}" x2="{width - pr}" y2="{sy(ny):.1f}" stroke="#bbb" stroke-dasharray="4 3"/>')
    # regression line (on analysis scale, back-transformed)
    b0, b1 = reg["intercept"]["estimate"], reg["slope"]["estimate"]
    xs_line = np.linspace(xmin, xmax, 40)
    pts = " ".join(f"{sx(xx):.1f},{sy(back_transform(measure, b0 + b1 * xx)):.1f}" for xx in xs_line)
    p.append(f'<polyline points="{pts}" fill="none" stroke="#c92a2a" stroke-width="2"/>')
    # bubbles
    for xi, yi2, wi in zip(xv, yv, w):
        r = 3 + 9 * math.sqrt(wi / wmax) if wmax else 4
        p.append(f'<circle cx="{sx(xi):.1f}" cy="{sy(yi2):.1f}" r="{r:.1f}" fill="#1c2d8c" fill-opacity="0.45" stroke="#1c2d8c"/>')
    # axis labels + ticks
    for frac in (0, 0.5, 1):
        xx = xmin + frac * (xmax - xmin)
        p.append(f'<text x="{sx(xx):.0f}" y="{height - pb + 16:.0f}" font-size="10" fill="#444" text-anchor="middle">{xx:.1f}</text>')
        yy = ymin + frac * (ymax - ymin)
        p.append(f'<text x="{pl - 8:.0f}" y="{sy(yy) + 3:.0f}" font-size="10" fill="#444" text-anchor="end">{yy:.2f}</text>')
    p.append(f'<text x="{(pl + width - pr) / 2:.0f}" y="{height - 12}" font-size="11" fill="#333" text-anchor="middle">{_esc(moderator)}</text>')
    p.append(f'<text x="16" y="{(pt + height - pb) / 2:.0f}" font-size="11" fill="#333" text-anchor="middle" transform="rotate(-90 16 {(pt + height - pb) / 2:.0f})">{_esc(measure)}</text>')
    p.append("</svg>")
    return "".join(p)


def _esc(t: object) -> str:
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
