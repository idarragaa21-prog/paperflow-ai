from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.core.logger import logger
from app.models.matrix import MatrixRow, MatrixVersion
from app.models.meta_run import MetaRun
from app.models.reference_item import ReferenceItem
from app.models.writing import WritingClaimLink, WritingDocument, WritingSection
from app.services.llm.factory import llm_provider


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

# Per-mode section templates. If a mode is not listed, DEFAULT_SECTION_SPECS is used.
MODE_SECTION_SPECS: dict[str, list[tuple[str, str]]] = {
    "narrative": DEFAULT_SECTION_SPECS,
    "systematic_review": [
        ("abstract", "Abstract"),
        ("introduction", "Introduction"),
        ("search_strategy", "Search strategy"),
        ("methods", "Methods"),
        ("risk_of_bias", "Risk of bias"),
        ("results", "Results"),
        ("discussion", "Discussion"),
        ("conclusion", "Conclusion"),
    ],
    "meta_analysis": [
        ("abstract", "Abstract"),
        ("introduction", "Introduction"),
        ("methods", "Methods"),
        ("statistical_analysis", "Statistical analysis"),
        ("results", "Results"),
        ("forest_plot", "Forest plot synthesis"),
        ("heterogeneity", "Heterogeneity assessment"),
        ("discussion", "Discussion"),
        ("conclusion", "Conclusion"),
    ],
    "letter_to_editor": [
        ("opening", "Opening"),
        ("comment", "Comment"),
        ("closing", "Closing"),
    ],
    "cover_letter": [
        ("salutation", "Salutation"),
        ("manuscript_summary", "Manuscript summary"),
        ("significance", "Significance"),
        ("disclosure", "Conflict of interest disclosure"),
        ("closing", "Closing"),
    ],
}


def _section_specs_for_mode(mode: str) -> list[tuple[str, str]]:
    return MODE_SECTION_SPECS.get(mode, DEFAULT_SECTION_SPECS)


