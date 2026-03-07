from __future__ import annotations


def _has_markdown_table(md: str) -> bool:
    if not md:
        return False
    lines = md.splitlines()
    for i in range(len(lines) - 1):
        ln = lines[i]
        nxt = lines[i + 1]
        if "|" in ln and "|" in nxt and set(nxt.replace("|", "").strip()) <= {"-", ":", " "}:
            return True
    return False


def _has_mermaid(md: str) -> bool:
    return "```mermaid" in (md or "")


def ensure_assets_present(md: str, *, topic: str) -> tuple[str, list[str]]:
    """Ensure the clinical sheet includes at least some tables and (when possible) a figure.

    We do NOT fabricate evidence. If we insert placeholders, we label them as
    evidence-insufficient and provide the required 'Fuentes:' transparency.

    Returns: (fixed_markdown, warnings)
    """

    if not md:
        return md, []

    warnings: list[str] = []

    needs_tables = not _has_markdown_table(md)
    needs_figure = not _has_mermaid(md)

    if not needs_tables and not needs_figure:
        return md, []

    out = md.rstrip()

    if needs_tables:
        warnings.append("No markdown tables found; inserted placeholder tables section.")
        out += (
            "\n\n## Tablas rápidas\n"
            "\n### Clasificación\n"
            "| Clase/Entidad | Criterios | Ref(s) |\n"
            "|---|---|---|\n"
            "| (No encontrado / evidencia insuficiente) | — | — |\n"
            "Fuentes: (No encontrado / evidencia insuficiente)\n"
            "\n### Diagnóstico diferencial\n"
            "| Diagnóstico | Claves clínicas/imagen | Cómo descartarlo | Ref(s) |\n"
            "|---|---|---|---|\n"
            "| (No encontrado / evidencia insuficiente) | — | — | — |\n"
            "Fuentes: (No encontrado / evidencia insuficiente)\n"
            "\n### Algoritmo (resumen en tabla)\n"
            "| Paso | Acción | Ref(s) |\n"
            "|---|---|---|\n"
            "| 1 | (No encontrado / evidencia insuficiente) | — |\n"
            "Fuentes: (No encontrado / evidencia insuficiente)\n"
            "\n### Tratamiento\n"
            "| Opción | Indicaciones | Riesgos/complicaciones | Ref(s) |\n"
            "|---|---|---|---|\n"
            "| (No encontrado / evidencia insuficiente) | — | — | — |\n"
            "Fuentes: (No encontrado / evidencia insuficiente)\n"
            "\n### Complicaciones y prevención\n"
            "| Complicación | Prevención/mitigación | Ref(s) |\n"
            "|---|---|---|\n"
            "| (No encontrado / evidencia insuficiente) | — | — |\n"
            "Fuentes: (No encontrado / evidencia insuficiente)\n"
            "\n### Perlas y trampas\n"
            "| Perla/Trampa | Explicación | Ref(s) |\n"
            "|---|---|---|\n"
            "| (No encontrado / evidencia insuficiente) | — | — |\n"
            "Fuentes: (No encontrado / evidencia insuficiente)\n"
        )

    if needs_figure:
        warnings.append("No mermaid figure found; inserted a conceptual figure.")
        safe_topic = (topic or "Tema clínico").strip().replace("\n", " ")[:80]
        out += (
            "\n\n## Figura conceptual: enfoque diagnóstico y manejo (conceptual)\n"
            f"Figura conceptual para: **{safe_topic}**.\n\n"
            "```mermaid\n"
            "flowchart TD\n"
            "A[Paciente con síntomas compatibles] --> B{Red flags?}\n"
            "B -->|Sí| C[Derivación urgente + imagen/labs según sospecha]\n"
            "B -->|No| D[Historia + examen dirigido]\n"
            "D --> E[Imágenes iniciales según clínica]\n"
            "E --> F{Diagnóstico probable?}\n"
            "F -->|No| G[Revaluar DDx + considerar imagen avanzada]\n"
            "F -->|Sí| H[Plan terapéutico escalonado]\n"
            "H --> I[Seguimiento + criterios de reevaluación]\n"
            "```\n"
            "Fuentes: (No encontrado / evidencia insuficiente)\n"
        )

    return out, warnings
