"""PRISMA 2020 study-flow diagram as a standalone SVG.

A faithful single-column PRISMA 2020 flow (databases & registers): identification,
screening and inclusion, with word-wrapped boxes, the "records removed before
screening" breakdown, itemised exclusion reasons, and the split between studies
included in the review and in the meta-analysis. Missing counts are tolerated and
derived where possible.
"""
from __future__ import annotations


def _i(counts: dict, *keys, default=None):
    for key in keys:
        v = counts.get(key)
        if v not in (None, ""):
            try:
                return int(float(v))
            except (TypeError, ValueError):
                pass
    return default


def _wrap(text: str, max_chars: int) -> list[str]:
    lines, cur = [], ""
    for word in str(text).split():
        if len(cur) + len(word) + 1 <= max_chars or not cur:
            cur = (cur + " " + word).strip()
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines or [""]


def _reason_lines(reasons: str) -> list[str]:
    """Split 'a (12); b (8)' or newline-separated reasons into bullet lines."""
    if not reasons:
        return []
    raw = [r.strip() for chunk in str(reasons).split("\n") for r in chunk.split(";")]
    return [f"• {r}" for r in raw if r]


def prisma_svg(counts: dict, *, included_meta: int | None = None) -> str:
    db = _i(counts, "identified_db", default=0) or 0
    registers = _i(counts, "identified_registers", default=0) or 0
    other = _i(counts, "identified_other", default=0) or 0
    duplicates = _i(counts, "duplicates", default=0) or 0
    auto_removed = _i(counts, "auto_removed", default=None)
    other_removed = _i(counts, "other_removed", default=None)
    identified = db + registers + other
    removed = duplicates + (auto_removed or 0) + (other_removed or 0)
    screened = _i(counts, "screened", default=(identified - removed if identified else None))
    excluded_screen = _i(counts, "excluded_screen", default=None)
    sought = _i(counts, "sought", default=(
        (screened - excluded_screen) if (screened is not None and excluded_screen is not None) else None))
    not_retrieved = _i(counts, "not_retrieved", default=None)
    assessed = _i(counts, "assessed", "fulltext_assessed", default=(
        (sought - not_retrieved) if (sought is not None and not_retrieved is not None) else sought))
    fulltext_excluded = _i(counts, "fulltext_excluded", default=None)
    included = _i(counts, "included", default=(
        (assessed - fulltext_excluded) if (assessed is not None and fulltext_excluded is not None) else None))
    reasons = _reason_lines(counts.get("exclusion_reasons") or "")

    # --- layout -------------------------------------------------------------
    W = 780
    band = 28
    lx, lw = 64, 312          # main flow column
    rx, rw = 430, 300         # exclusion column
    pad_x, lh, vpad = 12, 15, 9
    gap = 34
    main_chars = 46
    side_chars = 44

    parts: list[str] = []

    def box(x, y, w, lines, *, fill="#eef0fb", stroke="#c5cdf0", bold_first=False):
        h = len(lines) * lh + 2 * vpad
        parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h:.0f}" rx="9" fill="{fill}" stroke="{stroke}" stroke-width="1.2"/>')
        ty = y + vpad + 11
        for i, ln in enumerate(lines):
            weight = "700" if (bold_first and i == 0) else "400"
            parts.append(f'<text x="{x + pad_x}" y="{ty:.0f}" font-size="11.5" font-weight="{weight}" fill="#1a1a22">{_esc(ln)}</text>')
            ty += lh
        return h

    def varrow(x, y1, y2):
        parts.append(f'<line x1="{x}" y1="{y1:.0f}" x2="{x}" y2="{y2:.0f}" stroke="#7a7a85" stroke-width="1.5"/>')
        parts.append(f'<path d="M{x - 5},{y2 - 7:.0f} L{x},{y2:.0f} L{x + 5},{y2 - 7:.0f}" fill="#7a7a85"/>')

    def harrow(y, x1, x2):
        parts.append(f'<line x1="{x1}" y1="{y:.0f}" x2="{x2}" y2="{y:.0f}" stroke="#7a7a85" stroke-width="1.5"/>')
        parts.append(f'<path d="M{x2 - 7},{y - 5:.0f} L{x2},{y:.0f} L{x2 - 7},{y + 5:.0f}" fill="#7a7a85"/>')

    def lines_id():
        out = [f"Registros identificados (n = {identified})"]
        out += _wrap(f"Bases de datos: {db}" + (f" · Registros: {registers}" if registers else "") + (f" · Otras fuentes: {other}" if other else ""), main_chars)
        return out

    def removed_lines():
        out = ["Registros eliminados antes del cribado:"]
        out.append(f"Duplicados (n = {duplicates})")
        if auto_removed is not None:
            out.append(f"Excluidos por automatización (n = {auto_removed})")
        if other_removed is not None:
            out.append(f"Otros motivos (n = {other_removed})")
        return out

    y = 54
    parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="HEIGHT" viewBox="0 0 {W} HEIGHT" font-family="Helvetica, Arial, sans-serif">')
    parts.append('<text x="20" y="28" font-size="15" font-weight="800" fill="#111">Diagrama de flujo PRISMA 2020</text>')

    # Identification
    id_y = y
    h1 = box(lx, y, lw, lines_id(), fill="#eef0fb", stroke="#c5cdf0", bold_first=True)
    box(rx, y, rw, removed_lines(), fill="#f6f6f8", stroke="#d4d4dc", bold_first=True)
    harrow(y + h1 / 2, lx + lw, rx)
    y += h1 + gap

    # Screening: screened -> excluded
    scr_y = y
    h2 = box(lx, y, lw, [f"Registros cribados (n = {_n(screened)})"], bold_first=True)
    varrow(lx + lw / 2, id_y + h1, y)
    if excluded_screen is not None:
        box(rx, y, rw, [f"Registros excluidos (n = {excluded_screen})"], fill="#f6f6f8", stroke="#d4d4dc", bold_first=True)
        harrow(y + h2 / 2, lx + lw, rx)
    y += h2 + gap

    # Reports sought -> not retrieved
    h3 = box(lx, y, lw, [f"Informes buscados para recuperación (n = {_n(sought)})"], bold_first=True)
    varrow(lx + lw / 2, scr_y + h2, y)
    if not_retrieved is not None:
        box(rx, y, rw, [f"Informes no recuperados (n = {not_retrieved})"], fill="#f6f6f8", stroke="#d4d4dc", bold_first=True)
        harrow(y + h3 / 2, lx + lw, rx)
    sought_y = y
    y += h3 + gap

    # Reports assessed -> excluded with reasons
    h4 = box(lx, y, lw, [f"Informes evaluados para elegibilidad (n = {_n(assessed)})"], bold_first=True)
    varrow(lx + lw / 2, sought_y + h3, y)
    if fulltext_excluded is not None or reasons:
        rl = [f"Informes excluidos (n = {_n(fulltext_excluded)}):"] + reasons
        box(rx, y, rw, rl, fill="#f6f6f8", stroke="#d4d4dc", bold_first=True)
        harrow(y + h4 / 2, lx + lw, rx)
    ass_y = y
    y += h4 + gap

    # Included
    inc_lines = [f"Estudios incluidos en la revisión (n = {_n(included)})"]
    if included_meta is not None:
        inc_lines.append(f"Incluidos en el meta-análisis (n = {included_meta})")
    h5 = box(lx, y, lw, inc_lines, fill="#def7e8", stroke="#bce9cf", bold_first=True)
    varrow(lx + lw / 2, ass_y + h4, y)
    y += h5 + 24

    # Section bands (vertical labels)
    for label, top, bottom in [("Identificación", id_y, scr_y), ("Cribado", scr_y, ass_y + h4), ("Incluidos", ass_y + h4 + gap - 8, y)]:
        mid = (top + bottom) / 2
        parts.append(f'<text x="22" y="{mid:.0f}" font-size="11" font-weight="700" fill="#9a9aa4" transform="rotate(-90 22 {mid:.0f})" text-anchor="middle" letter-spacing="1">{label.upper()}</text>')

    parts.append("</svg>")
    return "".join(parts).replace("HEIGHT", str(int(y)))


def _n(v) -> str:
    return "—" if v is None else str(v)


def _esc(text: object) -> str:
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
