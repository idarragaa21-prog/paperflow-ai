"""Publication-style forest, funnel, leave-one-out and Baujat plots as SVG."""
from __future__ import annotations

import math

from .effects import Effect, back_transform, has_null_line, is_log_scale, null_value
from .pooling import PoolResult


def _esc(text: object) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _fmt(value: float, measure: str) -> str:
    return f"{back_transform(measure, value):.2f}"


def _axis_ticks(x_min: float, x_max: float, measure: str) -> list[float]:
    """Tick positions on the analysis scale."""
    if is_log_scale(measure):
        cands = [0.1, 0.2, 0.25, 0.5, 1, 2, 4, 5, 10]
        ticks = [math.log(v) for v in cands if x_min <= math.log(v) <= x_max]
        return ticks or [0.0]
    span = x_max - x_min
    if span <= 0:
        return [x_min]
    step = 10 ** math.floor(math.log10(span))
    if span / step < 3:
        step /= 2
    start = math.ceil(x_min / step) * step
    ticks, val = [], start
    while val <= x_max and len(ticks) < 8:
        ticks.append(val)
        val += step
    return ticks


def forest_svg(
    effects: list[Effect],
    result: PoolResult,
    *,
    favours_low: str = "intervention",
    favours_high: str = "control",
) -> str:
    measure = result.measure
    show_null = has_null_line(measure)
    null_v = null_value(measure)
    cis = [e.ci for e in effects]
    lows = [c[0] for c in cis] + [result.ci_low]
    highs = [c[1] for c in cis] + [result.ci_high]
    if show_null:
        lows.append(null_v)
        highs.append(null_v)
    if result.pi_low is not None:
        lows.append(result.pi_low)
        highs.append(result.pi_high)
    x_min, x_max = min(lows), max(highs)
    if x_max - x_min < 1e-9:
        x_min, x_max = x_min - 1, x_max + 1
    pad = (x_max - x_min) * 0.12
    x_min -= pad
    x_max += pad

    width = 780
    left, right = 250, 470
    est_x, weight_x = right + 14, width - 16
    row_h, top = 26, 58
    plot_bottom = top + (len(effects) + 1) * row_h
    axis_y = plot_bottom + 8
    height = axis_y + 60

    def sx(v: float) -> float:
        return left + (v - x_min) / (x_max - x_min) * (right - left)

    em = _esc(measure)
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" font-family="Helvetica, Arial, sans-serif">',
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        f'<text x="20" y="26" font-size="14" font-weight="700" fill="#111">Forest plot — {em} (95% CI)</text>',
        '<text x="20" y="46" font-size="10" fill="#888" font-weight="600">Study</text>',
        f'<text x="{est_x}" y="46" font-size="10" fill="#888" font-weight="600">{em} [95% CI]</text>',
        f'<text x="{weight_x}" y="46" font-size="10" fill="#888" font-weight="600" text-anchor="end">Weight</text>',
    ]
    if show_null:
        nx = sx(null_v)
        p.append(f'<line x1="{nx:.1f}" y1="{top - 6}" x2="{nx:.1f}" y2="{plot_bottom:.1f}" stroke="#999" stroke-dasharray="4 3"/>')

    max_w = max(result.weights_pct) if result.weights_pct else 1.0
    for i, e in enumerate(effects):
        y = top + i * row_h + row_h / 2
        lo, hi = e.ci
        w = result.weights_pct[i] if i < len(result.weights_pct) else 0.0
        size = 3.0 + 5.0 * math.sqrt((w / max_w) if max_w else 0)
        p.append(f'<text x="20" y="{y + 4:.1f}" font-size="12" fill="#222">{_esc(e.label)}</text>')
        p.append(f'<line x1="{sx(lo):.1f}" y1="{y:.1f}" x2="{sx(hi):.1f}" y2="{y:.1f}" stroke="#3b5bdb" stroke-width="1.6"/>')
        p.append(f'<rect x="{sx(e.yi) - size:.1f}" y="{y - size:.1f}" width="{2 * size:.1f}" height="{2 * size:.1f}" fill="#1c2d8c"/>')
        p.append(f'<text x="{est_x}" y="{y + 4:.1f}" font-size="11" fill="#444">{_fmt(e.yi, measure)} [{_fmt(lo, measure)}, {_fmt(hi, measure)}]</text>')
        p.append(f'<text x="{weight_x}" y="{y + 4:.1f}" font-size="10" fill="#777" text-anchor="end">{w:.1f}%</text>')

    yd = top + len(effects) * row_h + row_h / 2
    cx, lo_x, hi_x = sx(result.estimate), sx(result.ci_low), sx(result.ci_high)
    model_label = f"{result.model}-effects" + (f", {result.tau2_method}" if result.model == "random" else "")
    p.append(f'<text x="20" y="{yd + 4:.1f}" font-size="12" font-weight="700" fill="#111">Pooled ({_esc(model_label)})</text>')
    p.append(f'<polygon points="{lo_x:.1f},{yd:.1f} {cx:.1f},{yd - 7:.1f} {hi_x:.1f},{yd:.1f} {cx:.1f},{yd + 7:.1f}" fill="#c92a2a"/>')
    p.append(f'<text x="{est_x}" y="{yd + 4:.1f}" font-size="11" font-weight="700" fill="#111">{_fmt(result.estimate, measure)} [{_fmt(result.ci_low, measure)}, {_fmt(result.ci_high, measure)}]</text>')

    if result.pi_low is not None:
        yp = yd + 14
        p.append(f'<line x1="{sx(result.pi_low):.1f}" y1="{yp:.1f}" x2="{sx(result.pi_high):.1f}" y2="{yp:.1f}" stroke="#c92a2a" stroke-width="1.4" stroke-dasharray="3 2"/>')
        p.append(f'<text x="{est_x}" y="{yp + 4:.1f}" font-size="9" fill="#c92a2a">95% PI [{_fmt(result.pi_low, measure)}, {_fmt(result.pi_high, measure)}]</text>')

    p.append(f'<line x1="{left}" y1="{axis_y:.1f}" x2="{right}" y2="{axis_y:.1f}" stroke="#444"/>')
    for t in _axis_ticks(x_min, x_max, measure):
        tx = sx(t)
        p.append(f'<line x1="{tx:.1f}" y1="{axis_y:.1f}" x2="{tx:.1f}" y2="{axis_y + 4:.1f}" stroke="#444"/>')
        p.append(f'<text x="{tx:.1f}" y="{axis_y + 16:.1f}" font-size="10" fill="#444" text-anchor="middle">{_fmt(t, measure)}</text>')
    if show_null:
        nx = sx(null_v)
        p.append(f'<text x="{nx - 8:.1f}" y="{axis_y + 34:.1f}" font-size="10" fill="#666" text-anchor="end">◄ Favours {_esc(favours_low)}</text>')
        p.append(f'<text x="{nx + 8:.1f}" y="{axis_y + 34:.1f}" font-size="10" fill="#666">Favours {_esc(favours_high)} ►</text>')
    p.append(f'<text x="20" y="{height - 8}" font-size="10" fill="#666">Heterogeneity: I²={result.i2:.0f}%, τ²={result.tau2:.3f}, Q={result.q:.2f} (df={result.q_df}), p={result.q_p:.3f}</text>')
    p.append("</svg>")
    return "".join(p)


