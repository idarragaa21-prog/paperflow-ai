from __future__ import annotations

import re
from typing import Any


RE_CITE = re.compile(r"PMID:\d+|doi:[^\s\)]+|DOI:[^\s\)]+")
RE_BULLET = re.compile(r"^\s*(-|\d+\.)\s+")


def _core_labels(core: list[dict[str, Any]], *, max_n: int = 6) -> list[str]:
    out: list[str] = []
    for it in core or []:
        pmid = str(it.get("pmid") or "").strip()
        doi = str(it.get("doi") or "").strip()
        year = it.get("pub_year")
        pts = it.get("publication_types") or []
        low = " ".join([str(x).lower() for x in pts])
        if "practice guideline" in low or "guideline" in low:
            typ = "Guía"
        elif "systematic review" in low:
            typ = "Revisión sistemática"
        elif "meta-analysis" in low or "meta analysis" in low:
            typ = "Meta-análisis"
        elif "randomized controlled trial" in low:
            typ = "ECA"
        elif "review" in low:
            typ = "Revisión"
        else:
            typ = "Estudio"

        ident = f"PMID:{pmid}" if pmid else (f"doi:{doi}" if doi else "")
        if not ident:
            continue
        tail = []
        if year:
            tail.append(str(year))
        if typ:
            tail.append(typ)
        out.append(ident + (f" ({', '.join(tail)})" if tail else ""))
        if len(out) >= max_n:
            break
    return out


def enforce_claim_traceability(
    md: str,
    *,
    core_papers: list[dict[str, Any]] | None,
) -> tuple[str, list[str]]:
    """Best-effort claim-level traceability gate.

    For important bullet lines, if no PMID/DOI is present, append a conservative
    marker rather than fabricating citations.

    Also inject a small "Evidencia central" line near the end of the section
    when the section lacks visible citations.
    """

    if not md:
        return md, []

    warnings: list[str] = []

    core_labels = _core_labels(core_papers or [], max_n=8)

    lines = md.splitlines()
    out_lines: list[str] = []

    for ln in lines:
        if RE_BULLET.match(ln) and not RE_CITE.search(ln):
            # If this is a strong claim-like line, require explicit traceability.
            # We do not attach specific papers; we mark evidence insufficient for that claim.
            low = ln.lower()
            if any(k in low for k in ["recom", "indica", "trat", "diagn", "pron", "complic", "return", "seguim", "evitar", "primera línea", "contraind"]):
                ln = ln.rstrip() + " (Evidencia insuficiente para esta afirmación; ver Mapa de evidencia)"
                warnings.append("Added claim-level evidence-insufficient marker")
        out_lines.append(ln)

    txt = "\n".join(out_lines)

    # If the section has no citations at all, add a central evidence line (non-committal)
    if core_labels and not RE_CITE.search(txt):
        txt = txt.rstrip() + "\n\nEvidencia central (artículos): " + "; ".join(core_labels[:8]) + "\n"
        warnings.append("Inserted evidence central line (no citations detected)")

    return txt, warnings
