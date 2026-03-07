from __future__ import annotations

import csv
import io
import re
from uuid import UUID

from fastapi.responses import JSONResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.document import PaperChunk
from app.models.extraction import ExtractionFieldValue, ExtractionRecord, ExtractionTemplate
from app.models.paper import Paper

UNIVERSAL_FIELDS = [
    "title",
    "authors",
    "year",
    "country",
    "design",
    "population",
    "sample",
    "intervention",
    "comparator",
    "outcomes",
    "results",
    "follow_up",
    "limitations",
    "conclusion",
]

CONTROLLED_VOCAB = {
    "design": [
        "randomized",
        "cohort",
        "case-control",
        "cross-sectional",
        "systematic review",
        "meta-analysis",
    ],
}


def universal_template_schema() -> dict:
    return {
        "version": "universal-study-template.v1",
        "fields": [
            {"name": name, "label": name.replace("_", " ").title(), "type": "text"}
            for name in UNIVERSAL_FIELDS
        ]
    }


async def ensure_builtin_template(db: AsyncSession) -> ExtractionTemplate:
    existing = await db.execute(select(ExtractionTemplate).where(ExtractionTemplate.slug == "universal-study-template"))
    template = existing.scalars().first()
    if template:
        return template
    template = ExtractionTemplate(
        name="Universal Study Template",
        slug="universal-study-template",
        description="General-purpose structured extraction for scientific studies.",
        discipline="general",
        is_builtin=True,
        schema_json=universal_template_schema(),
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template


def _first_matching_chunk(chunks: list[PaperChunk], terms: list[str]) -> tuple[int | None, dict | None]:
    lowered_terms = [term.lower() for term in terms if term]
    for chunk in chunks:
        lowered = chunk.text.lower()
        if any(term in lowered for term in lowered_terms):
            return chunk.page_number, chunk.locator
    return None, None


def _candidate_spans(chunks: list[PaperChunk], *, field_name: str, value: str | None, limit: int = 3) -> list[dict]:
    candidates: list[dict] = []
    terms = [token for token in [value, field_name] if token]
    lowered_terms = [term.lower() for term in terms]
    for chunk in chunks:
        lowered = chunk.text.lower()
        if any(term in lowered for term in lowered_terms):
            candidates.append(
                {
                    "paper_chunk_id": str(chunk.id),
                    "page": chunk.page_number,
                    "locator": chunk.locator,
                    "quoted_text": chunk.text[:320],
                }
            )
        if len(candidates) >= limit:
            break
    return candidates


def _extract_value(name: str, paper: Paper, text: str) -> str | None:
    lowered = text.lower()
    if name == "title":
        return paper.title
    if name == "authors":
        return paper.authors
    if name == "year":
        return str(paper.publication_year) if paper.publication_year else None
    if name == "country":
        match = re.search(r"\b(in|from|country)\s+([A-Z][A-Za-z\s]{2,40})", text)
        return match.group(2).strip() if match else None
    if name == "design":
        for candidate in ["randomized", "cohort", "case-control", "cross-sectional", "systematic review", "meta-analysis"]:
            if candidate in lowered:
                return candidate
        return None
    if name == "sample":
        match = re.search(r"\b(?:n|sample size)\s*[=:]\s*(\d+)", lowered)
        return match.group(1) if match else None
    if name == "intervention":
        match = re.search(r"\bintervention[s]?:\s*([^\n.]+)", text, re.IGNORECASE)
        return match.group(1).strip() if match else None
    if name == "comparator":
        match = re.search(r"\bcomparator[s]?:\s*([^\n.]+)", text, re.IGNORECASE)
        return match.group(1).strip() if match else None
    if name == "outcomes":
        match = re.search(r"\boutcome[s]?:\s*([^\n.]+)", text, re.IGNORECASE)
        return match.group(1).strip() if match else None
    if name == "results":
        match = re.search(r"\bresults?\b[:\s]*([^\n]{20,250})", text, re.IGNORECASE)
        return match.group(1).strip() if match else None
    if name == "follow_up":
        match = re.search(r"\bfollow[- ]?up\b[:\s]*([^\n.]+)", text, re.IGNORECASE)
        return match.group(1).strip() if match else None
    if name == "limitations":
        match = re.search(r"\blimitations?\b[:\s]*([^\n]{15,250})", text, re.IGNORECASE)
        return match.group(1).strip() if match else None
    if name == "conclusion":
        match = re.search(r"\bconclusions?\b[:\s]*([^\n]{15,250})", text, re.IGNORECASE)
        return match.group(1).strip() if match else None
    if name == "population":
        match = re.search(r"\bparticipants?\b[:\s]*([^\n.]+)", text, re.IGNORECASE)
        return match.group(1).strip() if match else None
    return None


def _validate_field(name: str, value: str | None) -> list[str]:
    issues: list[str] = []
    if not value:
        return issues
    if name == "year":
        if not re.fullmatch(r"(19|20)\d{2}", value.strip()):
            issues.append("invalid_year")
    if name == "sample":
        if not re.fullmatch(r"\d+", value.strip()):
            issues.append("invalid_sample_size")
    if name in CONTROLLED_VOCAB and value.lower() not in CONTROLLED_VOCAB[name]:
        issues.append("outside_controlled_vocab")
    return issues


async def create_extraction_record(
    db: AsyncSession,
    *,
    project_id: UUID,
    paper_id: UUID | None,
    template_id: UUID | None,
) -> ExtractionRecord:
    template = await ensure_builtin_template(db) if template_id is None else await db.get(ExtractionTemplate, template_id)
    if template is None:
        raise ValueError("Extraction template not found")

    paper = await db.get(Paper, paper_id) if paper_id else None
    text = paper.full_text_extracted or "" if paper else ""
    chunks: list[PaperChunk] = []
    if paper_id is not None:
        chunks_q = await db.execute(select(PaperChunk).where(PaperChunk.paper_id == paper_id).order_by(PaperChunk.page_number, PaperChunk.chunk_index))
        chunks = chunks_q.scalars().all()

    record = ExtractionRecord(
        project_id=project_id,
        paper_id=paper_id,
        template_id=template.id,
        status="ready" if paper else "draft",
        summary_json={
            "field_count": len(UNIVERSAL_FIELDS),
            "paper_title": paper.title if paper else None,
            "template_version": template.schema_json.get("version", "unversioned"),
        },
    )
    db.add(record)
    await db.flush()

    for field_name in UNIVERSAL_FIELDS:
        value = _extract_value(field_name, paper, text) if paper else None
        page, locator = _first_matching_chunk(chunks, [value or field_name]) if chunks else (None, None)
        candidate_spans = _candidate_spans(chunks, field_name=field_name, value=value)
        validations = _validate_field(field_name, value)
        db.add(
            ExtractionFieldValue(
                record_id=record.id,
                field_name=field_name,
                value_text=value,
                auto_value_text=value,
                confidence=0.8 if value and not validations else (0.55 if value else 0.1),
                source_page=page,
                source_locator=locator,
                metadata_json={"candidate_spans": candidate_spans, "validation_issues": validations},
                manually_edited=False,
            )
        )
    await db.commit()
    stmt = (
        select(ExtractionRecord)
        .where(ExtractionRecord.id == record.id)
        .options(selectinload(ExtractionRecord.field_values))
    )
    hydrated = await db.execute(stmt)
    return hydrated.scalars().first()


async def list_records(db: AsyncSession, *, project_id: UUID) -> list[ExtractionRecord]:
    stmt = (
        select(ExtractionRecord)
        .where(ExtractionRecord.project_id == project_id)
        .options(selectinload(ExtractionRecord.field_values))
        .order_by(ExtractionRecord.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def patch_record(db: AsyncSession, *, record: ExtractionRecord, status: str | None, fields: dict) -> ExtractionRecord:
    if status is not None:
        record.status = status
    if fields:
        field_map = {field.field_name: field for field in record.field_values}
        for field_name, payload in fields.items():
            current = field_map.get(field_name)
            if current is None:
                current = ExtractionFieldValue(record_id=record.id, field_name=field_name)
                db.add(current)
                field_map[field_name] = current
            if payload.value_text is not None:
                current.value_text = payload.value_text
                current.manually_edited = True
            if payload.confidence is not None:
                current.confidence = payload.confidence
            if payload.source_page is not None:
                current.source_page = payload.source_page
            if payload.source_locator is not None:
                current.source_locator = payload.source_locator
            meta = dict(current.metadata_json or {})
            meta["diff"] = {"auto": current.auto_value_text, "current": current.value_text}
            meta["validation_issues"] = _validate_field(field_name, current.value_text)
            meta["candidate_spans"] = meta.get("candidate_spans", [])
            current.metadata_json = meta
    record.version += 1
    await db.commit()
    await db.refresh(record)
    return record


def export_records(records: list[ExtractionRecord], fmt: str) -> Response:
    rows: list[dict] = []
    for record in records:
        row = {"record_id": str(record.id), "project_id": str(record.project_id), "paper_id": str(record.paper_id) if record.paper_id else None}
        for field in record.field_values:
            row[field.field_name] = field.value_text
        rows.append(row)

    if fmt == "json":
        return JSONResponse(rows)
    if fmt == "csv":
        output = io.StringIO()
        fieldnames = sorted({key for row in rows for key in row.keys()}) if rows else ["record_id", "project_id", "paper_id"]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        return Response(output.getvalue(), media_type="text/csv")
    if fmt == "xlsx":
        import pandas as pd

        df = pd.DataFrame(rows)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="extraction", index=False)
        return Response(
            buffer.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    raise ValueError("Unsupported export format")