def funnel_svg(effects: list[Effect], result: PoolResult, imputed: list[dict] | None = None) -> str:
    width, height = 460, 360
    pad_l, pad_r, pad_t, pad_b = 60, 20, 30, 50
    measure = result.measure
    seis = [e.sei for e in effects]
    imp_pts = []
    if imputed:
        from .effects import forward_transform
        for d in imputed:
            imp_pts.append((forward_transform(measure, d["estimate"]), d["se"]))
        seis += [s for _, s in imp_pts]
    se_max = (max(seis) if seis else 1.0) * 1.1 or 1.0
    x_center = result.estimate
    all_y = [e.yi for e in effects] + [y for y, _ in imp_pts]
    x_half = max(abs(y - x_center) for y in all_y) * 1.3 + 1.96 * se_max
    x_min, x_max = x_center - x_half, x_center + x_half

    def sx(v: float) -> float:
        return pad_l + (v - x_min) / (x_max - x_min) * (width - pad_l - pad_r)

    def sy(se: float) -> float:
        return pad_t + (se / se_max) * (height - pad_t - pad_b)

    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" font-family="Helvetica, Arial, sans-serif">',
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        '<text x="16" y="20" font-size="13" font-weight="700" fill="#111">Funnel plot</text>',
    ]
    bl = sx(x_center - 1.96 * se_max)
    br = sx(x_center + 1.96 * se_max)
    by = sy(se_max)
    p.append(f'<polygon points="{sx(x_center):.1f},{sy(0):.1f} {bl:.1f},{by:.1f} {br:.1f},{by:.1f}" fill="#eef0fb" stroke="#c5cdf0"/>')
    p.append(f'<line x1="{sx(x_center):.1f}" y1="{sy(0):.1f}" x2="{sx(x_center):.1f}" y2="{by:.1f}" stroke="#888" stroke-dasharray="4 3"/>')
    p.append(f'<line x1="{pad_l}" y1="{pad_t}" x2="{pad_l}" y2="{height - pad_b}" stroke="#444"/>')
    p.append(f'<line x1="{pad_l}" y1="{height - pad_b}" x2="{width - pad_r}" y2="{height - pad_b}" stroke="#444"/>')
    mid_y = (pad_t + by) / 2
    p.append(f'<text x="14" y="{mid_y:.0f}" font-size="10" fill="#444" transform="rotate(-90 14 {mid_y:.0f})" text-anchor="middle">Standard error</text>')
    p.append(f'<text x="{(pad_l + width - pad_r) / 2:.0f}" y="{height - 14}" font-size="10" fill="#444" text-anchor="middle">{_esc(measure)} (analysis scale)</text>')
    for e in effects:
        p.append(f'<circle cx="{sx(e.yi):.1f}" cy="{sy(e.sei):.1f}" r="4" fill="#1c2d8c" fill-opacity="0.75"/>')
    for y, se in imp_pts:
        p.append(f'<circle cx="{sx(y):.1f}" cy="{sy(se):.1f}" r="4.5" fill="none" stroke="#c92a2a" stroke-width="1.6"/>')
    if imp_pts:
        p.append(f'<text x="{width - pad_r:.0f}" y="20" font-size="9" fill="#c92a2a" text-anchor="end">○ imputed (trim-and-fill)</text>')
    p.append("</svg>")
    return "".join(p)


