from __future__ import annotations

import re
from typing import Any

from app.schemas.clinical_pro import (
    ClinicalProChart,
    ClinicalProMermaid,
    ClinicalProOutput,
    ClinicalProSection,
    ClinicalProTable,
)
from app.services.clinical.citations_gate import ensure_fuentes_per_section
from app.services.clinical.traceability_gate import enforce_claim_traceability


RE_PAPER_CITE = re.compile(r"(PMID:\d+|doi:|DOI:)\S*")


def _append_gap(out: ClinicalProOutput, gap: str) -> None:
    if gap not in out.quality.gaps:
        out.quality.gaps.append(gap)


def gate_min_sections(out: ClinicalProOutput) -> tuple[ClinicalProOutput, list[str]]:
    warnings: list[str] = []

    required = [
        ("resumen", "Resumen Ejecutivo"),
        ("definicion", "Definición + fisiopatología"),
        ("diagnostico", "Diagnóstico (algoritmo)"),
        ("tratamiento", "Tratamiento (tabla por escenarios)"),
        ("perlas", "Perlas clínicas + errores frecuentes"),
        ("controversias", "Controversias / zonas grises"),
        ("checklist", "Checklist para guardia / consultorio"),
    ]

    existing_ids = {s.id for s in out.sections}
    sections = list(out.sections)

    for sid, stitle in required:
        if sid not in existing_ids:
            sections.append(
                ClinicalProSection(
                    id=sid,
                    title=stitle,
                    content_markdown="Fuentes: (No encontrado / evidencia insuficiente)",
                )
            )
            warnings.append(f"Inserted missing section: {sid}")

    # Keep order by required list first then others
    order = {sid: i for i, (sid, _t) in enumerate(required)}
    sections.sort(key=lambda s: order.get(s.id, 999))

    out2 = out.model_copy(deep=True)
    out2.sections = sections
    return out2, warnings


def gate_citations_per_section(out: ClinicalProOutput) -> tuple[ClinicalProOutput, list[str]]:
    warnings: list[str] = []
    out2 = out.model_copy(deep=True)

    fixed_sections = []
    for s in out.sections:
        fixed, w = ensure_fuentes_per_section(s.content_markdown)
        if w:
            warnings.extend([f"{s.id}: {x}" for x in w])
        fixed_sections.append(s.model_copy(update={"content_markdown": fixed}))

    out2.sections = fixed_sections
    return out2, warnings


def gate_min_evidence_map(out: ClinicalProOutput) -> tuple[ClinicalProOutput, list[str]]:
    warnings: list[str] = []

    out2 = out.model_copy(deep=True)

    if not out.evidence_map:
        warnings.append("Evidence map missing; inserted explicit degraded fallback row.")
        out2.evidence_map = [
            {
                "question": "(No encontrado / evidencia insuficiente)",
                "conclusion": "No encontrado / evidencia insuficiente",
                "strength": "low",
                "key_papers": [],
                "limitations": "No se identificaron artículos suficientes en el bundle provisto.",
            }
        ]
        _append_gap(out2, "evidence_map_missing")
        _append_gap(out2, "evidence_map_degraded_fallback")

    return out2, warnings



