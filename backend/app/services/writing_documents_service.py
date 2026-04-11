from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.matrix import MatrixRow, MatrixVersion
from app.models.meta_run import MetaRun
from app.models.reference_item import ReferenceItem
from app.models.writing import WritingClaimLink, WritingDocument, WritingSection


SUPPORTED_WRITING_MODES = {
    "narrative",
    "systematic_review",
    "meta_analysis",
    "letter_to_editor",
    "cover_letter",
}

DEFAULT_SECTION_SPECS: list[tuple[str, str]] = [
    ("introduction", "Introduction"),
    ("methods", "Methods"),
    ("results", "Results"),
    ("discussion", "Discussion"),
    ("conclusion", "Conclusion"),
    ("abstract", "Abstract"),
]


def _default_section_text(section_key: str, heading: str) -> str:
    return (
        f"## {heading}\n\n"
        f"_Draft placeholder for **{section_key}**. Use `/writing/documents/{{id}}/sections/{section_key}` "
        "to generate grounded content from matrix, meta runs, and references._"
    )


async def create_document(
    db: AsyncSession,
    *,
    project_id: UUID,
    user_id: UUID,
    title: str,
    mode: str,
) -> WritingDocument:
    if mode not in SUPPORTED_WRITING_MODES:
        raise ValueError(f"Unsupported writing mode: {mode}")
    if not title.strip():
        raise ValueError("title is required")

    document = WritingDocument(
        project_id=project_id,
        user_id=user_id,
        title=title.strip(),
        mode=mode,
        status="draft",
        version=1,
        metadata_json={},
    )
    db.add(document)
    await db.flush()

    for position, (section_key, heading) in enumerate(DEFAULT_SECTION_SPECS, start=1):
        db.add(
            WritingSection(
                document_id=document.id,
                section_key=section_key,
                heading=heading,
                position=position,
                status="draft",
                content_markdown=_default_section_text(section_key, heading),
                metadata_json={},
            )
        )

    await db.commit()
    stmt = (
        select(WritingDocument)
        .where(WritingDocument.id == document.id)
        .options(
            selectinload(WritingDocument.sections),
            selectinload(WritingDocument.claim_links),
        )
    )
    result = await db.execute(stmt)
    return result.scalars().first()


async def get_document(db: AsyncSession, *, document_id: UUID) -> WritingDocument | None:
    stmt = (
        select(WritingDocument)
        .where(WritingDocument.id == document_id)
        .options(
            selectinload(WritingDocument.sections),
            selectinload(WritingDocument.claim_links),
        )
    )
    result = await db.execute(stmt)
    return result.scalars().first()


