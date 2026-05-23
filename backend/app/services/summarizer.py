from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.models.note import Note
from app.models.paper import Paper
from app.services.llm.factory import llm_provider
from app.services.pdf_processor import process_paper

_H2_RE = re.compile(r"^##\s+(.+?)\s*$")
_BOLD_RE = re.compile(r"^\*\*(.+?)\*\*\s*$")


def parse_summary_markdown(text: str) -> dict[str, str]:
    """Parse a markdown-ish summary into sections.

    Accepts headings like:
      - "## Título"
      - "**Título**"

    Returns {section_title: content}.
    """

    if not text:
        return {}

    t = re.sub(r"\r\n?", "\n", text).strip()

    # Split on headings (best-effort)
    lines = t.split("\n")
    sections: dict[str, list[str]] = {}
    current = "Resumen"
    sections[current] = []

    for ln in lines:
        m = _H2_RE.match(ln)
        if m:
            current = m.group(1).strip()
            sections.setdefault(current, [])
            continue
        m = _BOLD_RE.match(ln.strip())
        if m:
            current = m.group(1).strip()
            sections.setdefault(current, [])
            continue
        sections[current].append(ln)

    out: dict[str, str] = {}
    for k, v in sections.items():
        block = "\n".join(v).strip()
        if block:
            out[k] = block
    return out


async def generate_summary_async(
    *,
    paper_id: UUID,
    custom_instructions: str | None,
    db: AsyncSession,
) -> dict[str, Any]:
    paper = await db.get(Paper, paper_id)
    if not paper:
        raise ValueError("Paper no encontrado")

    if not paper.full_text_extracted:
        logger.info(f"Paper {paper_id} has no extracted text; processing first")
        await process_paper(paper_id, db)
        # refresh state best-effort
        paper = await db.get(Paper, paper_id)
        if not paper:
            raise ValueError("Paper no encontrado")

    full_text = (paper.full_text_extracted or "").strip()

    # Guardrail: avoid hallucinations when we barely extracted any text.
    # For scanned PDFs with OCR disabled, full_text can be extremely short.
    if len(full_text) < 800:
        summary_text = (
            "## Resumen\n"
            "Texto insuficiente para resumir el paper de forma fiable (poco texto extraíble).\n\n"
            "Sugerencias:\n"
            "- Verifica que el PDF no esté escaneado.\n"
            "- Si es escaneado, habilita OCR (OCR_ENABLED=true) e intenta de nuevo.\n"
            "- O sube una versión con texto seleccionable.\n"
        )
        r = {
            "model": None,
            "usage": {
                "input_tokens": 0,
                "output_tokens": 0,
                "cost_usd": None,
                "latency_ms": 0,
            },
        }
    else:
        llm = llm_provider()

        # M13: Structured summary – use a dedicated summarization model when configured.
        # Fall back to `llm.summarize_paper()` for all providers; inject a more
        # structured prompt via `custom_instructions` when none was supplied by the
        # caller so every summary always contains the five key academic sections.
        structured_sections_instruction = (
            "Structure the summary with exactly these sections (use ## headers):\n"
            "## Objetivo\n## Métodos\n## Resultados\n## Limitaciones\n## Conclusión\n"
            "Be concise and evidence-based. Do NOT invent numbers or data not in the text."
        )
        effective_instructions = custom_instructions or structured_sections_instruction

        r = await llm.summarize_paper(
            full_text=full_text,
            title=paper.title,
            custom_instructions=effective_instructions,
        )

        summary_text = (r.get("summary") or "").strip()

    sections = parse_summary_markdown(summary_text)

    note = Note(
        project_id=paper.project_id,
        paper_id=paper.id,
        title=f"Resumen: {paper.title}"[:255],
        content=summary_text or "(sin contenido)",
        note_type="summary",
        llm_model=r.get("model"),
        llm_usage=r.get("usage"),
        generation_prompt=None,
        updated_at=datetime.now(timezone.utc),
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)

    return {
        "note_id": str(note.id),
        "paper_id": str(paper.id),
        "sections": list(sections.keys()),
        "usage": r.get("usage"),
        "model": r.get("model"),
    }


def generate_summary_task(
    paper_id: str, custom_instructions: str | None = None
) -> dict[str, Any]:
    """SYNC wrapper for RQ (uses asyncio.run)."""

    async def _run() -> dict[str, Any]:
        from app.database import async_session_maker

        async with async_session_maker() as db:
            return await generate_summary_async(
                paper_id=UUID(paper_id),
                custom_instructions=custom_instructions,
                db=db,
            )

    return asyncio.run(_run())
