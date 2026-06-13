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


def fetch_fulltext(record: dict, *, timeout: int = 30) -> str | None:
    pmcid = record.get("pmcid")
    if not pmcid:
        return None
    url = FULLTEXT.format(id=pmcid)
    try:
        req = urllib.request.Request(url, headers=_UA)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            xml = resp.read().decode("utf-8", "ignore")
    except Exception:  # noqa: BLE001 — not OA / not retrievable
        return None
    text = re.sub(r"<[^>]+>", " ", xml)        # strip JATS tags
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def _label(record: dict) -> str:
    first = (record.get("authors") or "").split(",")[0].strip() or "Estudio"
    return f"{first} {record.get('year', '')}".strip()


def _build_prompt(text: str, measure: str, outcome: str, fields: list[str]) -> str:
    return (
        "Eres un revisor experto extrayendo datos para un meta-análisis. A partir del "
        "texto del artículo, extrae ÚNICAMENTE los números necesarios para calcular el "
        f"efecto «{measure}» para el desenlace «{outcome or 'el desenlace principal'}». "
        "No inventes valores: si un dato no aparece con claridad, ponlo en null.\n\n"
        f"Campos a extraer (numéricos): {', '.join(fields)}.\n"
        "Para tablas 2x2: a=eventos en el grupo de intervención/expuesto, b=no eventos en "
        "ese grupo, c=eventos en control/no expuesto, d=no eventos en control.\n\n"
        f"TEXTO DEL ARTÍCULO (puede estar truncado):\n{text[:14000]}\n\n"
        "Devuelve SOLO un objeto JSON (sin markdown) con esta forma:\n"
        '{"found": true|false, "fields": {' + ", ".join(f'"{f}": <número|null>' for f in fields) +
        '}, "quote": "frase o celda exacta de donde sale el dato", "note": "aclaración breve"}'
    )


def extract_data(record: dict, *, measure: str = "OR", outcome: str = "", mode: str = "auto") -> dict:
    measure = (measure or "OR").upper()
    fields = fields_for(measure)
    full = fetch_fulltext(record)
    source_text = full or record.get("abstract", "")
    base = {"study_label": _label(record), "effect_measure": measure,
            "source": "fulltext" if full else "abstract", "doi": record.get("doi"),
            "fields": {f: None for f in fields}, "found": False, "quote": "", "note": ""}

    if not source_text:
        base["note"] = "Sin texto disponible (no es de acceso abierto)."
        return base
    if not (mode != "local" and (mode == "ai" or ai_available())):
        base["note"] = "Extracción manual: la IA no está disponible."
        return base
    try:
        obj = run_claude_json(_build_prompt(source_text, measure, outcome, fields), timeout=120)
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
