"""Manuscript drafting: turn the actual analysis into a publishable draft.

Given the research question, the (optional) protocol and the *real* numbers from
the meta-analysis, drafts manuscript sections. To stay fast and reliable, the AI
works one section at a time (a full 8-section draft in a single call is slow and
times out). A deterministic local fallback writes correct sections — notably a
Results paragraph straight from the data — instantly and offline.

The AI is always told to use only the verified statistics provided, never to
invent numbers or references.
"""
from __future__ import annotations

import os

from .ai import ai_available, run_claude_json

SECTIONS = ["title", "abstract", "introduction", "methods", "results", "discussion", "limitations", "conclusion"]

SECTION_GUIDE = {
    "title": "a concise, informative title for this systematic review and meta-analysis",
    "abstract": "a structured abstract (Background, Methods, Results, Conclusion), about 250 words",
    "introduction": "the Introduction: background, the knowledge gap, and the objective",
    "methods": "the Methods: eligibility, search, data extraction, and the exact synthesis approach used",
    "results": "the Results, reporting the pooled estimate, confidence interval, p-value and heterogeneity EXACTLY as provided",
    "discussion": "the Discussion: interpret the findings in context, using [cita] for any external claim",
    "limitations": "the Limitations of this review and analysis",
    "conclusion": "a short Conclusion grounded strictly in the pooled result",
}


def _fmt(x, dp=2):
    return "NA" if x is None else f"{x:.{dp}f}"


def facts_summary(result: dict) -> str:
    """A compact, verified factual brief the writer must ground on."""
    p, h = result["pooled"], result["heterogeneity"]
    m = result["measure"]
    side = {"left": "izquierdo", "right": "derecho"}
    lines = [
        f"Medida de efecto: {result.get('measure_label', m)} ({m}).",
        f"Número de estudios (k): {result['k']}.",
        f"Modelo: {'efectos aleatorios' if result['model'] == 'random' else 'efecto fijo'}"
        + (f", estimador de τ² {result['tau2_method']}" if result["model"] == "random" else "")
        + (", ajuste de Knapp-Hartung" if result.get("knapp_hartung") else "") + ".",
        f"{m} combinado: {_fmt(p['estimate'])} (IC 95% {_fmt(p['ci_low'])} a {_fmt(p['ci_high'])}), p = {_fmt(p['p_value'], 4)}.",
    ]
    if p.get("pi_low") is not None:
        lines.append(f"Intervalo de predicción 95%: {_fmt(p['pi_low'])} a {_fmt(p['pi_high'])}.")
    lines.append(
        f"Heterogeneidad: I² = {_fmt(h['i2'], 0)}%, τ² = {_fmt(h['tau2'], 4)}, "
        f"Q = {_fmt(h['q'])} (gl = {h['q_df']}, p = {_fmt(h['q_p'], 3)})."
    )
    if result.get("egger"):
        lines.append(f"Prueba de Egger (efectos de estudios pequeños): p = {_fmt(result['egger']['p_value'], 3)}.")
    if result.get("trim_fill") and result["trim_fill"]["k0"] > 0:
        t = result["trim_fill"]
        lines.append(f"Trim-and-fill imputó {t['k0']} estudio(s) al lado {side.get(t['side'], t['side'])}; estimación ajustada {_fmt(t['adjusted_estimate'])}.")
    if result.get("subgroups"):
        s = result["subgroups"]
        groups = "; ".join(f"{g['subgroup']}: {_fmt(g['estimate'])} (k={g['k']})" for g in s["groups"])
        lines.append(f"Subgrupos [{groups}]; prueba entre subgrupos p = {_fmt(s['p_value'], 3)}.")
    labels = ", ".join(s["label"] for s in result.get("studies", []))
    if labels:
        lines.append(f"Estudios incluidos: {labels}.")
    return "\n".join(lines)


def _proto_brief(protocol: dict | None) -> str:
    if not protocol:
        return ""
    crit = "; ".join(protocol.get("inclusion_criteria", [])[:4])
    return (f"\nProtocol objective: {protocol.get('objective','')}\n"
            f"Key inclusion criteria: {crit}\n"
            f"Search strategy: {protocol.get('search_pubmed','')}\n")


def _build_section_prompt(question: str, protocol: dict | None, result: dict, section: str) -> str:
    return (
        "You are an experienced scientific medical writer drafting a systematic "
        "review and meta-analysis manuscript for a peer-reviewed journal.\n\n"
        f'Research question: "{question}"\n'
        f"{_proto_brief(protocol)}\n"
        "VERIFIED STATISTICS — use ONLY these numbers, do NOT invent other figures, "
        "studies or references (use [cita] as a placeholder for any external claim):\n"
        f"{facts_summary(result)}\n\n"
        f"Write ONLY {SECTION_GUIDE[section]}. Respond in the SAME language as the "
        'research question. Return ONLY a JSON object: {"text":"..."} (Markdown allowed).'
    )


