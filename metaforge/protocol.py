"""Study-protocol generation: turn a research question into a review protocol.

Produces the scaffolding a systematic review/meta-analysis needs before data
collection: objective, eligibility criteria, a database search strategy, and the
data-extraction fields that match the chosen effect measure.
"""
from __future__ import annotations

import os

from .ai import ai_available, run_claude_json

# Extraction fields keyed by effect measure — these map onto MetaForge's CSV columns.
_EXTRACTION_BY_MEASURE = {
    "OR": ["study_label", "year", "a_events", "b_non_events", "c_events", "d_non_events"],
    "RR": ["study_label", "year", "a_events", "b_non_events", "c_events", "d_non_events"],
    "RD": ["study_label", "year", "a_events", "b_non_events", "c_events", "d_non_events"],
    "HR": ["study_label", "year", "effect_value", "ci_lower_95", "ci_upper_95"],
    "IRR": ["study_label", "year", "events_intervention", "time_intervention", "events_control", "time_control"],
    "MD": ["study_label", "year", "n_intervention", "mean_intervention", "sd_intervention", "n_control", "mean_control", "sd_control"],
    "SMD": ["study_label", "year", "n_intervention", "mean_intervention", "sd_intervention", "n_control", "mean_control", "sd_control"],
    "PLOGIT": ["study_label", "year", "events", "n_total"],
    "ZCOR": ["study_label", "year", "r", "n_total"],
    "GEN": ["study_label", "year", "yi", "se"],
}


def _extraction_fields(measure: str) -> list[str]:
    return _EXTRACTION_BY_MEASURE.get((measure or "GEN").upper(), _EXTRACTION_BY_MEASURE["GEN"])


def _build_prompt(question: str, measure: str) -> str:
    return (
        "You are a Cochrane-trained systematic-review methodologist. Draft the "
        "core of a review protocol for the research question below. Be specific "
        "and practical.\n\n"
        f'Research question: "{question}"\n'
        f"Planned effect measure for synthesis: {measure}\n\n"
        "Return ONLY a JSON object (no prose, no fences), responding in the SAME "
        "language as the question, with this shape:\n"
        '{"objective":"one-sentence objective",'
        '"inclusion_criteria":["...","..."],'
        '"exclusion_criteria":["...","..."],'
        '"study_designs":["..."],'
        '"keywords":["...","..."],'
        '"search_pubmed":"a ready-to-paste PubMed boolean query with MeSH terms",'
        '"outcomes":["primary outcome","secondary outcome"],'
        '"prisma_note":"one sentence on screening/flow"}'
    )


def _clean(obj: dict, measure: str) -> dict:
    def lst(key):
        v = obj.get(key)
        return [str(x).strip() for x in v if str(x).strip()] if isinstance(v, list) else []
    return {
        "objective": str(obj.get("objective") or "").strip(),
        "inclusion_criteria": lst("inclusion_criteria"),
        "exclusion_criteria": lst("exclusion_criteria"),
        "study_designs": lst("study_designs"),
        "keywords": lst("keywords"),
        "search_pubmed": str(obj.get("search_pubmed") or "").strip(),
        "outcomes": lst("outcomes"),
        "prisma_note": str(obj.get("prisma_note") or "").strip(),
        "extraction_fields": _extraction_fields(measure),
    }


def _local(question: str, measure: str) -> dict:
    q = question.strip()
    return {
        "objective": f"Sintetizar la evidencia disponible para responder: {q}",
        "inclusion_criteria": [
            "Estudios que aborden la población y el desenlace de la pregunta",
            "Diseños con grupo de comparación cuando aplique",
            "Datos suficientes para calcular el tamaño del efecto",
            "Texto completo disponible",
        ],
        "exclusion_criteria": [
            "Resúmenes de congreso sin datos completos",
            "Estudios duplicados o con datos no extraíbles",
            "Población o desenlace no relevantes",
        ],
        "study_designs": ["Ensayos aleatorizados", "Estudios de cohorte", "Casos y controles"],
        "keywords": [w for w in q.replace("¿", "").replace("?", "").split() if len(w) > 4][:8],
        "search_pubmed": "(\"<concepto población>\"[Mesh]) AND (\"<concepto intervención/exposición>\"[Mesh]) AND (\"<desenlace>\"[Mesh])",
        "outcomes": ["Desenlace principal de la pregunta", "Desenlaces secundarios relevantes"],
        "prisma_note": "Cribado por título/resumen y luego texto completo por dos revisores; registrar el flujo PRISMA.",
        "extraction_fields": _extraction_fields(measure),
    }


def generate_protocol(question: str, *, measure: str = "GEN", mode: str = "auto") -> dict:
    question = (question or "").strip()
    if not question:
        raise ValueError("Falta la pregunta de investigación para generar el protocolo.")
    measure = (measure or "GEN").upper()

    env_mode = os.environ.get("METAFORGE_AI", "auto").lower()
    want_ai = mode != "local" and env_mode != "off" and (mode == "ai" or ai_available())
    if want_ai:
        try:
            obj = run_claude_json(_build_prompt(question, measure))
            return {"source": "ai", "measure": measure, "protocol": _clean(obj, measure)}
        except Exception as exc:  # noqa: BLE001
            if mode == "ai":
                raise ValueError(f"No se pudo generar el protocolo con IA: {exc}") from exc
            return {"source": "local", "measure": measure, "protocol": _local(question, measure),
                    "ai_error": str(exc)}
    return {"source": "local", "measure": measure, "protocol": _local(question, measure)}
