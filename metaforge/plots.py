"""Publication-style forest and funnel plots as standalone SVG strings."""
from __future__ import annotations

import math

from .effects import Effect
from .pooling import PoolResult


def _esc(text: object) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _fmt(value: float, log_scale: bool) -> str:
    return f"{math.exp(value):.2f}" if log_scale else f"{value:.2f}"


def _axis_ticks(x_min: float, x_max: float, log_scale: bool) -> list[float]:
    if log_scale:
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
    log_scale = result.log_scale
    null_value = 0.0 if log_scale else 0.0
    cis = [e.ci for e in effects]
    lows = [c[0] for c in cis] + [result.ci_low, null_value]
    highs = [c[1] for c in cis] + [result.ci_high, null_value]
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

    null_x = sx(null_value)
    measure = _esc(result.measure)
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" font-family="Helvetica, Arial, sans-serif">',
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        f'<text x="20" y="26" font-size="14" font-weight="700" fill="#111">Forest plot — {measure} (95% CI)</text>',
        '<text x="20" y="46" font-size="10" fill="#888" font-weight="600">Study</text>',
        f'<text x="{est_x}" y="46" font-size="10" fill="#888" font-weight="600">{measure} [95% CI]</text>',
        f'<text x="{weight_x}" y="46" font-size="10" fill="#888" font-weight="600" text-anchor="end">Weight</text>',
        f'<line x1="{null_x:.1f}" y1="{top - 6}" x2="{null_x:.1f}" y2="{plot_bottom:.1f}" stroke="#999" stroke-dasharray="4 3"/>',
    ]
    max_w = max(result.weights_pct) if result.weights_pct else 1.0
    for i, e in enumerate(effects):
        y = top + i * row_h + row_h / 2
        lo, hi = e.ci
        w = result.weights_pct[i] if i < len(result.weights_pct) else 0.0
        size = 3.0 + 5.0 * math.sqrt((w / max_w) if max_w else 0)
        p.append(f'<text x="20" y="{y + 4:.1f}" font-size="12" fill="#222">{_esc(e.label)}</text>')
        p.append(f'<line x1="{sx(lo):.1f}" y1="{y:.1f}" x2="{sx(hi):.1f}" y2="{y:.1f}" stroke="#3b5bdb" stroke-width="1.6"/>')
        p.append(f'<rect x="{sx(e.yi) - size:.1f}" y="{y - size:.1f}" width="{2 * size:.1f}" height="{2 * size:.1f}" fill="#1c2d8c"/>')
        p.append(f'<text x="{est_x}" y="{y + 4:.1f}" font-size="11" fill="#444">{_fmt(e.yi, log_scale)} [{_fmt(lo, log_scale)}, {_fmt(hi, log_scale)}]</text>')
        p.append(f'<text x="{weight_x}" y="{y + 4:.1f}" font-size="10" fill="#777" text-anchor="end">{w:.1f}%</text>')

    yd = top + len(effects) * row_h + row_h / 2
    cx, lo_x, hi_x = sx(result.estimate), sx(result.ci_low), sx(result.ci_high)
    model_label = f"{result.model}-effects" + (f", {result.tau2_method}" if result.model == "random" else "")
    p.append(f'<text x="20" y="{yd + 4:.1f}" font-size="12" font-weight="700" fill="#111">Pooled ({_esc(model_label)})</text>')
    p.append(f'<polygon points="{lo_x:.1f},{yd:.1f} {cx:.1f},{yd - 7:.1f} {hi_x:.1f},{yd:.1f} {cx:.1f},{yd + 7:.1f}" fill="#c92a2a"/>')
    p.append(f'<text x="{est_x}" y="{yd + 4:.1f}" font-size="11" font-weight="700" fill="#111">{_fmt(result.estimate, log_scale)} [{_fmt(result.ci_low, log_scale)}, {_fmt(result.ci_high, log_scale)}]</text>')

    if result.pi_low is not None:
        yp = yd + 14
        p.append(f'<line x1="{sx(result.pi_low):.1f}" y1="{yp:.1f}" x2="{sx(result.pi_high):.1f}" y2="{yp:.1f}" stroke="#c92a2a" stroke-width="1.4" stroke-dasharray="3 2"/>')
        p.append(f'<text x="{est_x}" y="{yp + 4:.1f}" font-size="9" fill="#c92a2a">95% PI [{_fmt(result.pi_low, log_scale)}, {_fmt(result.pi_high, log_scale)}]</text>')

    p.append(f'<line x1="{left}" y1="{axis_y:.1f}" x2="{right}" y2="{axis_y:.1f}" stroke="#444"/>')
    for t in _axis_ticks(x_min, x_max, log_scale):
        tx = sx(t)
        p.append(f'<line x1="{tx:.1f}" y1="{axis_y:.1f}" x2="{tx:.1f}" y2="{axis_y + 4:.1f}" stroke="#444"/>')
        p.append(f'<text x="{tx:.1f}" y="{axis_y + 16:.1f}" font-size="10" fill="#444" text-anchor="middle">{_fmt(t, log_scale)}</text>')
    p.append(f'<text x="{null_x - 8:.1f}" y="{axis_y + 34:.1f}" font-size="10" fill="#666" text-anchor="end">◄ Favours {_esc(favours_low)}</text>')
    p.append(f'<text x="{null_x + 8:.1f}" y="{axis_y + 34:.1f}" font-size="10" fill="#666">Favours {_esc(favours_high)} ►</text>')
    p.append(f'<text x="20" y="{height - 8}" font-size="10" fill="#666">Heterogeneity: I²={result.i2:.0f}%, τ²={result.tau2:.3f}, Q={result.q:.2f} (df={result.q_df}), p={result.q_p:.3f}</text>')
    p.append("</svg>")
    return "".join(p)


