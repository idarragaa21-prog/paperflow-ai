"""PRISMA 2020 study-flow diagram as a standalone SVG.

Renders either the single-column flow (databases & registers) or the full
two-column 2020 flow (databases/registers + other methods: citation searching,
websites, organisations) when "other methods" counts are supplied. Boxes are
word-wrapped; exclusion reasons are itemised; missing counts are derived where
possible.
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
    if not reasons:
        return []
    raw = [r.strip() for chunk in str(reasons).split("\n") for r in chunk.split(";")]
    return [f"• {r}" for r in raw if r]


def _n(v) -> str:
    return "—" if v is None else str(v)


def _esc(text: object) -> str:
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


_LH, _VPAD, _PADX = 15, 9, 12


class _Canvas:
    def __init__(self):
        self.parts: list[str] = []

    def box(self, x, y, w, lines, *, fill="#eef0fb", stroke="#c5cdf0", bold_first=False, chars=46):
        wrapped = []
        for i, ln in enumerate(lines):
            wrapped += [(w2, i == 0 and bold_first) for w2 in _wrap(ln, chars)]
        h = len(wrapped) * _LH + 2 * _VPAD
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h:.0f}" rx="9" fill="{fill}" stroke="{stroke}" stroke-width="1.2"/>')
        ty = y + _VPAD + 11
        for text, bold in wrapped:
            weight = "700" if bold else "400"
            self.parts.append(f'<text x="{x + _PADX}" y="{ty:.0f}" font-size="11.5" font-weight="{weight}" fill="#1a1a22">{_esc(text)}</text>')
            ty += _LH
        return h

    def vdown(self, x, y1, y2):
        self.parts.append(f'<line x1="{x}" y1="{y1:.0f}" x2="{x}" y2="{y2:.0f}" stroke="#7a7a85" stroke-width="1.5"/>')
        self.parts.append(f'<path d="M{x - 5},{y2 - 7:.0f} L{x},{y2:.0f} L{x + 5},{y2 - 7:.0f}" fill="#7a7a85"/>')

    def hright(self, y, x1, x2):
        self.parts.append(f'<line x1="{x1}" y1="{y:.0f}" x2="{x2}" y2="{y:.0f}" stroke="#7a7a85" stroke-width="1.5"/>')
        self.parts.append(f'<path d="M{x2 - 7},{y - 5:.0f} L{x2},{y:.0f} L{x2 - 7},{y + 5:.0f}" fill="#7a7a85"/>')

    def elbow(self, x1, y1, x2, y2):
        """Down from (x1,y1) then across to (x2,y2) with an arrowhead at the end."""
        self.parts.append(f'<polyline points="{x1},{y1:.0f} {x1},{y2:.0f} {x2},{y2:.0f}" fill="none" stroke="#7a7a85" stroke-width="1.5"/>')
        self.parts.append(f'<path d="M{x2 - 7},{y2 - 5:.0f} L{x2},{y2:.0f} L{x2 - 7},{y2 + 5:.0f}" fill="#7a7a85"/>' if x2 > x1
                          else f'<path d="M{x2 + 7},{y2 - 5:.0f} L{x2},{y2:.0f} L{x2 + 7},{y2 + 5:.0f}" fill="#7a7a85"/>')

    def text(self, x, y, s, *, size=11, weight="400", fill="#1a1a22", anchor="start", extra=""):
        self.parts.append(f'<text x="{x}" y="{y:.0f}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}" {extra}>{_esc(s)}</text>')

    def svg(self, width, height) -> str:
        head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{int(height)}" '
                f'viewBox="0 0 {width} {int(height)}" font-family="Helvetica, Arial, sans-serif">'
                f'<rect width="{width}" height="{int(height)}" fill="#ffffff"/>')
        return head + "".join(self.parts) + "</svg>"


_GREY = dict(fill="#f6f6f8", stroke="#d4d4dc")
_BLUE = dict(fill="#eef0fb", stroke="#c5cdf0")
_GREEN = dict(fill="#def7e8", stroke="#bce9cf")


def _has_other(counts: dict) -> bool:
    return any(_i(counts, k) for k in ("other_websites", "other_orgs", "other_citation", "other_sought", "other_assessed"))


# --- single column -----------------------------------------------------------
def _single(counts: dict, included_meta: int | None) -> str:
    db = _i(counts, "identified_db", default=0) or 0
    registers = _i(counts, "identified_registers", default=0) or 0
    other = _i(counts, "identified_other", default=0) or 0
    duplicates = _i(counts, "duplicates", default=0) or 0
    auto_removed = _i(counts, "auto_removed")
    other_removed = _i(counts, "other_removed")
    identified = db + registers + other
    removed = duplicates + (auto_removed or 0) + (other_removed or 0)
    screened = _i(counts, "screened", default=(identified - removed if identified else None))
    excluded_screen = _i(counts, "excluded_screen")
    sought = _i(counts, "sought", default=((screened - excluded_screen) if (screened is not None and excluded_screen is not None) else None))
    not_retrieved = _i(counts, "not_retrieved")
    assessed = _i(counts, "assessed", "fulltext_assessed", default=((sought - not_retrieved) if (sought is not None and not_retrieved is not None) else sought))
    fulltext_excluded = _i(counts, "fulltext_excluded")
    included = _i(counts, "included", default=((assessed - fulltext_excluded) if (assessed is not None and fulltext_excluded is not None) else None))
    reasons = _reason_lines(counts.get("exclusion_reasons") or "")

    c = _Canvas()
    c.text(20, 28, "Diagrama de flujo PRISMA 2020", size=15, weight="800", fill="#111")
    lx, lw, rx, rw, gap = 64, 312, 430, 300, 34
    id_lines = ["Registros identificados (n = %d)" % identified,
                "Bases: %d" % db + (" · Registros: %d" % registers if registers else "") + (" · Otras: %d" % other if other else "")]
    removed_lines = ["Registros eliminados antes del cribado:", "Duplicados (n = %d)" % duplicates]
    if auto_removed is not None:
        removed_lines.append("Excluidos por automatización (n = %d)" % auto_removed)
    if other_removed is not None:
        removed_lines.append("Otros motivos (n = %d)" % other_removed)

    y = 54
    id_y = y
    h = c.box(lx, y, lw, id_lines, bold_first=True, **_BLUE)
    c.box(rx, y, rw, removed_lines, bold_first=True, **_GREY)
    c.hright(y + h / 2, lx + lw, rx)
    y += h + gap
    scr_y = y
    h2 = c.box(lx, y, lw, [f"Registros cribados (n = {_n(screened)})"], bold_first=True, **_BLUE)
    c.vdown(lx + lw / 2, id_y + h, y)
    if excluded_screen is not None:
        c.box(rx, y, rw, [f"Registros excluidos (n = {excluded_screen})"], bold_first=True, **_GREY)
        c.hright(y + h2 / 2, lx + lw, rx)
    y += h2 + gap
    h3 = c.box(lx, y, lw, [f"Informes buscados para recuperación (n = {_n(sought)})"], bold_first=True, **_BLUE)
    c.vdown(lx + lw / 2, scr_y + h2, y)
    if not_retrieved is not None:
        c.box(rx, y, rw, [f"Informes no recuperados (n = {not_retrieved})"], bold_first=True, **_GREY)
        c.hright(y + h3 / 2, lx + lw, rx)
    so_y = y
    y += h3 + gap
    h4 = c.box(lx, y, lw, [f"Informes evaluados para elegibilidad (n = {_n(assessed)})"], bold_first=True, **_BLUE)
    c.vdown(lx + lw / 2, so_y + h3, y)
    if fulltext_excluded is not None or reasons:
        c.box(rx, y, rw, [f"Informes excluidos (n = {_n(fulltext_excluded)}):"] + reasons, bold_first=True, **_GREY)
        c.hright(y + h4 / 2, lx + lw, rx)
    as_y = y
    y += h4 + gap
    inc_lines = [f"Estudios incluidos en la revisión (n = {_n(included)})"]
    if included_meta is not None:
        inc_lines.append(f"Incluidos en el meta-análisis (n = {included_meta})")
    h5 = c.box(lx, y, lw, inc_lines, bold_first=True, **_GREEN)
    c.vdown(lx + lw / 2, as_y + h4, y)
    y += h5 + 24

    for label, top, bottom in [("Identificación", id_y, scr_y), ("Cribado", scr_y, as_y), ("Incluidos", as_y + gap, y)]:
        mid = (top + bottom) / 2
        c.text(22, mid, label.upper(), size=11, weight="700", fill="#9a9aa4", anchor="middle",
               extra=f'transform="rotate(-90 22 {mid:.0f})" letter-spacing="1"')
    return c.svg(780, y)


# --- two columns -------------------------------------------------------------
def _two(counts: dict, included_meta: int | None) -> str:
    db = _i(counts, "identified_db", default=0) or 0
    registers = _i(counts, "identified_registers", default=0) or 0
    duplicates = _i(counts, "duplicates", default=0) or 0
    identified = db + registers
    screened = _i(counts, "screened", default=(identified - duplicates if identified else None))
    excluded_screen = _i(counts, "excluded_screen")
    sought = _i(counts, "sought", default=((screened - excluded_screen) if (screened is not None and excluded_screen is not None) else None))
    not_retrieved = _i(counts, "not_retrieved")
    assessed = _i(counts, "assessed", "fulltext_assessed", default=sought)
    fulltext_excluded = _i(counts, "fulltext_excluded")
    reasons = _reason_lines(counts.get("exclusion_reasons") or "")

    o_web = _i(counts, "other_websites", default=0) or 0
    o_org = _i(counts, "other_orgs", default=0) or 0
    o_cit = _i(counts, "other_citation", default=0) or 0
    o_ident = o_web + o_org + o_cit
    o_sought = _i(counts, "other_sought", default=(o_ident or None))
    o_not = _i(counts, "other_not_retrieved")
    o_assessed = _i(counts, "other_assessed", default=o_sought)
    o_excluded = _i(counts, "other_excluded")
    o_reasons = _reason_lines(counts.get("other_reasons") or "")
    included = _i(counts, "included")

    W = 1060
    c = _Canvas()
    c.text(20, 26, "Diagrama de flujo PRISMA 2020", size=15, weight="800", fill="#111")
    # column header bands
    c.parts.append('<rect x="40" y="40" width="486" height="26" rx="6" fill="#e7e9f6"/>')
    c.parts.append('<rect x="556" y="40" width="466" height="26" rx="6" fill="#eef0e8"/>')
    c.text(283, 58, "Identificación vía bases de datos y registros", size="11.5", weight="700", fill="#3a3a55", anchor="middle")
    c.text(789, 58, "Identificación vía otras fuentes", size="11.5", weight="700", fill="#4a5a3a", anchor="middle")

    lx, lw, lex, lew = 56, 300, 372, 154        # left main / exclusion
    rx, rw, rex, rew = 588, 300, 904, 118        # right main / exclusion
    gap = 30
    chars_main = 44

    # left column
    ly = 80
    li_lines = ["Registros identificados (n = %d)" % identified, "Bases: %d · Registros: %d" % (db, registers)]
    lh = c.box(lx, ly, lw, li_lines, bold_first=True, chars=chars_main, **_BLUE)
    c.box(lex, ly, lew, ["Duplicados eliminados antes del cribado (n = %d)" % duplicates], bold_first=False, chars=24, **_GREY)
    c.hright(ly + lh / 2, lx + lw, lex)
    ly2 = ly + lh + gap
    lh2 = c.box(lx, ly2, lw, [f"Registros cribados (n = {_n(screened)})"], bold_first=True, chars=chars_main, **_BLUE)
    c.vdown(lx + lw / 2, ly + lh, ly2)
    if excluded_screen is not None:
        c.box(lex, ly2, lew, [f"Registros excluidos (n = {excluded_screen})"], chars=24, **_GREY)
        c.hright(ly2 + lh2 / 2, lx + lw, lex)
    ly3 = ly2 + lh2 + gap
    lh3 = c.box(lx, ly3, lw, [f"Informes buscados (n = {_n(sought)})"], bold_first=True, chars=chars_main, **_BLUE)
    c.vdown(lx + lw / 2, ly2 + lh2, ly3)
    if not_retrieved is not None:
        c.box(lex, ly3, lew, [f"No recuperados (n = {not_retrieved})"], chars=24, **_GREY)
        c.hright(ly3 + lh3 / 2, lx + lw, lex)
    ly4 = ly3 + lh3 + gap
    lh4 = c.box(lx, ly4, lw, [f"Informes evaluados para elegibilidad (n = {_n(assessed)})"], bold_first=True, chars=chars_main, **_BLUE)
    c.vdown(lx + lw / 2, ly3 + lh3, ly4)
    lex_h = 0
    if fulltext_excluded is not None or reasons:
        lex_h = c.box(lex, ly4, lew, [f"Excluidos (n = {_n(fulltext_excluded)}):"] + reasons, bold_first=True, chars=22, **_GREY)
        c.hright(ly4 + lh4 / 2, lx + lw, lex)
    left_bottom = ly4 + max(lh4, lex_h)

    # right column (other methods)
    ry = 80
    ri_lines = ["Registros identificados de:", "Búsqueda en citas: %d" % o_cit, "Webs: %d · Organizaciones: %d" % (o_web, o_org)]
    rh = c.box(rx, ry, rw, ri_lines, bold_first=True, chars=chars_main, **_BLUE)
    ry2 = ry + rh + gap
    rh2 = c.box(rx, ry2, rw, [f"Informes buscados (n = {_n(o_sought)})"], bold_first=True, chars=chars_main, **_BLUE)
    c.vdown(rx + rw / 2, ry + rh, ry2)
    if o_not is not None:
        c.box(rex, ry2, rew, [f"No recuperados (n = {o_not})"], chars=24, **_GREY)
        c.hright(ry2 + rh2 / 2, rx + rw, rex)
    ry3 = ry2 + rh2 + gap
    rh3 = c.box(rx, ry3, rw, [f"Informes evaluados para elegibilidad (n = {_n(o_assessed)})"], bold_first=True, chars=chars_main, **_BLUE)
    c.vdown(rx + rw / 2, ry2 + rh2, ry3)
    rex_h = 0
    if o_excluded is not None or o_reasons:
        rex_h = c.box(rex, ry3, rew, [f"Excluidos (n = {_n(o_excluded)}):"] + o_reasons, bold_first=True, chars=20, **_GREY)
        c.hright(ry3 + rh3 / 2, rx + rw, rex)
    right_bottom = ry3 + max(rh3, rex_h)

    # included box (shared)
    iy = max(left_bottom, right_bottom) + gap + 6
    ix, iw = 300, 460
    inc_lines = [f"Estudios incluidos en la revisión (n = {_n(included)})"]
    if included_meta is not None:
        inc_lines.append(f"Incluidos en el meta-análisis (n = {included_meta})")
    ih = c.box(ix, iy, iw, inc_lines, bold_first=True, chars=64, **_GREEN)
    c.elbow(lx + lw / 2, ly4 + lh4, ix + 60, iy)             # left main -> included
    c.elbow(rx + rw / 2, ry3 + rh3, ix + iw - 60, iy)        # right main -> included
    return c.svg(W, iy + ih + 24)


def prisma_svg(counts: dict, *, included_meta: int | None = None) -> str:
    counts = counts or {}
    if _has_other(counts):
        return _two(counts, included_meta)
    return _single(counts, included_meta)
