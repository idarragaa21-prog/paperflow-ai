"""Risk-of-bias assessment: domain definitions and a traffic-light summary SVG.

Supports RoB 2 (randomised trials) and ROBINS-I (non-randomised studies). A
per-study, per-domain matrix of judgements renders as the familiar traffic-light
plot used in systematic reviews.
"""
from __future__ import annotations

# domain code -> human label
TOOLS = {
    "rob2": {
        "name": "RoB 2 (ensayos aleatorizados)",
        "domains": {
            "D1": "Proceso de aleatorización",
            "D2": "Desviaciones de la intervención prevista",
            "D3": "Datos de desenlace faltantes",
            "D4": "Medición del desenlace",
            "D5": "Selección del resultado informado",
        },
    },
    "robins-i": {
        "name": "ROBINS-I (estudios no aleatorizados)",
        "domains": {
            "D1": "Confusión",
            "D2": "Selección de participantes",
            "D3": "Clasificación de intervenciones",
            "D4": "Desviaciones de la intervención",
            "D5": "Datos faltantes",
            "D6": "Medición de desenlaces",
            "D7": "Selección del resultado informado",
        },
    },
}

_RATING = {
    "low": ("#2e7d32", "+", "Bajo"),
    "some": ("#f9a825", "?", "Dudas"),
    "high": ("#c62828", "−", "Alto"),
    "critical": ("#7f1d1d", "×", "Crítico"),
    "na": ("#bdbdbd", "", "Sin info."),
}


def domains_for(tool: str) -> dict:
    return TOOLS.get(tool, TOOLS["rob2"])["domains"]


def _overall(row: dict, codes: list[str]) -> str:
    order = ["na", "low", "some", "high", "critical"]
    worst = "na"
    for c in codes:
        r = row.get(c, "na")
        if order.index(r) > order.index(worst):
            worst = r
    return worst


def rob_summary_svg(studies: list[str], ratings: dict, *, tool: str = "rob2") -> str:
    domains = domains_for(tool)
    codes = list(domains.keys())
    cols = codes + ["overall"]
    col_labels = codes + ["Global"]

    left = 220
    cell = 40
    top = 96
    width = left + len(cols) * cell + 20
    height = top + len(studies) * cell + 110

    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" font-family="Helvetica, Arial, sans-serif">',
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        f'<text x="20" y="26" font-size="14" font-weight="700" fill="#111">Riesgo de sesgo — {TOOLS.get(tool, TOOLS["rob2"])["name"]}</text>',
    ]
    # column headers
    for j, lbl in enumerate(col_labels):
        cx = left + j * cell + cell / 2
        p.append(f'<text x="{cx:.0f}" y="{top - 10}" font-size="11" font-weight="700" fill="#444" text-anchor="middle">{lbl}</text>')
    # rows
    for i, study in enumerate(studies):
        cy = top + i * cell
        p.append(f'<text x="{left - 12}" y="{cy + cell / 2 + 4:.0f}" font-size="11.5" fill="#222" text-anchor="end">{_esc(study)[:34]}</text>')
        row = ratings.get(study, {})
        for j, code in enumerate(cols):
            rating = _overall(row, codes) if code == "overall" else row.get(code, "na")
            color, sym, _ = _RATING.get(rating, _RATING["na"])
            cx = left + j * cell + cell / 2
            p.append(f'<circle cx="{cx:.0f}" cy="{cy + cell / 2:.0f}" r="13" fill="{color}"/>')
            if sym:
                p.append(f'<text x="{cx:.0f}" y="{cy + cell / 2 + 5:.0f}" font-size="14" font-weight="700" fill="#fff" text-anchor="middle">{sym}</text>')
    # legend
    ly = top + len(studies) * cell + 28
    p.append(f'<text x="20" y="{ly}" font-size="11" font-weight="700" fill="#444">Leyenda:</text>')
    lx = 90
    for key in ("low", "some", "high", "na"):
        color, sym, label = _RATING[key]
        p.append(f'<circle cx="{lx}" cy="{ly - 4:.0f}" r="9" fill="{color}"/>')
        if sym:
            p.append(f'<text x="{lx}" y="{ly:.0f}" font-size="10" font-weight="700" fill="#fff" text-anchor="middle">{sym}</text>')
        p.append(f'<text x="{lx + 14}" y="{ly:.0f}" font-size="10.5" fill="#444">{label}</text>')
        lx += 36 + len(label) * 6
    # domain key
    dy = ly + 22
    for code, name in domains.items():
        p.append(f'<text x="20" y="{dy}" font-size="10" fill="#777">{code} = {_esc(name)}</text>')
        dy += 15
    p.append("</svg>")
    return "".join(p)


def _esc(text: object) -> str:
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