def funnel_svg(effects: list[Effect], result: PoolResult) -> str:
    width, height = 460, 360
    pad_l, pad_r, pad_t, pad_b = 60, 20, 30, 50
    log_scale = result.log_scale
    yis = [e.yi for e in effects]
    seis = [e.sei for e in effects]
    se_max = max(seis) * 1.1
    x_center = result.estimate
    x_half = max(abs(e.yi - x_center) for e in effects) * 1.3 + 1.96 * se_max
    x_min, x_max = x_center - x_half, x_center + x_half

    def sx(v: float) -> float:
        return pad_l + (v - x_min) / (x_max - x_min) * (width - pad_l - pad_r)

    def sy(se: float) -> float:  # SE increases downward (inverted)
        return pad_t + (se / se_max) * (height - pad_t - pad_b)

    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" font-family="Helvetica, Arial, sans-serif">',
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        '<text x="16" y="20" font-size="13" font-weight="700" fill="#111">Funnel plot</text>',
    ]
    # 95% pseudo-confidence funnel around the pooled estimate.
    top_x = sx(x_center)
    bl = sx(x_center - 1.96 * se_max)
    br = sx(x_center + 1.96 * se_max)
    by = sy(se_max)
    p.append(f'<polygon points="{top_x:.1f},{sy(0):.1f} {bl:.1f},{by:.1f} {br:.1f},{by:.1f}" fill="#eef0fb" stroke="#c5cdf0"/>')
    p.append(f'<line x1="{sx(x_center):.1f}" y1="{sy(0):.1f}" x2="{sx(x_center):.1f}" y2="{by:.1f}" stroke="#888" stroke-dasharray="4 3"/>')
    # Axes.
    p.append(f'<line x1="{pad_l}" y1="{pad_t}" x2="{pad_l}" y2="{height - pad_b}" stroke="#444"/>')
    p.append(f'<line x1="{pad_l}" y1="{height - pad_b}" x2="{width - pad_r}" y2="{height - pad_b}" stroke="#444"/>')
    p.append(f'<text x="14" y="{(pad_t + by) / 2:.0f}" font-size="10" fill="#444" transform="rotate(-90 14 {(pad_t + by) / 2:.0f})" text-anchor="middle">Standard error</text>')
    p.append(f'<text x="{(pad_l + width - pad_r) / 2:.0f}" y="{height - 14}" font-size="10" fill="#444" text-anchor="middle">{_esc(result.measure)} (analysis scale)</text>')
    for e in effects:
        p.append(f'<circle cx="{sx(e.yi):.1f}" cy="{sy(e.sei):.1f}" r="4" fill="#1c2d8c" fill-opacity="0.75"/>')
    p.append("</svg>")
    return "".join(p)
