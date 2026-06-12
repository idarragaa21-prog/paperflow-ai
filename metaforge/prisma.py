"""PRISMA 2020 study-flow diagram as a standalone SVG.

Builds the identification → screening → included flow that every systematic
review reports, from the counts the reviewer provides. Missing counts are
tolerated; derived totals are filled in where possible.
"""
from __future__ import annotations


def _i(counts: dict, key: str, default=None):
    v = counts.get(key)
    if v in (None, ""):
        return default
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def prisma_svg(counts: dict, *, included_meta: int | None = None) -> str:
    db = _i(counts, "identified_db", 0) or 0
    other = _i(counts, "identified_other", 0) or 0
    duplicates = _i(counts, "duplicates", 0) or 0
    identified = db + other
    screened = _i(counts, "screened", identified - duplicates)
    excluded_screen = _i(counts, "excluded_screen", None)
    fulltext = _i(counts, "fulltext_assessed", None)
    if fulltext is None and screened is not None and excluded_screen is not None:
        fulltext = screened - excluded_screen
    fulltext_excluded = _i(counts, "fulltext_excluded", None)
    included = _i(counts, "included", None)
    if included is None and fulltext is not None and fulltext_excluded is not None:
        included = fulltext - fulltext_excluded
    reasons = str(counts.get("exclusion_reasons") or "").strip()

    W, H = 720, 560
    lx, lw = 60, 320          # left (main flow) column
    rx, rw = 430, 230         # right (exclusions) column
    box_h = 64
    gap = 30
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Helvetica, Arial, sans-serif">',
        f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
        '<text x="20" y="26" font-size="14" font-weight="700" fill="#111">Diagrama de flujo PRISMA 2020</text>',
    ]

    def box(x, y, w, text, fill="#f4f4f5", stroke="#c8c8cf"):
        p.append(f'<rect x="{x}" y="{y}" width="{w}" height="{box_h}" rx="8" fill="{fill}" stroke="{stroke}"/>')
        lines = text.split("\n")
        ty = y + box_h / 2 - (len(lines) - 1) * 7 + 4
        for ln in lines:
            p.append(f'<text x="{x + w / 2}" y="{ty:.0f}" font-size="11.5" fill="#222" text-anchor="middle">{ln}</text>')
            ty += 14

    def arrow_down(x, y1, y2):
        p.append(f'<line x1="{x}" y1="{y1}" x2="{x}" y2="{y2}" stroke="#888" stroke-width="1.4"/>')
        p.append(f'<path d="M{x - 4},{y2 - 6} L{x},{y2} L{x + 4},{y2 - 6}" fill="#888"/>')

    def arrow_right(y, x1, x2):
        p.append(f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="#888" stroke-width="1.4"/>')
        p.append(f'<path d="M{x2 - 6},{y - 4} L{x2},{y} L{x2 - 6},{y + 4}" fill="#888"/>')

    y = 44
    primary = "#eef0fb"
    # 1. identified
    box(lx, y, lw, f"Registros identificados (n = {identified})\nbases: {db} · otras fuentes: {other}", primary, "#c5cdf0")
    box(rx, y, rw, f"Duplicados eliminados\n(n = {duplicates})")
    arrow_right(y + box_h / 2, lx + lw, rx)
    y2 = y + box_h + gap
    # 2. screened
    arrow_down(lx + lw / 2, y + box_h, y2)
    box(lx, y2, lw, f"Registros cribados\n(n = {'' if screened is None else screened})", primary, "#c5cdf0")
    if excluded_screen is not None:
        box(rx, y2, rw, f"Registros excluidos\n(n = {excluded_screen})")
        arrow_right(y2 + box_h / 2, lx + lw, rx)
    y3 = y2 + box_h + gap
    # 3. full text
    arrow_down(lx + lw / 2, y2 + box_h, y3)
    box(lx, y3, lw, f"Informes evaluados a texto completo\n(n = {'' if fulltext is None else fulltext})", primary, "#c5cdf0")
    if fulltext_excluded is not None:
        extra = f"\n{reasons}" if reasons else ""
        box(rx, y3, rw, f"Informes excluidos (n = {fulltext_excluded}){extra}")
        arrow_right(y3 + box_h / 2, lx + lw, rx)
    y4 = y3 + box_h + gap
    # 4. included
    arrow_down(lx + lw / 2, y3 + box_h, y4)
    meta_line = f"\nincluidos en meta-análisis: {included_meta}" if included_meta is not None else ""
    box(lx, y4, lw, f"Estudios incluidos en la revisión\n(n = {'' if included is None else included}){meta_line}",
        "#def7e8", "#bce9cf")

    # stage labels (left margin)
    for label, yy in [("Identificación", 44), ("Cribado", y2), ("Elegibilidad", y3), ("Incluidos", y4)]:
        p.append(f'<text x="16" y="{yy + box_h / 2 + 4:.0f}" font-size="9" fill="#999" transform="rotate(-90 16 {yy + box_h / 2:.0f})" text-anchor="middle">{label}</text>')
    p.append("</svg>")
    return "".join(p)