def _local(question: str, result: dict) -> dict:
    p, h = result["pooled"], result["heterogeneity"]
    m = result["measure"]
    model = result["model"] + ("-effects" if result["model"] == "random" else "-effect")
    sig = (p["ci_low"] > 1 or p["ci_high"] < 1) if result["log_scale"] else (p["ci_low"] > 0 or p["ci_high"] < 0)
    results = (
        f"Se incluyeron {result['k']} estudios. El {result.get('measure_label', m).lower()} combinado "
        f"({model}) fue {_fmt(p['estimate'])} (IC 95% {_fmt(p['ci_low'])}–{_fmt(p['ci_high'])}; "
        f"p = {_fmt(p['p_value'], 4)}), lo que "
        + ("indica un efecto estadísticamente significativo. " if sig else "no alcanzó significación estadística. ")
        + f"La heterogeneidad entre estudios fue I² = {_fmt(h['i2'], 0)}% "
        f"(τ² = {_fmt(h['tau2'], 4)}; Q = {_fmt(h['q'])}, gl = {h['q_df']}, p = {_fmt(h['q_p'], 3)})."
    )
    if p.get("pi_low") is not None:
        results += f" El intervalo de predicción del 95% fue {_fmt(p['pi_low'])}–{_fmt(p['pi_high'])}."
    if result.get("subgroups"):
        s = result["subgroups"]
        results += (f" La prueba entre subgrupos fue p = {_fmt(s['p_value'], 3)}.")
    methods = (
        f"Se combinaron los tamaños de efecto mediante un modelo de {model} "
        + (f"con estimador {result['tau2_method']} de τ²" if result["model"] == "random" else "")
        + (" y ajuste de Knapp-Hartung" if result.get("knapp_hartung") else "")
        + ". Se cuantificó la heterogeneidad con I², τ² y la Q de Cochran. "
        "Se evaluó el sesgo de publicación mediante el funnel plot, la prueba de Egger y trim-and-fill."
    )
    return {
        "title": f"Revisión sistemática y meta-análisis: {question.strip().rstrip('?').strip()}",
        "abstract": f"**Antecedentes.** [completar]. **Métodos.** {methods} **Resultados.** {results} **Conclusión.** [completar].",
        "introduction": "[Redacta aquí los antecedentes, la brecha de conocimiento y el objetivo de la revisión.]",
        "methods": methods,
        "results": results,
        "discussion": "[Interpreta los hallazgos a la luz de la literatura previa; usa [cita] para afirmaciones externas.]",
        "limitations": "Limitaciones posibles: heterogeneidad entre estudios, número limitado de estudios y riesgo de sesgo de publicación.",
        "conclusion": "[Resume la conclusión principal basada en el efecto combinado observado.]",
    }


def generate_section(question: str, result: dict, section: str, *, protocol: dict | None = None, mode: str = "auto") -> dict:
    """Draft a single manuscript section."""
    question = (question or "").strip()
    if section not in SECTIONS:
        raise ValueError(f"Sección desconocida: {section}")
    if not question:
        raise ValueError("Falta la pregunta de investigación.")
    if not result or "pooled" not in result:
        raise ValueError("Hace falta un resultado de meta-análisis.")

    env_mode = os.environ.get("METAFORGE_AI", "auto").lower()
    want_ai = mode != "local" and env_mode != "off" and (mode == "ai" or ai_available())
    if want_ai:
        try:
            obj = run_claude_json(_build_section_prompt(question, protocol, result, section), timeout=90)
            text = str(obj.get("text") or "").strip()
            if not text:
                raise RuntimeError("empty section from AI")
            return {"section": section, "source": "ai", "text": text}
        except Exception as exc:  # noqa: BLE001
            if mode == "ai":
                raise ValueError(f"No se pudo redactar la sección con IA: {exc}") from exc
            return {"section": section, "source": "local", "text": _local(question, result)[section], "ai_error": str(exc)}
    return {"section": section, "source": "local", "text": _local(question, result)[section]}


def generate_manuscript(question: str, result: dict, *, protocol: dict | None = None, mode: str = "auto") -> dict:
    """Draft the whole manuscript. AI mode drafts section by section (slower but
    reliable); local mode is instant. The UI prefers per-section generation."""
    question = (question or "").strip()
    if not question:
        raise ValueError("Falta la pregunta de investigación.")
    if not result or "pooled" not in result:
        raise ValueError("Hace falta un resultado de meta-análisis para redactar el manuscrito.")

    if mode == "local" or not ai_available() or os.environ.get("METAFORGE_AI", "auto").lower() == "off":
        return {"source": "local", "sections": _local(question, result), "facts": facts_summary(result)}

    sections, any_ai = {}, False
    for sec in SECTIONS:
        out = generate_section(question, result, sec, protocol=protocol, mode="auto")
        sections[sec] = out["text"]
        any_ai = any_ai or out["source"] == "ai"
    return {"source": "ai" if any_ai else "local", "sections": sections, "facts": facts_summary(result)}
