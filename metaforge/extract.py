"""AI-assisted data extraction from open-access full text.

For an included open-access record, fetches the JATS full text from Europe PMC
and asks the AI to pull out exactly the numbers needed to compute the chosen
effect measure for a given outcome (2x2 cells, arm means/SDs, or effect+CI),
together with the supporting quote. Falls back to the abstract when no full text
is available. Every extraction must be checked against the source by a human.
"""
from __future__ import annotations

import re
import urllib.request
import xml.etree.ElementTree as ET

from .ai import ai_available, run_claude_json

_UA = {"User-Agent": "MetaForge/1.0 (systematic-review tool)"}
FULLTEXT = "https://www.ebi.ac.uk/europepmc/webservices/rest/{id}/fullTextXML"

FIELDS_BY_MEASURE = {
    "OR": ["a_events", "b_non_events", "c_events", "d_non_events"],
    "RR": ["a_events", "b_non_events", "c_events", "d_non_events"],
    "RD": ["a_events", "b_non_events", "c_events", "d_non_events"],
    "HR": ["effect_value", "ci_lower_95", "ci_upper_95"],
    "IRR": ["events_intervention", "time_intervention", "events_control", "time_control"],
    "MD": ["n_intervention", "mean_intervention", "sd_intervention", "n_control", "mean_control", "sd_control"],
    "SMD": ["n_intervention", "mean_intervention", "sd_intervention", "n_control", "mean_control", "sd_control"],
    "PLOGIT": ["events", "n_total"],
    "ZCOR": ["r", "n_total"],
    "GEN": ["yi", "se"],
}


def fields_for(measure: str) -> list[str]:
    return FIELDS_BY_MEASURE.get((measure or "GEN").upper(), FIELDS_BY_MEASURE["GEN"])


def _fetch_xml(record: dict, *, timeout: int = 30) -> str | None:
    pmcid = record.get("pmcid")
    if not pmcid:
        return None
    try:
        req = urllib.request.Request(FULLTEXT.format(id=pmcid), headers=_UA)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", "ignore")
    except Exception:  # noqa: BLE001 — not OA / not retrievable
        return None


def _narrative(xml: str) -> str:
    text = re.sub(r"<[^>]+>", " ", xml)
    return re.sub(r"\s+", " ", text).strip()


def _txt(el) -> str:
    return " ".join("".join(el.itertext()).split())


def extract_tables(xml: str) -> list[str]:
    """Parse JATS/HTML tables into readable pipe-delimited grids with captions."""
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return []
    for el in root.iter():
        el.tag = el.tag.rpartition("}")[2]  # drop namespaces

    out, seen = [], set()
    for wrap in root.iter():
        if wrap.tag not in ("table-wrap", "table"):
            continue
        if id(wrap) in seen:
            continue
        if wrap.tag == "table-wrap":
            caption = " ".join(_txt(e) for e in list(wrap.findall("label")) + list(wrap.findall("caption")))
            tables = list(wrap.iter("table"))
            for t in tables:
                seen.add(id(t))
        else:
            caption, tables = "", [wrap]
        grids = []
        for table in tables:
            rows = []
            for tr in table.iter("tr"):
                cells = [_txt(c) for c in tr if c.tag in ("td", "th")]
                if any(cells):
                    rows.append(" | ".join(cells))
            if rows:
                grids.append("\n".join(rows))
        if grids:
            out.append((caption.strip() + "\n" if caption.strip() else "") + "\n".join(grids))
    return out


def fetch_fulltext(record: dict, *, timeout: int = 30) -> str | None:
    """Narrative full text (tables stripped) — used by full-text screening."""
    xml = _fetch_xml(record, timeout=timeout)
    return _narrative(xml) or None if xml else None


def fetch_fulltext_parts(record: dict, *, timeout: int = 30) -> tuple[str, list[str]]:
    """(narrative text, list of table grids) from the open-access full text."""
    xml = _fetch_xml(record, timeout=timeout)
    if not xml:
        return "", []
    return _narrative(xml), extract_tables(xml)