def loo_forest_svg(loo: list[dict], result: PoolResult) -> str:
    """Forest plot of leave-one-out estimates."""
    measure = result.measure
    if not loo:
        return ""
    from .effects import forward_transform
    rows = [(d["omitted"], forward_transform(measure, d["estimate"]),
             forward_transform(measure, d["ci_low"]), forward_transform(measure, d["ci_high"])) for d in loo]
    lows = [r[2] for r in rows] + [result.ci_low]
    highs = [r[3] for r in rows] + [result.ci_high]
    x_min, x_max = min(lows), max(highs)
    pad = (x_max - x_min) * 0.15 or 1.0
    x_min -= pad
    x_max += pad

    width = 560
    left, right = 230, 420
    est_x = right + 12
    row_h, top = 24, 50
    height = top + (len(rows) + 1) * row_h + 30

    def sx(v: float) -> float:
        return left + (v - x_min) / (x_max - x_min) * (right - left)

    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" font-family="Helvetica, Arial, sans-serif">',
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        '<text x="16" y="26" font-size="13" font-weight="700" fill="#111">Leave-one-out sensitivity</text>',
        f'<line x1="{sx(result.estimate):.1f}" y1="{top - 6}" x2="{sx(result.estimate):.1f}" y2="{top + len(rows) * row_h:.1f}" stroke="#c92a2a" stroke-dasharray="4 3"/>',
    ]
    for i, (lbl, est, lo, hi) in enumerate(rows):
        y = top + i * row_h + row_h / 2
        p.append(f'<text x="16" y="{y + 4:.1f}" font-size="11" fill="#333">− {_esc(lbl)}</text>')
        p.append(f'<line x1="{sx(lo):.1f}" y1="{y:.1f}" x2="{sx(hi):.1f}" y2="{y:.1f}" stroke="#3b5bdb" stroke-width="1.4"/>')
        p.append(f'<circle cx="{sx(est):.1f}" cy="{y:.1f}" r="3.4" fill="#1c2d8c"/>')
        p.append(f'<text x="{est_x}" y="{y + 4:.1f}" font-size="10" fill="#555">{back_transform(measure, est):.2f} [{back_transform(measure, lo):.2f}, {back_transform(measure, hi):.2f}]</text>')
    p.append(f'<text x="16" y="{height - 10}" font-size="9" fill="#888">Dashed red line = pooled estimate with all studies</text>')
    p.append("</svg>")
    return "".join(p)


def baujat_svg(influence: list[dict]) -> str:
    """Baujat plot: heterogeneity contribution (x) vs influence on the estimate (y)."""
    if not influence:
        return ""
    width, height = 460, 340
    pad = 52
    xs = [d["baujat_x"] for d in influence]
    ys = [d["baujat_y"] for d in influence]
    x_max = max(xs) * 1.15 or 1.0
    y_max = max(ys) * 1.15 or 1.0

    def sx(v: float) -> float:
        return pad + (v / x_max) * (width - pad - 20)

    def sy(v: float) -> float:
        return (height - pad) - (v / y_max) * (height - pad - 24)

    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" font-family="Helvetica, Arial, sans-serif">',
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        '<text x="16" y="22" font-size="13" font-weight="700" fill="#111">Baujat plot (influence)</text>',
        f'<line x1="{pad}" y1="24" x2="{pad}" y2="{height - pad}" stroke="#444"/>',
        f'<line x1="{pad}" y1="{height - pad}" x2="{width - 20}" y2="{height - pad}" stroke="#444"/>',
        f'<text x="{(pad + width - 20) / 2:.0f}" y="{height - 16}" font-size="10" fill="#444" text-anchor="middle">Contribution to heterogeneity</text>',
        f'<text x="16" y="{(24 + height - pad) / 2:.0f}" font-size="10" fill="#444" transform="rotate(-90 16 {(24 + height - pad) / 2:.0f})" text-anchor="middle">Influence on result</text>',
    ]
    for d in influence:
        x, y = sx(d["baujat_x"]), sy(d["baujat_y"])
        p.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.6" fill="#1c2d8c" fill-opacity="0.8"/>')
        p.append(f'<text x="{x + 5:.1f}" y="{y + 3:.1f}" font-size="8" fill="#666">{_esc(d["label"][:14])}</text>')
    p.append("</svg>")
    return "".join(p)