def gate_min_assets(out: ClinicalProOutput) -> tuple[ClinicalProOutput, list[str]]:
    warnings: list[str] = []

    out2 = out.model_copy(deep=True)

    tables = list(out.tables or [])
    charts = list(out.charts or [])
    mermaid = list(out.mermaid or [])

    # Tables: ensure >=5
    if len(tables) < 5:
        warnings.append("Inserted degraded fallback tables to reach minimum 5.")
        _append_gap(out2, "tables_degraded_fallback")
        needed = 5 - len(tables)
        for i in range(needed):
            tables.append(
                ClinicalProTable(
                    title=f"Tabla de apoyo (fallback degradado {len(tables)+1})",
                    columns=["Campo", "Contenido", "Ref(s)"],
                    rows=[["(No encontrado / evidencia insuficiente)", "—", "—"]],
                )
            )

    # Charts: ensure >=2
    if len(charts) < 2:
        warnings.append("Inserted degraded fallback charts to reach minimum 2.")
        _append_gap(out2, "charts_degraded_fallback")
        while len(charts) < 2:
            charts.append(
                ClinicalProChart(
                    title=f"Gráfico conceptual (fallback degradado {len(charts)+1})",
                    type="conceptual",
                    data={"note": "No se extrajeron datos cuantitativos suficientes para un gráfico analítico."},
                    note="Fallback degradado: conceptual, no derivado de datos cuantitativos.",
                )
            )

    # Mermaid: ensure mindmap + flowchart
    has_flow = any("flowchart" in (m.code or "") for m in mermaid)
    has_mind = any("mindmap" in (m.code or "") for m in mermaid)

    if not has_mind:
        warnings.append("Inserted degraded fallback mermaid mindmap.")
        _append_gap(out2, "mindmap_degraded_fallback")
        mermaid.append(
            ClinicalProMermaid(
                title="Mapa conceptual (fallback degradado)",
                code="mindmap\n  root((Tema))\n    (No encontrado / evidencia insuficiente)",
            )
        )

    if not has_flow:
        warnings.append("Inserted degraded fallback mermaid flowchart.")
        _append_gap(out2, "flowchart_degraded_fallback")
        mermaid.append(
            ClinicalProMermaid(
                title="Algoritmo clínico (fallback degradado)",
                code="flowchart TD\nA[Inicio]-->B{Evidencia?}\nB-->|No|C[No encontrado / evidencia insuficiente]\nB-->|Sí|D[Aplicar recomendación]\n",
            )
        )

    out2.tables = tables
    out2.charts = charts
    out2.mermaid = mermaid
    return out2, warnings


def gate_claim_traceability(out: ClinicalProOutput, *, core_papers: list[dict[str, Any]] | None) -> tuple[ClinicalProOutput, list[str]]:
    """Claim-level traceability: important bullets must be cited or marked evidence-insufficient."""

    warnings: list[str] = []
    out2 = out.model_copy(deep=True)

    fixed_sections = []
    for s in out.sections:
        fixed, w = enforce_claim_traceability(s.content_markdown or "", core_papers=core_papers or [])
        warnings.extend([f"{s.id}: {x}" for x in w])
        fixed_sections.append(s.model_copy(update={"content_markdown": fixed}))

    out2.sections = fixed_sections
    return out2, warnings



def gate_article_dominance(out: ClinicalProOutput) -> tuple[ClinicalProOutput, list[str]]:
    """Best-effort: if articles exist, ensure sections include visible PMID/DOI.

    We don't rewrite clinical content; we only add a warning line when missing.
    """

    warnings: list[str] = []

    # Detect whether any PMID/DOI appears anywhere
    any_article_cite = False
    for s in out.sections:
        if RE_PAPER_CITE.search(s.content_markdown or ""):
            any_article_cite = True
            break

    if not any_article_cite:
        warnings.append("No visible PMID/DOI citations detected in sections.")

    out2 = out.model_copy(deep=True)
    fixed_sections = []
    for s in out.sections:
        txt = s.content_markdown or ""
        if not RE_PAPER_CITE.search(txt):
            # Add a conservative note before Fuentes line (or at end)
            if "Fuentes:" in txt:
                parts = txt.split("Fuentes:")
                txt = parts[0].rstrip() + "\n\nNota: faltan citas por afirmación; ver Mapa de evidencia.\n\nFuentes:" + "Fuentes:".join(parts[1:])
            else:
                txt = txt.rstrip() + "\n\nNota: faltan citas por afirmación; ver Mapa de evidencia.\n"
            warnings.append(f"Section {s.id}: no PMID/DOI detected")
        fixed_sections.append(s.model_copy(update={"content_markdown": txt}))

    out2.sections = fixed_sections
    return out2, warnings