def _label(record: dict) -> str:
    first = (record.get("authors") or "").split(",")[0].strip() or "Estudio"
    return f"{first} {record.get('year', '')}".strip()


def _build_prompt(tables: list[str], narrative: str, measure: str, outcome: str, fields: list[str]) -> str:
    tables_block = "\n\n".join(f"[TABLA {i + 1}]\n{t}" for i, t in enumerate(tables))[:9000]
    return (
        "Eres un revisor experto extrayendo datos para un meta-análisis. Extrae "
        "ÚNICAMENTE los números necesarios para calcular el efecto "
        f"«{measure}» para el desenlace «{outcome or 'el desenlace principal'}». "
        "Los datos suelen estar en las TABLAS: revísalas primero. No inventes "
        "valores: si un dato no aparece con claridad, ponlo en null.\n\n"
        f"Campos a extraer (numéricos): {', '.join(fields)}.\n"
        "Para tablas 2x2: a=eventos en el grupo de intervención/expuesto, b=no eventos en "
        "ese grupo, c=eventos en control/no expuesto, d=no eventos en control.\n\n"
        f"=== TABLAS DEL ARTÍCULO ===\n{tables_block or '(sin tablas extraíbles)'}\n\n"
        f"=== TEXTO (puede estar truncado) ===\n{narrative[:8000]}\n\n"
        "Devuelve SOLO un objeto JSON (sin markdown) con esta forma:\n"
        '{"found": true|false, "fields": {' + ", ".join(f'"{f}": <número|null>' for f in fields) +
        '}, "quote": "celda o frase exacta de donde sale el dato (indica la tabla)", "note": "aclaración breve"}'
    )


def extract_data(record: dict, *, measure: str = "OR", outcome: str = "", mode: str = "auto") -> dict:
    measure = (measure or "OR").upper()
    fields = fields_for(measure)
    narrative, tables = fetch_fulltext_parts(record)
    has_full = bool(narrative or tables)
    if not narrative and not tables:
        narrative = record.get("abstract", "")
    base = {"study_label": _label(record), "effect_measure": measure,
            "source": "fulltext" if has_full else "abstract", "n_tables": len(tables),
            "doi": record.get("doi"), "fields": {f: None for f in fields},
            "found": False, "quote": "", "note": ""}

    if not narrative and not tables:
        base["note"] = "Sin texto disponible (no es de acceso abierto)."
        return base
    if not (mode != "local" and (mode == "ai" or ai_available())):
        base["note"] = "Extracción manual: la IA no está disponible."
        return base
    try:
        obj = run_claude_json(_build_prompt(tables, narrative, measure, outcome, fields), timeout=120)
    except Exception as exc:  # noqa: BLE001
        base["note"] = f"No se pudo extraer con IA: {exc}"
        return base

    raw = obj.get("fields", {}) if isinstance(obj.get("fields"), dict) else {}
    cleaned = {}
    for f in fields:
        v = raw.get(f)
        try:
            cleaned[f] = float(v) if v not in (None, "", "null") else None
        except (TypeError, ValueError):
            cleaned[f] = None
    base.update({
        "fields": cleaned,
        "found": bool(obj.get("found")) and any(v is not None for v in cleaned.values()),
        "quote": str(obj.get("quote") or "")[:400],
        "note": str(obj.get("note") or ""),
    })
    return base


def extract_to_csv_row(extraction: dict) -> str:
    """One CSV line: study_label,effect_measure,<fields…> (blank where missing)."""
    fields = list(extraction["fields"].keys())
    vals = ["" if extraction["fields"][f] is None else _fmt(extraction["fields"][f]) for f in fields]
    label = extraction["study_label"].replace('"', "'")
    return f'"{label}",{extraction["effect_measure"]},' + ",".join(vals)


def _fmt(v: float) -> str:
    return str(int(v)) if float(v).is_integer() else str(v)
