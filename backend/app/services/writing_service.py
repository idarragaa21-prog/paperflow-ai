from __future__ import annotations

from collections import defaultdict
import re
from types import SimpleNamespace
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.document import PaperCitationSpan
from app.models.draft import Draft, DraftCitation, DraftSection, EvidenceTable
from app.models.extraction import ExtractionRecord
from app.models.reference_item import ReferenceItem
from app.services.model_router import resolve_model


async def build_evidence_table(db: AsyncSession, *, project_id: UUID) -> EvidenceTable:
    stmt = (
        select(ExtractionRecord)
        .where(ExtractionRecord.project_id == project_id)
        .options(selectinload(ExtractionRecord.field_values))
        .order_by(ExtractionRecord.created_at.asc())
    )
    result = await db.execute(stmt)
    records = result.scalars().all()
    rows: list[dict] = []
    for record in records:
        row = {"record_id": str(record.id)}
        for field in record.field_values:
            row[field.field_name] = field.value_text
        rows.append(row)

    table = EvidenceTable(
        project_id=project_id,
        title="Project evidence table",
        table_json={"rows": rows, "count": len(rows)},
        confidence=0.75 if rows else 0.1,
        generated_from={"source": "extraction_records"},
    )
    db.add(table)
    await db.commit()
    await db.refresh(table)
    return table


async def generate_section(
    db: AsyncSession,
    *,
    draft: Draft,
    heading: str,
    paper_ids: list[UUID],
    extraction_record_ids: list[UUID],
    runtime_mode: str,
) -> DraftSection:
    route = resolve_model("writing", runtime_mode)
    references_q = await db.execute(select(ReferenceItem).where(ReferenceItem.project_id == draft.project_id).order_by(ReferenceItem.created_at.asc()))
    references = references_q.scalars().all()
    reference_by_paper = {ref.paper_id: ref for ref in references if ref.paper_id}

    records_stmt = (
        select(ExtractionRecord)
        .where(ExtractionRecord.project_id == draft.project_id)
        .options(selectinload(ExtractionRecord.field_values))
    )
    if extraction_record_ids:
        records_stmt = records_stmt.where(ExtractionRecord.id.in_(extraction_record_ids))
    elif paper_ids:
        records_stmt = records_stmt.where(ExtractionRecord.paper_id.in_(paper_ids))
    extraction_records = (await db.execute(records_stmt)).scalars().all()

    lines: list[str] = []
    citations_payload: list[tuple[str, ReferenceItem | None, PaperCitationSpan | None]] = []
    marker_counter = 1
    for record in extraction_records:
        field_map = {field.field_name: field.value_text for field in record.field_values}
        title = field_map.get("title") or f"Study {str(record.id)[:8]}"
        design = field_map.get("design") or "study"
        result = field_map.get("results") or "reported relevant findings"
        conclusion = field_map.get("conclusion") or "supports further review"
        marker = f"[{marker_counter}]"
        marker_counter += 1
        lines.append(f"{title} was identified as a {design}. Key findings indicate that {result}. The reported conclusion was that {conclusion} {marker}")

        reference = reference_by_paper.get(record.paper_id) if record.paper_id else None
        span = None
        if record.paper_id:
            span_q = await db.execute(
                select(PaperCitationSpan)
                .where(PaperCitationSpan.paper_id == record.paper_id)
                .order_by(PaperCitationSpan.created_at.asc())
                .limit(1)
            )
            span = span_q.scalars().first()
        citations_payload.append((marker, reference, span))

    content = "\n\n".join(lines) if lines else f"{heading} is ready for authoring. Add papers or extraction records to generate grounded prose."
    unsupported_spans = []
    for sentence in re.split(r"(?<=[.!?])\s+", content):
        stripped = sentence.strip()
        if not stripped:
            continue
        if "[" not in stripped or "]" not in stripped:
            unsupported_spans.append(stripped[:220])
    section = DraftSection(
        draft_id=draft.id,
        heading=heading,
        position=len(draft.sections),
        content=content,
        generated_with_model=route.model,
        confidence=0.7 if lines else 0.1,
        source_summary={
            "records": len(extraction_records),
            "references": len(references),
            "unsupported_spans": unsupported_spans,
            "citation_coverage": 0.0 if not content else round(max(0.0, 1 - (len(unsupported_spans) / max(1, len([s for s in re.split(r'(?<=[.!?])\\s+', content) if s.strip()])))), 2),
        },
    )
    db.add(section)
    await db.flush()

    for marker, reference, span in citations_payload:
        db.add(
            DraftCitation(
                draft_section_id=section.id,
                reference_item_id=reference.id if reference else None,
                paper_citation_span_id=span.id if span else None,
                marker=marker,
                quoted_text=span.quoted_text if span else (reference.title if reference else None),
                locator=span.locator if span else None,
                confidence=0.8 if reference or span else 0.2,
            )
        )

    draft.version += 1
    await db.commit()
    await db.refresh(section)
    return section


