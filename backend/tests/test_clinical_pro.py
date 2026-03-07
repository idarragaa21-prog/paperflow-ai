import uuid

import pytest

from app.database import async_session_maker
from app.models.clinical import ClinicalSheet


SHEET_ID = uuid.UUID("1b8cb0e2-35ab-4ace-89fe-be07f7e01849")


@pytest.mark.asyncio(scope="session")
async def test_json_schema_valid():
    """Valida que el content_json del sheet PRO tenga las keys y estructura mínimas esperadas."""
    async with async_session_maker() as db:
        sheet = await db.get(ClinicalSheet, SHEET_ID)
        assert sheet is not None, "ClinicalSheet no encontrado en DB"
        data = sheet.content_json
        assert isinstance(data, dict), "content_json debe ser dict"

        for k in ["title", "sections", "mermaid", "tables", "references_vancouver"]:
            assert k in data, f"content_json missing key: {k}"

        assert isinstance(data["sections"], list), "sections debe ser lista"
        for i, sec in enumerate(data["sections"]):
            assert isinstance(sec, dict), f"section[{i}] debe ser dict"
            assert isinstance(sec.get("id"), str) and sec.get("id"), f"section[{i}].id requerido"
            assert isinstance(sec.get("title"), str) and sec.get("title"), f"section[{i}].title requerido"
            assert isinstance(sec.get("content_markdown"), str), f"section[{i}].content_markdown debe ser string"

        assert isinstance(data["mermaid"], list), "mermaid debe ser lista"
        for i, d in enumerate(data["mermaid"]):
            assert isinstance(d, dict), f"mermaid[{i}] debe ser dict"
            assert isinstance(d.get("title"), str) and d.get("title"), f"mermaid[{i}].title requerido"
            assert isinstance(d.get("code"), str) and d.get("code"), f"mermaid[{i}].code requerido"

        assert isinstance(data["tables"], list), "tables debe ser lista"
        for i, t in enumerate(data["tables"]):
            assert isinstance(t, dict), f"tables[{i}] debe ser dict"
            assert isinstance(t.get("title"), str) and t.get("title"), f"tables[{i}].title requerido"
            assert isinstance(t.get("columns"), list), f"tables[{i}].columns debe ser lista"
            assert isinstance(t.get("rows"), list), f"tables[{i}].rows debe ser lista"

        assert isinstance(data["references_vancouver"], list), "references_vancouver debe ser lista"
        for i, r in enumerate(data["references_vancouver"]):
            assert isinstance(r, str) and r.strip(), f"references_vancouver[{i}] debe ser string no vacío"


@pytest.mark.asyncio(scope="session")
async def test_output_has_min_tables_charts_mermaid():
    """Asegura mínimos de assets PRO: tablas, diagramas mermaid y (comparativas o tablas extra)."""
    async with async_session_maker() as db:
        sheet = await db.get(ClinicalSheet, SHEET_ID)
        assert sheet is not None, "ClinicalSheet no encontrado en DB"
        data = sheet.content_json or {}

        tables = data.get("tables") or []
        mermaid = data.get("mermaid") or []

        assert len(tables) >= 2, "Should have at least 2 tables"
        assert len(mermaid) >= 1, "Should have at least 1 mermaid diagram"

        # El schema actual no tiene comparative_tables; usamos una condición equivalente.
        assert len(tables) >= 3 or (data.get("evidence_map") and len(data.get("evidence_map") or []) >= 1), (
            "Should have evidence_map or 3+ tables"
        )


@pytest.mark.asyncio(scope="session")
async def test_every_section_has_sources_or_insufficient_evidence():
    """Cada sección debe tener citas visibles o un disclaimer de evidencia insuficiente (no inventar)."""
    async with async_session_maker() as db:
        sheet = await db.get(ClinicalSheet, SHEET_ID)
        assert sheet is not None, "ClinicalSheet no encontrado en DB"
        data = sheet.content_json or {}

        sections = data.get("sections") or []
        assert isinstance(sections, list) and sections, "Debe existir al menos 1 sección"

        for sec in sections:
            title = sec.get("title") or sec.get("id") or "(sin título)"
            txt = (sec.get("content_markdown") or "").lower()
            has_fuentes = ("fuentes:" in txt) or ("pmid:" in txt) or ("doi:" in txt)
            has_disclaimer = ("evidencia insuficiente" in txt) or ("no encontrado" in txt) or ("insufficient evidence" in txt) or ("no evidence" in txt)

            assert has_fuentes or has_disclaimer, (
                f"Sección sin fuentes ni disclaimer de evidencia insuficiente: {title}"
            )
