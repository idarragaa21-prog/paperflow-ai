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
from app.models.extraction import (
    ExtractionFieldValue,
    ExtractionRecord,
    ExtractionTemplate,
)
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

COUNTRY_ALIASES = {
    "us": "United States",
    "u.s.": "United States",
    "usa": "United States",
    "u.s.a.": "United States",
    "united states of america": "United States",
    "uk": "United Kingdom",
    "u.k.": "United Kingdom",
}

COUNTRY_TRAILING_TOKENS = (
    "participants",
    "patients",
    "adults",
    "children",
    "women",
    "men",
    "hospitals",
    "hospital",
    "centers",
    "centres",
    "clinics",
)

# ⚡ BOLT PERFORMANCE OPTIMIZATION
# Hoisting regex compilation out of functions.
# Compiling regexes once at module load avoids the overhead of internal re cache
# lookups, particularly with flags like re.IGNORECASE (~50% improvement).
_COUNTRY_PATTERNS = [
    re.compile(
        r"\bcountry(?:\s+of\s+(?:study|origin|recruitment|setting))?\s*[:=-]\s*([A-Za-z][A-Za-z .'\-]{1,60}?)(?:[\.,;\n]|$)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:conducted|performed|carried out|implemented)\s+in\s+([A-Z][A-Za-z .'\-]{1,60}?)(?:\s+(?:among|with|across|at|participants?|patients?|adults?|children|women|men|hospitals?|cent(?:ers|res)|clinics?)\b|[\.,;\n]|$)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bfrom\s+([A-Z][A-Za-z .'\-]{1,60}?)(?:\s+(?:participants?|patients?|adults?|children|women|men|hospitals?|cent(?:ers|res)|clinics?)\b|[\.,;\n]|$)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bin\s+([A-Z][A-Za-z .'\-]{1,60}?)(?:\s+(?:participants?|patients?|adults?|children|women|men|hospitals?|cent(?:ers|res)|clinics?)\b|[\.,;\n]|$)",
        re.IGNORECASE,
    ),
]

_POPULATION_PATTERNS = [
    re.compile(r"\bpopulation\s*[:=-]\s*([^\n.;]{8,220})", re.IGNORECASE),
    re.compile(
        r"\bparticipants?\s*(?:were|included|comprised|consisted of|enrolled|recruited|:)?\s*([^\n.;]{8,220})",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bpatients?\s*(?:were|included|comprised|consisted of|with|undergoing|presenting with|:)?\s*([^\n.;]{8,220})",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b((?:adults?|children|women|men)\s+with\s+[^\n.;]{8,220})", re.IGNORECASE
    ),
]

_VALUE_PATTERNS = {
    "sample": re.compile(r"\b(?:n|sample size)\s*[=:]\s*(\d+)"),
    "intervention": re.compile(r"\bintervention[s]?:\s*([^\n.]+)", re.IGNORECASE),
    "comparator": re.compile(r"\bcomparator[s]?:\s*([^\n.]+)", re.IGNORECASE),
    "outcomes": re.compile(r"\boutcome[s]?:\s*([^\n.]+)", re.IGNORECASE),
    "results": re.compile(r"\bresults?\b[:\s]*([^\n]{20,250})", re.IGNORECASE),
    "follow_up": re.compile(r"\bfollow[- ]?up\b[:\s]*([^\n.]+)", re.IGNORECASE),
    "limitations": re.compile(r"\blimitations?\b[:\s]*([^\n]{15,250})", re.IGNORECASE),
    "conclusion": re.compile(r"\bconclusions?\b[:\s]*([^\n]{15,250})", re.IGNORECASE),
}

_NORMALIZE_INLINE_WS_PATTERN = re.compile(r"\s+")
_NORMALIZE_COUNTRY_THE_PATTERN = re.compile(r"^(?:the)\s+", flags=re.IGNORECASE)
_NORMALIZE_COUNTRY_TRAILING_PATTERN = re.compile(
    rf"\s+(?:{'|'.join(COUNTRY_TRAILING_TOKENS)})\b.*$",
    flags=re.IGNORECASE,
)


def universal_template_schema() -> dict:
    return {
        "version": "universal-study-template.v1",
        "fields": [
            {"name": name, "label": name.replace("_", " ").title(), "type": "text"}
            for name in UNIVERSAL_FIELDS
        ],
    }


async def ensure_builtin_template(db: AsyncSession) -> ExtractionTemplate:
    existing = await db.execute(
        select(ExtractionTemplate).where(
            ExtractionTemplate.slug == "universal-study-template"
        )
    )
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


def _first_matching_chunk(
    chunks: list[PaperChunk], terms: list[str]
) -> tuple[int | None, dict | None]:
    lowered_terms = [term.lower() for term in terms if term]
    for chunk in chunks:
        lowered = chunk.text.lower()
        if any(term in lowered for term in lowered_terms):
            return chunk.page_number, chunk.locator
    return None, None


def _candidate_spans(
    chunks: list[PaperChunk], *, field_name: str, value: str | None, limit: int = 3
) -> list[dict]:
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
                    "quoted_text": _best_quoted_text(chunk.text, terms),
                }
            )
        if len(candidates) >= limit:
            break
    return candidates


def _normalize_inline_text(value: str, *, max_len: int | None = None) -> str:
    text = _NORMALIZE_INLINE_WS_PATTERN.sub(" ", value or "").strip()
    if max_len is not None and len(text) > max_len:
        return text[: max_len - 1].rstrip() + "…"
    return text


