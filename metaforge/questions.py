"""Research-question generation.

Turns a free-text topic (in any language) into specific, developable research
questions, each structured with a framework (PICO/PECO/SPIDER), a suggested
study design and an effect measure that flows straight into MetaForge's
meta-analysis engine. AI via the local Claude CLI, with a deterministic local
fallback.
"""
from __future__ import annotations

import os

from .ai import ai_available, run_claude_json
from .effects import ALL_MEASURES

_MEASURE_HELP = (
    "OR/RR/RD (binary outcomes), HR (time-to-event), IRR (rates), "
    "MD/SMD (continuous outcomes), PLOGIT (single-group proportion/prevalence), "
    "ZCOR (correlation), or GEN (generic, for qualitative/descriptive questions)."
)

_SYSTEM = (
    "You are an expert research methodologist and epidemiologist who helps "
    "researchers turn a vague topic into sharp, answerable, developable research "
    "questions. You avoid generic, unfocused questions; every question names a "
    "population, an intervention/exposure, a comparator (when relevant) and a "
    "concrete, measurable outcome."
)


def _build_prompt(topic: str, n: int) -> str:
    return (
        f"{_SYSTEM}\n\n"
        f'Topic provided by the researcher: "{topic}"\n\n'
        f"Generate {n} distinct, specific and developable research questions that "
        "span different research angles where sensible (e.g. efficacy via a trial, "
        "risk/prognosis via a cohort, prevalence, association, and one qualitative "
        "angle). Each question must be concrete enough to design a study and run a "
        "meta-analysis around.\n\n"
        "For each question return: the full question text; the framework used "
        "(PICO, PECO or SPIDER); the population/sample; the intervention or "
        "exposure; the comparator (or empty if none); the outcome; the suggested "
        "study design; the effect measure best suited for synthesis — choose from: "
        f"{_MEASURE_HELP}; a FINER feasibility note (Feasible, Interesting, Novel, "
        "Ethical, Relevant); and a one-sentence rationale.\n\n"
        "IMPORTANT: respond in the SAME language as the topic. Return ONLY a JSON "
        "object, no prose, no markdown fences, with this exact shape:\n"
        '{"questions":[{"question":"...","framework":"PICO|PECO|SPIDER",'
        '"population":"...","exposure":"...","comparator":"...","outcome":"...",'
        '"design":"...","measure":"OR|RR|RD|HR|IRR|MD|SMD|PLOGIT|ZCOR|GEN",'
        '"finer":"...","rationale":"..."}]}'
    )


def _normalise_measure(m: str | None) -> str:
    if not m:
        return "GEN"
    m = str(m).upper().strip()
    return m if m in ALL_MEASURES else "GEN"


def _clean_questions(raw: list) -> list[dict]:
    out = []
    for q in raw:
        if not isinstance(q, dict) or not q.get("question"):
            continue
        out.append({
            "question": str(q.get("question")).strip(),
            "framework": str(q.get("framework") or "PICO").upper().strip(),
            "population": q.get("population") or "",
            "exposure": q.get("exposure") or q.get("intervention") or "",
            "comparator": q.get("comparator") or "",
            "outcome": q.get("outcome") or "",
            "design": q.get("design") or "",
            "measure": _normalise_measure(q.get("measure")),
            "finer": q.get("finer") or "",
            "rationale": q.get("rationale") or "",
        })
    return out


def _generate_ai(topic: str, n: int) -> list[dict]:
    obj = run_claude_json(_build_prompt(topic, n))
    questions = _clean_questions(obj.get("questions", []))
    if not questions:
        raise RuntimeError("no questions parsed from AI response")
    return questions


# --- Local deterministic fallback -------------------------------------------
def _looks_english(topic: str) -> bool:
    t = f" {topic.lower()} "
    en = sum(w in t for w in (" the ", " of ", " and ", " in ", " on ", " effect ", " risk ", " with "))
    es = sum(w in t for w in (" el ", " la ", " de ", " y ", " en ", " efecto ", " riesgo ", " con "))
    return en > es


