from __future__ import annotations


def sections_for(*, objective: str, focus: str) -> list[str]:
    """Return a canonical ordered section list based on objective/focus.

    This is used to constrain the LLM (and for tests). The LLM may add minor
    subsections, but must keep major headings.
    """

    objective = (objective or "clinical_decision").strip().lower()
    focus = (focus or "complete").strip().lower()

    # Base full set
    all_sections = [
        "Resumen ejecutivo",
        "Definición y conceptos clave",
        "Epidemiología relevante",
        "Clasificación/Estadificación",
        "Anatomía/Biomecánica relevante",
        "Presentación clínica + Red flags",
        "Evaluación diagnóstica",
        "Diagnóstico diferencial",
        "Tratamiento conservador",
        "Tratamiento quirúrgico",
        "Rehabilitación / Return to sport-work",
        "Complicaciones y manejo",
        "Pronóstico y factores pronósticos",
        "Controversias actuales / Evidencia en desarrollo",
        "Checklist práctico",
        "Referencias",
    ]

    if objective == "quick_review":
        # max 2000 words: only key sections
        return [
            "Resumen ejecutivo",
            "Presentación clínica + Red flags",
            "Evaluación diagnóstica",
            "Tratamiento conservador",
            "Tratamiento quirúrgico",
            "Checklist práctico",
            "Referencias",
        ]

    if objective == "presentation":
        # keep it concise but broad
        return [
            "Resumen ejecutivo",
            "Presentación clínica + Red flags",
            "Evaluación diagnóstica",
            "Tratamiento (conservador y quirúrgico)",
            "Complicaciones y manejo",
            "Checklist práctico",
            "Referencias",
        ]

    # teaching: include all
    if objective == "teaching":
        base = list(all_sections)
    else:
        base = list(all_sections)

    # Focus filters
    if focus == "diagnostic":
        # Expand dx, omit treatment
        base = [
            "Resumen ejecutivo",
            "Definición y conceptos clave",
            "Presentación clínica + Red flags",
            "Evaluación diagnóstica",
            "Diagnóstico diferencial",
            "Checklist práctico",
            "Referencias",
        ]
    elif focus == "surgical":
        base = [s for s in base if s not in ("Tratamiento conservador",)]
    elif focus == "conservative":
        base = [s for s in base if s not in ("Tratamiento quirúrgico",)]
    elif focus == "rehab":
        # keep rehab emphasized; keep treatments but allow LLM to focus rehab
        base = [s for s in base if s != "Anatomía/Biomecánica relevante"]
    elif focus == "complications":
        base = [
            "Resumen ejecutivo",
            "Complicaciones y manejo",
            "Pronóstico y factores pronósticos",
            "Checklist práctico",
            "Referencias",
        ]

    # Ensure references last
    if base[-1] != "Referencias":
        if "Referencias" in base:
            base = [s for s in base if s != "Referencias"] + ["Referencias"]
        else:
            base.append("Referencias")

    return base