def _numeric(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _best_effect_value(payload: dict[str, Any]) -> float | None:
    for key in (
        "effect_value",
        "adjusted_hr",
        "adjusted_rr",
        "adjusted_or",
        "or_value",
        "log_or",
    ):
        parsed = _numeric(payload.get(key))
        if parsed is not None:
            return parsed
    return None


def _default_section_text(section_key: str, heading: str) -> str:
    return f"## {heading}\n\n"


def _clip_text(text: str | None, *, max_len: int = 420, collapse_whitespace: bool = True) -> str:
    if not text:
        return ""
    compact = re.sub(r"\s+", " ", text).strip() if collapse_whitespace else str(text).strip()
    if len(compact) <= max_len:
        return compact
    return compact[: max_len - 1].rstrip() + "…"


def _safe_confidence(value: Any, default: float = 0.6) -> float:
    try:
        parsed = float(value)
    except Exception:
        return default
    return max(0.0, min(1.0, parsed))


def _extract_citation_markers(text: str) -> set[str]:
    return {match.group(0) for match in re.finditer(r"\[[A-Z]\d+\]", text or "")}


def _render_fallback_section(section: WritingSection, claims_payload: list[dict[str, Any]]) -> str:
    lines: list[str] = [f"## {section.heading}", ""]
    lines.append(
        "Grounded section generated from the current extraction matrix, latest quantitative run, and project references."
    )
    lines.append("")
    if not claims_payload:
        lines.append("### Traceability note")
        lines.append("- No matrix/meta/reference evidence was available at generation time [N1].")
        lines.append("")
    else:
        lines.append("### Evidence-grounded claims")
        for claim in claims_payload:
            marker = claim.get("citation_marker") or "[N]"
            lines.append(f"- {_clip_text(claim.get('claim_text'), max_len=320)} {marker}")
        lines.append("")
    lines.append("### Limitations")
    lines.append(
        "- Claims are constrained to linked matrix rows, run summaries, and reference entries. "
        "No unlinked factual statements were introduced."
    )
    return "\n".join(lines)


async def _generate_llm_grounded_markdown(
    *,
    document: WritingDocument,
    section: WritingSection,
    claims_payload: list[dict[str, Any]],
) -> tuple[str | None, str | None, str | None]:
    # Keep tests deterministic and fast.
    if os.getenv("PYTEST_CURRENT_TEST"):
        return None, None, "llm generation skipped in pytest context"
    if not claims_payload:
        return None, None, "no grounded claims available"

    provider = llm_provider()
    if not hasattr(provider, "chat"):
        return None, None, "llm provider has no chat method"

    evidence_lines = []
    for claim in claims_payload:
        marker = claim.get("citation_marker") or "[N]"
        source_type = claim.get("source_type") or "unknown_source"
        source_id = claim.get("source_id") or "unknown_id"
        confidence = _safe_confidence(claim.get("confidence"))
        evidence_lines.append(
            f"{marker} | source={source_type}:{source_id} | confidence={confidence:.2f} | claim={_clip_text(claim.get('claim_text'), max_len=260)}"
        )

    system = (
        "You are a senior biomedical scientific writer. "
        "Write concise, publication-grade English. "
        "Use ONLY the provided evidence claims. "
        "Do not invent numbers, effects, limitations, or citations. "
        "Every factual sentence must cite one or more provided markers exactly as given."
    )
    user = (
        f"Document mode: {document.mode}\n"
        f"Section key: {section.section_key}\n"
        f"Section heading: {section.heading}\n\n"
        "Allowed evidence claims (marker-locked):\n"
        + "\n".join(f"- {line}" for line in evidence_lines)
        + "\n\nTask:\n"
        "- Write the section in markdown with:\n"
        "  1) a short section opening,\n"
        "  2) an evidence synthesis paragraph,\n"
        "  3) a limitations paragraph.\n"
        "- Keep it directly grounded in the listed claims.\n"
        "- Reuse markers verbatim (e.g. [M1], [R2], [C3]).\n"
        "- Do not add any marker that is not in the list."
    )

    try:
        response = await provider.chat(  # type: ignore[attr-defined]
            model=settings.PAPERFLOW_WRITING_MODEL,
            system=system,
            user=user,
            temperature=0.15,
            max_tokens=1500,
            timeout=45,
            retry=1,
        )
        content = _clip_text(response.get("content"), max_len=12000, collapse_whitespace=False)
        model = str(response.get("model") or settings.PAPERFLOW_WRITING_MODEL)
        if not content:
            return None, None, "llm returned empty content"

        allowed_markers = {
            str(item.get("citation_marker") or "").strip()
            for item in claims_payload
            if str(item.get("citation_marker") or "").strip()
        }
        used_markers = _extract_citation_markers(content)

        if not used_markers:
            return None, None, "llm output missing grounded citation markers"
        if not used_markers.issubset(allowed_markers):
            unknown = ", ".join(sorted(used_markers - allowed_markers))
            return None, None, f"llm output used unknown citation markers: {unknown}"
        return content, model, None
    except Exception as exc:
        logger.warning(f"[writing] grounded llm generation failed for section {section.section_key}: {exc}")
        return None, None, str(exc)


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

    for position, (section_key, heading) in enumerate(_section_specs_for_mode(mode), start=1):
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

    claims_payload: list[dict[str, Any]] = []
    citation_counter = 1
    if rows:
        for row in rows[:6]:
            payload = row.data_json or {}
            marker = f"[M{citation_counter}]"
            effect_measure = payload.get("effect_measure") or row.effect_measure or "effect"
            outcome = payload.get("outcome_name") or payload.get("outcome_key") or "Outcome"
            effect_value = _best_effect_value(payload)
            ci_lower = _numeric(payload.get("ci_lower_95"))
            ci_upper = _numeric(payload.get("ci_upper_95"))
            n_total = payload.get("total_n")

            if effect_value is not None:
                ci_text = ""
                if ci_lower is not None and ci_upper is not None:
                    ci_text = f" (95% CI {ci_lower:.3g} to {ci_upper:.3g})"
                n_text = f"; n={n_total}" if n_total is not None else ""
                claim_text = f"{outcome}: {effect_measure} {effect_value:.4g}{ci_text}{n_text}"
                confidence = float(payload.get("confidence") or 0.6)
                grounding_status = "quantitative_supported"
            else:
                claim_text = (
                    f"{outcome}: extraction row available for {effect_measure}, "
                    "but no harmonized quantitative estimate is present yet."
                )
                confidence = float(payload.get("confidence") or 0.45)
                grounding_status = "qualitative_only"

            claims_payload.append(
                {
                    "claim_text": claim_text,
                    "source_type": "matrix_row",
                    "source_id": str(row.id),
                    "citation_marker": marker,
                    "confidence": confidence,
                    "source_locator": {"row_key": row.row_key},
                    "metadata_json": {"grounding_status": grounding_status},
                }
            )
            citation_counter += 1

    if latest_run:
        marker = f"[R{citation_counter}]"
        claims_payload.append(
            {
                "claim_text": (
                    f"Latest meta run `{latest_run.title}` (preset `{latest_run.preset}`) reports "
                    f"{(latest_run.summary_json or {}).get('rows', 'n/a')} analyzed rows."
                ),
                "source_type": "meta_run",
                "source_id": str(latest_run.id),
                "citation_marker": marker,
                "confidence": 0.75,
                "source_locator": {"preset": latest_run.preset},
                "metadata_json": {},
            }
        )
        citation_counter += 1

    if references:
        for ref in references[:4]:
            marker = f"[C{citation_counter}]"
            claims_payload.append(
                {
                    "claim_text": f"{ref.title} ({ref.publication_year or 'n.d.'})",
                    "source_type": "reference_item",
                    "source_id": str(ref.id),
                    "citation_marker": marker,
                    "confidence": 0.65,
                    "source_locator": {"doi": ref.doi, "pmid": ref.pmid},
                    "metadata_json": {},
                }
            )
            citation_counter += 1

    if not claims_payload:
        marker = "[N1]"
        claims_payload.append(
            {
                "claim_text": "No matrix/meta/reference evidence was available at generation time.",
                "source_type": "generation_context",
                "source_id": str(document.id),
                "citation_marker": marker,
                "confidence": 0.4,
                "source_locator": {"reason": "insufficient_project_evidence"},
                "metadata_json": {},
            }
        )

    for payload in claims_payload:
        db.add(
            WritingClaimLink(
                document_id=document.id,
                section_id=section.id,
                claim_text=str(payload["claim_text"]),
                source_type=str(payload["source_type"]),
                source_id=str(payload["source_id"]),
                citation_marker=str(payload.get("citation_marker") or ""),
                confidence=_safe_confidence(payload.get("confidence")),
                source_locator=payload.get("source_locator") or {},
                metadata_json=payload.get("metadata_json") or {},
            )
        )

    fallback_markdown = _render_fallback_section(section, claims_payload)
    llm_markdown, llm_model, llm_warning = await _generate_llm_grounded_markdown(
        document=document,
        section=section,
        claims_payload=claims_payload,
    )

    section.content_markdown = llm_markdown or fallback_markdown
    section.status = "ready"
    section.generated_with_model = llm_model or "grounded-template-fallback"
    section.metadata_json = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "matrix_rows_used": len(rows),
        "references_used": len(references),
        "meta_run_id": str(latest_run.id) if latest_run else None,
        "claim_count": len(claims_payload),
        "llm_used": bool(llm_markdown),
        "llm_warning": llm_warning,
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