_LOCAL_ANGLES_ES = [
    ("PICO", "Ensayo clínico aleatorizado", "SMD",
     'En [población], ¿"{t}" como intervención comparado con [control] mejora [desenlace medible]?'),
    ("PICO", "Ensayo clínico aleatorizado", "RR",
     'En [población], ¿"{t}" comparado con [control] reduce el riesgo de [evento binario]?'),
    ("PECO", "Cohorte prospectiva", "HR",
     'En [población], ¿la exposición a "{t}" frente a [no exposición] se asocia con [desenlace] en el tiempo?'),
    ("PECO", "Casos y controles", "OR",
     '¿La exposición a "{t}" se asocia con mayores probabilidades de [desenlace] comparado con [control]?'),
    ("DESCRIPTIVO", "Transversal", "PLOGIT",
     '¿Cuál es la prevalencia de [desenlace relacionado con "{t}"] en [población]?'),
    ("SPIDER", "Cualitativo fenomenológico", "GEN",
     '¿Cómo viven y significan [población] su experiencia con "{t}"?'),
]
_LOCAL_ANGLES_EN = [
    ("PICO", "Randomised controlled trial", "SMD",
     'In [population], does "{t}" versus [comparator] improve [measurable outcome]?'),
    ("PICO", "Randomised controlled trial", "RR",
     'In [population], does "{t}" versus [comparator] reduce the risk of [binary event]?'),
    ("PECO", "Prospective cohort", "HR",
     'In [population], is exposure to "{t}" versus [no exposure] associated with [outcome] over time?'),
    ("PECO", "Case-control", "OR",
     'Is exposure to "{t}" associated with higher odds of [outcome] versus [controls]?'),
    ("DESCRIPTIVE", "Cross-sectional", "PLOGIT",
     'What is the prevalence of [outcome related to "{t}"] in [population]?'),
    ("SPIDER", "Qualitative phenomenological", "GEN",
     'How do [population] experience and make sense of "{t}"?'),
]


def _generate_local(topic: str, n: int) -> list[dict]:
    english = _looks_english(topic)
    angles = _LOCAL_ANGLES_EN if english else _LOCAL_ANGLES_ES
    finer = ("Refine population, comparator and outcome to ensure feasibility and relevance (FINER)."
             if english else
             "Refina población, comparador y desenlace para asegurar viabilidad y relevancia (FINER).")
    rationale = ("Scaffold — fill the bracketed slots to finish the question."
                 if english else
                 "Plantilla — completa los campos entre corchetes para terminar la pregunta.")
    out = []
    for framework, design, measure, tmpl in angles[:max(1, n)]:
        out.append({
            "question": tmpl.format(t=topic.strip()),
            "framework": framework, "population": "", "exposure": topic.strip(),
            "comparator": "", "outcome": "", "design": design, "measure": measure,
            "finer": finer, "rationale": rationale,
        })
    return out


def generate_questions(topic: str, *, n: int = 5, mode: str = "auto") -> dict:
    """Generate research questions. mode: "auto" | "ai" | "local"."""
    topic = (topic or "").strip()
    if not topic:
        raise ValueError("Escribe un tema para generar preguntas.")
    if len(topic) > 2000:
        raise ValueError("El tema es demasiado largo (máx. 2000 caracteres).")
    n = max(1, min(int(n), 8))

    mode = mode.lower()
    env_mode = os.environ.get("METAFORGE_AI", "auto").lower()
    want_ai = mode != "local" and env_mode != "off" and (mode == "ai" or ai_available())

    if want_ai:
        try:
            return {"topic": topic, "source": "ai", "questions": _generate_ai(topic, n)}
        except Exception as exc:  # noqa: BLE001 — degrade gracefully
            if mode == "ai":
                raise ValueError(f"No se pudo generar con IA: {exc}") from exc
            return {"topic": topic, "source": "local", "questions": _generate_local(topic, n),
                    "ai_error": str(exc)}
    return {"topic": topic, "source": "local", "questions": _generate_local(topic, n)}