async def list_documents(db: AsyncSession, *, project_id: UUID) -> list[WritingDocument]:
    stmt = (
        select(WritingDocument)
        .where(WritingDocument.project_id == project_id)
        .options(
            selectinload(WritingDocument.sections),
            selectinload(WritingDocument.claim_links),
        )
        .order_by(WritingDocument.created_at.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def _latest_matrix_rows(db: AsyncSession, *, project_id: UUID, limit: int = 8) -> list[MatrixRow]:
    matrix_stmt = (
        select(MatrixVersion)
        .where(MatrixVersion.project_id == project_id)
        .where(MatrixVersion.is_current == True)  # noqa: E712
        .order_by(MatrixVersion.version_number.desc())
        .limit(1)
    )
    matrix = (await db.execute(matrix_stmt)).scalars().first()
    if not matrix:
        return []
    rows_stmt = (
        select(MatrixRow)
        .where(MatrixRow.matrix_version_id == matrix.id)
        .where(MatrixRow.row_kind == "effect")
        .order_by(MatrixRow.sort_index.asc(), MatrixRow.created_at.asc())
        .limit(limit)
    )
    return (await db.execute(rows_stmt)).scalars().all()


async def _latest_meta_run(db: AsyncSession, *, project_id: UUID) -> MetaRun | None:
    stmt = (
        select(MetaRun)
        .where(MetaRun.project_id == project_id)
        .where(MetaRun.status == "completed")
        .order_by(MetaRun.created_at.desc())
        .limit(1)
    )
    return (await db.execute(stmt)).scalars().first()


async def _top_references(db: AsyncSession, *, project_id: UUID, limit: int = 8) -> list[ReferenceItem]:
    stmt = (
        select(ReferenceItem)
        .where(ReferenceItem.project_id == project_id)
        .order_by(ReferenceItem.created_at.desc())
        .limit(limit)
    )
    return (await db.execute(stmt)).scalars().all()


async def generate_section(
    db: AsyncSession,
    *,
    document: WritingDocument,
    section: WritingSection,
) -> WritingSection:
    rows = await _latest_matrix_rows(db, project_id=document.project_id, limit=10)
    latest_run = await _latest_meta_run(db, project_id=document.project_id)
    references = await _top_references(db, project_id=document.project_id, limit=8)

    # Replace existing claim links for this section before regeneration.
    old_links_q = await db.execute(
        select(WritingClaimLink).where(WritingClaimLink.document_id == document.id).where(WritingClaimLink.section_id == section.id)
    )
    for item in old_links_q.scalars().all():
        await db.delete(item)
    await db.flush()

    lines: list[str] = [f"## {section.heading}", ""]
    lines.append(
        "Grounded section generated from the current extraction matrix, latest quantitative run, and project references."
    )
    lines.append("")

    citation_counter = 1
    if rows:
        lines.append("### Matrix-derived evidence")
        for row in rows[:6]:
            payload = row.data_json or {}
            marker = f"[M{citation_counter}]"
            effect_measure = payload.get("effect_measure") or row.effect_measure or "effect"
            outcome = payload.get("outcome_name") or payload.get("outcome_key") or "Outcome"
            effect_value = payload.get("or_value") or payload.get("adjusted_or") or payload.get("adjusted_rr") or payload.get("adjusted_hr")
            lines.append(f"- {outcome}: {effect_measure} {effect_value if effect_value is not None else 'not reported'} {marker}")
            db.add(
                WritingClaimLink(
                    document_id=document.id,
                    section_id=section.id,
                    claim_text=f"{outcome}: {effect_measure} {effect_value if effect_value is not None else 'not reported'}",
                    source_type="matrix_row",
                    source_id=str(row.id),
                    citation_marker=marker,
                    confidence=float(payload.get("confidence") or 0.6),
                    source_locator={"row_key": row.row_key},
                    metadata_json={},
                )
            )
            citation_counter += 1
        lines.append("")

    if latest_run:
        marker = f"[R{citation_counter}]"
        lines.append("### Quantitative synthesis")
        lines.append(
            f"- Latest meta run `{latest_run.title}` (preset `{latest_run.preset}`) reports "
            f"{(latest_run.summary_json or {}).get('rows', 'n/a')} analyzed rows {marker}."
        )
        db.add(
            WritingClaimLink(
                document_id=document.id,
                section_id=section.id,
                claim_text=f"Latest meta run: {latest_run.title}",
                source_type="meta_run",
                source_id=str(latest_run.id),
                citation_marker=marker,
                confidence=0.75,
                source_locator={"preset": latest_run.preset},
                metadata_json={},
            )
        )
        citation_counter += 1
        lines.append("")

    if references:
        lines.append("### Supporting references")
        for ref in references[:4]:
            marker = f"[C{citation_counter}]"
            lines.append(f"- {ref.title} ({ref.publication_year or 'n.d.'}) {marker}")
            db.add(
                WritingClaimLink(
                    document_id=document.id,
                    section_id=section.id,
                    claim_text=ref.title,
                    source_type="reference_item",
                    source_id=str(ref.id),
                    citation_marker=marker,
                    confidence=0.65,
                    source_locator={"doi": ref.doi, "pmid": ref.pmid},
                    metadata_json={},
                )
            )
            citation_counter += 1
        lines.append("")

    if citation_counter == 1:
        marker = "[N1]"
        lines.append("### Traceability note")
        lines.append(f"- No matrix/meta/reference evidence was available at generation time {marker}.")
        db.add(
            WritingClaimLink(
                document_id=document.id,
                section_id=section.id,
                claim_text="No matrix/meta/reference evidence was available at generation time.",
                source_type="generation_context",
                source_id=str(document.id),
                citation_marker=marker,
                confidence=0.4,
                source_locator={"reason": "insufficient_project_evidence"},
                metadata_json={},
            )
        )
        citation_counter += 1
        lines.append("")

    lines.append("### Limitations")
    lines.append(
        "- Claims are constrained to linked matrix rows, run summaries, and reference entries. "
        "No unlinked factual statements were introduced."
    )

    section.content_markdown = "\n".join(lines)
    section.status = "ready"
    section.generated_with_model = "grounded-template"
    section.metadata_json = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "matrix_rows_used": len(rows),
        "references_used": len(references),
        "meta_run_id": str(latest_run.id) if latest_run else None,
    }
    document.status = "in_progress"
    document.version = int(document.version or 1) + 1
    document.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(section)
    return section


async def update_section_content(
    db: AsyncSession,
    *,
    document: WritingDocument,
    section: WritingSection,
    content_markdown: str | None,
    heading: str | None,
) -> WritingSection:
    if content_markdown is not None:
        section.content_markdown = content_markdown
    if heading is not None and heading.strip():
        section.heading = heading.strip()
    section.status = "edited"
    document.version = int(document.version or 1) + 1
    document.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(section)
    return section


async def resolve_document_citations(
    db: AsyncSession,
    *,
    document: WritingDocument,
) -> dict[str, Any]:
    stmt = (
        select(WritingClaimLink)
        .where(WritingClaimLink.document_id == document.id)
        .order_by(WritingClaimLink.created_at.asc())
    )
    links = (await db.execute(stmt)).scalars().all()
    citations = [
        {
            "marker": link.citation_marker,
            "claim_text": link.claim_text,
            "source_type": link.source_type,
            "source_id": link.source_id,
            "source_locator": link.source_locator or {},
            "confidence": link.confidence,
        }
        for link in links
    ]
    return {
        "document_id": str(document.id),
        "count": len(citations),
        "citations": citations,
    }


def serialize_document(document: WritingDocument) -> dict[str, Any]:
    sections_sorted = sorted(document.sections, key=lambda item: (item.position, item.created_at))
    return {
        "id": str(document.id),
        "project_id": str(document.project_id),
        "user_id": str(document.user_id),
        "title": document.title,
        "mode": document.mode,
        "status": document.status,
        "version": document.version,
        "created_at": document.created_at.isoformat() if document.created_at else None,
        "updated_at": document.updated_at.isoformat() if document.updated_at else None,
        "metadata_json": document.metadata_json or {},
        "sections": [
            {
                "id": str(section.id),
                "section_key": section.section_key,
                "heading": section.heading,
                "position": section.position,
                "status": section.status,
                "generated_with_model": section.generated_with_model,
                "content_markdown": section.content_markdown,
                "metadata_json": section.metadata_json or {},
            }
            for section in sections_sorted
        ],
        "claim_links": [
            {
                "id": str(link.id),
                "section_id": str(link.section_id) if link.section_id else None,
                "claim_text": link.claim_text,
                "source_type": link.source_type,
                "source_id": link.source_id,
                "citation_marker": link.citation_marker,
                "confidence": link.confidence,
                "source_locator": link.source_locator or {},
            }
            for link in document.claim_links
        ],
    }