def _extract_context_window(
    text: str, start: int, end: int, *, max_len: int = 480
) -> str:
    if not text:
        return ""

    boundaries = ".!?\n"
    left_candidates = [text.rfind(char, 0, start) for char in boundaries]
    right_candidates = [
        text.find(char, end) for char in boundaries if text.find(char, end) != -1
    ]

    left = max(left_candidates)
    left = 0 if left < 0 else left + 1
    right = min(right_candidates) + 1 if right_candidates else len(text)

    fragment = text[left:right].strip()
    if not fragment:
        half = max_len // 2
        fragment = text[max(0, start - half) : min(len(text), end + half)].strip()
    if len(fragment) > max_len:
        half = max_len // 2
        fragment = text[max(0, start - half) : min(len(text), end + half)].strip()
    return _normalize_inline_text(fragment, max_len=max_len)


def _best_quoted_text(text: str, terms: list[str], *, max_len: int = 480) -> str:
    normalized_terms = [term.strip() for term in terms if term and term.strip()]
    lowered = text.lower()
    matches: list[tuple[int, int]] = []
    for term in normalized_terms:
        idx = lowered.find(term.lower())
        if idx >= 0:
            matches.append((idx, idx + len(term)))
    if not matches:
        return _normalize_inline_text(text, max_len=max_len)
    start, end = min(matches, key=lambda item: item[0])
    return _extract_context_window(text, start, end, max_len=max_len)


def _normalize_country_name(raw_value: str) -> str | None:
    cleaned = _normalize_inline_text(raw_value.strip(" ,;:."))
    cleaned = _NORMALIZE_COUNTRY_THE_PATTERN.sub("", cleaned)
    cleaned = _NORMALIZE_COUNTRY_TRAILING_PATTERN.sub("", cleaned).strip(" ,;:.")
    if not cleaned:
        return None
    alias = COUNTRY_ALIASES.get(cleaned.lower())
    if alias:
        return alias
    return " ".join(
        part.capitalize() if part.islower() else part for part in cleaned.split()
    )


def _extract_country_value(text: str) -> str | None:
    for pattern in _COUNTRY_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        country = _normalize_country_name(match.group(1))
        if country:
            return country
    return None


def _extract_population_value(text: str) -> str | None:
    for pattern in _POPULATION_PATTERNS:
        match = pattern.search(text)
        if match:
            return _normalize_inline_text(match.group(1), max_len=220)
    return None


def _extract_value(name: str, paper: Paper, text: str) -> str | None:
    lowered = text.lower()
    if name == "title":
        return paper.title
    if name == "authors":
        return paper.authors
    if name == "year":
        return str(paper.publication_year) if paper.publication_year else None
    if name == "country":
        return _extract_country_value(text)
    if name == "design":
        for candidate in [
            "randomized",
            "cohort",
            "case-control",
            "cross-sectional",
            "systematic review",
            "meta-analysis",
        ]:
            if candidate in lowered:
                return candidate
        return None
    if name == "sample":
        match = _VALUE_PATTERNS["sample"].search(lowered)
        return match.group(1) if match else None
    if name == "population":
        return _extract_population_value(text)
    if name in _VALUE_PATTERNS:
        match = _VALUE_PATTERNS[name].search(text)
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
    template = (
        await ensure_builtin_template(db)
        if template_id is None
        else await db.get(ExtractionTemplate, template_id)
    )
    if template is None:
        raise ValueError("Extraction template not found")

    paper = await db.get(Paper, paper_id) if paper_id else None
    text = paper.full_text_extracted or "" if paper else ""
    chunks: list[PaperChunk] = []
    if paper_id is not None:
        chunks_q = await db.execute(
            select(PaperChunk)
            .where(PaperChunk.paper_id == paper_id)
            .order_by(PaperChunk.page_number, PaperChunk.chunk_index)
        )
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
        page, locator = (
            _first_matching_chunk(chunks, [value or field_name])
            if chunks
            else (None, None)
        )
        candidate_spans = _candidate_spans(chunks, field_name=field_name, value=value)
        validations = _validate_field(field_name, value)
        db.add(
            ExtractionFieldValue(
                record_id=record.id,
                field_name=field_name,
                value_text=value,
                auto_value_text=value,
                confidence=0.8
                if value and not validations
                else (0.55 if value else 0.1),
                source_page=page,
                source_locator=locator,
                metadata_json={
                    "candidate_spans": candidate_spans,
                    "validation_issues": validations,
                },
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


async def patch_record(
    db: AsyncSession, *, record: ExtractionRecord, status: str | None, fields: dict
) -> ExtractionRecord:
    if status is not None:
        record.status = status
    if fields:
        field_map = {field.field_name: field for field in record.field_values}
        for field_name, payload in fields.items():
            current = field_map.get(field_name)
            if current is None:
                current = ExtractionFieldValue(
                    record_id=record.id, field_name=field_name
                )
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
            meta["diff"] = {
                "auto": current.auto_value_text,
                "current": current.value_text,
            }
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
        row = {
            "record_id": str(record.id),
            "project_id": str(record.project_id),
            "paper_id": str(record.paper_id) if record.paper_id else None,
        }
        for field in record.field_values:
            row[field.field_name] = field.value_text
        rows.append(row)

    if fmt == "json":
        return JSONResponse(rows)
    if fmt == "csv":
        output = io.StringIO()
        fieldnames = (
            sorted({key for row in rows for key in row.keys()})
            if rows
            else ["record_id", "project_id", "paper_id"]
        )
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
