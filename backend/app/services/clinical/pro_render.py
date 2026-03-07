from __future__ import annotations

from typing import Any

from app.schemas.clinical_pro import ClinicalProOutput


def render_pro_to_markdown(out: ClinicalProOutput) -> str:
    """Render a ClinicalProOutput to a single Markdown document.

    This is used for exports (PDF/DOCX) and as a fallback viewer.
    """

    parts: list[str] = []
    parts.append(f"# {out.title}\n")

    for s in out.sections:
        parts.append(f"## {s.title}\n")
        parts.append((s.content_markdown or "").strip() + "\n")

    if out.tables:
        parts.append("## Tablas\n")
        for t in out.tables:
            parts.append(f"### {t.title}\n")
            cols = t.columns
            parts.append("| " + " | ".join([str(c) for c in cols]) + " |")
            parts.append("| " + " | ".join(["---" for _ in cols]) + " |")
            for row in t.rows:
                parts.append("| " + " | ".join([str(x) if x is not None else "" for x in row]) + " |")
            parts.append("")

    if out.charts:
        parts.append("## Gráficos\n")
        for ch in out.charts:
            parts.append(f"### {ch.title}\n")
            parts.append(f"Tipo: {ch.type}\n")
            if ch.note:
                parts.append(f"Nota: {ch.note}\n")
            parts.append("```json\n" + str(ch.data) + "\n```\n")

    if out.mermaid:
        parts.append("## Diagramas\n")
        for m in out.mermaid:
            parts.append(f"### {m.title}\n")
            parts.append("```mermaid\n" + (m.code or "") + "\n```\n")

    if out.evidence_map:
        parts.append("## Mapa de evidencia\n")
        parts.append("| Pregunta clínica | Conclusión | Fuerza | Papers clave | Limitaciones |")
        parts.append("|---|---|---|---|---|")
        for r in out.evidence_map:
            parts.append(
                "| "
                + " | ".join(
                    [
                        str(r.question),
                        str(r.conclusion),
                        str(r.strength),
                        ", ".join(r.key_papers or []),
                        str(r.limitations or ""),
                    ]
                )
                + " |"
            )
        parts.append("")

    if out.references_vancouver:
        parts.append("## Referencias\n")
        for x in out.references_vancouver:
            parts.append(str(x))

    return "\n".join(parts).strip() + "\n"