async def resolve_section_citations(db: AsyncSession, *, section: DraftSection) -> list[DraftCitation]:
    await db.refresh(section, attribute_names=["citations"])
    if section.citations:
        return list(section.citations)

    markers = defaultdict(int)
    for token in section.content.split():
        if token.startswith("[") and token.endswith("]"):
            markers[token] += 1

    created: list[DraftCitation] = []
    for marker in markers:
        citation = DraftCitation(
            draft_section_id=section.id,
            marker=marker,
            quoted_text=None,
            locator=None,
            confidence=0.1,
        )
        db.add(citation)
        created.append(citation)
    await db.commit()
    return created


def _build_clinical_context_for_draft(draft: Draft) -> str | None:
    snippets: list[str] = []
    for section in sorted(draft.sections, key=lambda item: item.position)[:4]:
        content = (section.content or "").strip()
        if not content:
            continue
        snippet = content[:900]
        if len(content) > 900:
            snippet = f"{snippet}..."
        snippets.append(f"{section.heading}: {snippet}")
    if not snippets:
        return None
    return "Existing draft context:\n" + "\n\n".join(snippets)


async def enhance_draft_with_clinical_evidence(
    db: AsyncSession,
    *,
    draft: Draft,
    user_id: UUID,
) -> DraftSection:
    from app.services.clinical.generator import generate_clinical_sheet

    context = _build_clinical_context_for_draft(draft)
    clinical_request = SimpleNamespace(
        project_id=draft.project_id,
        user_id=user_id,
        topic=draft.title,
        input_params={
            "context": context,
            "objective": "quick_review",
            "focus": "complete",
            "level": "specialist",
            "max_length": "standard",
            "use_project_papers": True,
            "search_online": True,
            "use_books": True,
            "pro_output": True,
        },
    )
    output = await generate_clinical_sheet(db=db, sheet=clinical_request, progress_cb=None)

    heading = "Clinical evidence enrichment"
    content = str(output.get("content_markdown") or "").strip()
    if not content:
        raise RuntimeError("Clinical enrichment returned empty content")

    source_summary = {
        "generated_from": "clinical_pipeline",
        "format_version": output.get("format_version"),
        "llm_model": output.get("llm_model"),
        "warnings": output.get("warnings") or [],
        "sources_used": output.get("sources_used") or {},
    }
    metadata = dict(draft.metadata_json or {})
    metadata["clinical_enrichment"] = {
        "heading": heading,
        "format_version": output.get("format_version"),
        "llm_model": output.get("llm_model"),
        "warnings": output.get("warnings") or [],
    }
    draft.metadata_json = metadata

    existing_section = next((section for section in draft.sections if section.heading == heading), None)
    if existing_section is None:
        existing_section = DraftSection(
            draft_id=draft.id,
            heading=heading,
            position=len(draft.sections),
            content=content,
            generated_with_model=str(output.get("llm_model") or "clinical"),
            confidence=0.82,
            source_summary=source_summary,
        )
        draft.sections.append(existing_section)
        db.add(existing_section)
    else:
        existing_section.content = content
        existing_section.generated_with_model = str(output.get("llm_model") or "clinical")
        existing_section.confidence = 0.82
        existing_section.source_summary = source_summary

    draft.version += 1
    await db.commit()
    await db.refresh(existing_section)
    return existing_section
