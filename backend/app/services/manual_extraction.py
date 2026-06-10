"""Manual / imported extraction entry.

Lets an analyst who already has extracted data (the common expert workflow:
data prepared in a spreadsheet or another tool) create studies and effect
sizes directly, without the LLM PDF-extraction batch path. This makes the
whole synthesis pipeline — matrix -> dataset -> meta-run -> forest plot ->
export — usable fully offline.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.meta_extractor import ExtractedEffectSize, ExtractedStudy
from app.models.paper import Paper


# Effect columns we accept verbatim from a payload, mapped onto the ORM model.
_NUMERIC_EFFECT_FIELDS = (
    "a_events", "b_non_events", "c_events", "d_non_events", "events_total", "total_n",
    "or_value", "log_or", "se_log_or", "effect_value", "effect_se", "weight",
    "ci_lower_95", "ci_upper_95", "adjusted_or", "adjusted_rr", "adjusted_hr",
    "n_intervention", "n_control", "mean_intervention", "sd_intervention",
    "mean_control", "sd_control", "median_intervention", "median_control",
    "followup_time", "person_time_intervention", "person_time_control",
    "tp", "fp", "fn", "tn", "sensitivity_value", "specificity_value", "subgroup_order",
)
_TEXT_EFFECT_FIELDS = (
    "timepoint", "outcome_unit", "comparator_type", "effect_direction",
    "iqr_intervention", "iqr_control", "followup_unit", "subgroup_label",
    "subgroup_level", "sensitivity_reason", "analysis_population", "model_type",
    "comments",
)


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def build_effect(study_id: UUID, payload: dict[str, Any]) -> ExtractedEffectSize:
    """Construct an ExtractedEffectSize from a flat payload, validating required fields."""
    for required in ("outcome_name", "arm_intervention", "arm_control"):
        if not payload.get(required):
            raise ValueError(f"{required} es requerido para cada efecto")

    eff = ExtractedEffectSize(
        extracted_study_id=study_id,
        outcome_name=str(payload["outcome_name"]),
        arm_intervention=str(payload["arm_intervention"]),
        arm_control=str(payload["arm_control"]),
        effect_measure=str(payload.get("effect_measure") or "OR").upper(),
        outcome_type=str(payload.get("outcome_type") or "binary").lower(),
        sensitivity_flag=bool(payload.get("sensitivity_flag") or False),
        covariates_json=payload.get("covariates_json"),
        raw_extracted_value=payload.get("raw_extracted_value"),
        source_page=payload.get("source_page"),
        manually_edited=True,
        edited_at=datetime.now(timezone.utc),
        confidence=_to_float(payload.get("confidence")) or 1.0,
    )
    for field in _NUMERIC_EFFECT_FIELDS:
        if field in payload:
            setattr(eff, field, _to_float(payload.get(field)))
    for field in _TEXT_EFFECT_FIELDS:
        if payload.get(field) is not None:
            setattr(eff, field, payload.get(field))
    return eff


async def _ensure_paper(
    db: AsyncSession,
    *,
    project_id: UUID,
    paper_id: UUID | None,
    study: dict[str, Any],
) -> Paper:
    """Reuse an existing paper or mint a lightweight provenance record for the study."""
    if paper_id is not None:
        paper = await db.get(Paper, paper_id)
        if paper is None or paper.project_id != project_id:
            raise ValueError("paper_id no pertenece al proyecto")
        return paper

    label = str(study.get("study_label") or study.get("title") or "Estudio importado").strip()
    seed = f"{project_id}:{label}:{study.get('doi') or study.get('pmid') or uuid4()}"
    content_hash = hashlib.sha256(seed.encode()).hexdigest()

    existing = await db.execute(
        select(Paper).where(Paper.project_id == project_id, Paper.content_hash == content_hash).limit(1)
    )
    found = existing.scalars().first()
    if found is not None:
        return found

    paper = Paper(
        project_id=project_id,
        title=label,
        authors=study.get("authors"),
        doi=study.get("doi"),
        pmid=str(study["pmid"]) if study.get("pmid") else None,
        filename=f"{label[:60]}.manual",
        file_path=f"manual/{content_hash[:16]}",
        content_hash=content_hash,
        processing_status="manual",
        is_processed=True,
    )
    db.add(paper)
    await db.flush()
    return paper


async def create_study(
    db: AsyncSession,
    *,
    project_id: UUID,
    paper_id: UUID | None,
    study: dict[str, Any],
    effects: list[dict[str, Any]],
) -> ExtractedStudy:
    """Create one manually-entered study with its effect sizes."""
    paper = await _ensure_paper(db, project_id=project_id, paper_id=paper_id, study=study)

    study_json = {
        "label": study.get("study_label") or study.get("title") or paper.title,
        "design": study.get("design"),
        "authors": study.get("authors"),
        "year": study.get("year"),
        "country": study.get("country"),
        "population": study.get("population"),
        "notes": study.get("notes"),
        "source": "manual",
    }
    record = ExtractedStudy(
        project_id=project_id,
        paper_id=paper.id,
        version=1,
        is_current=True,
        study_json={k: v for k, v in study_json.items() if v is not None},
        extraction_confidence=1.0,
    )
    db.add(record)
    await db.flush()

    for effect_payload in effects:
        db.add(build_effect(record.id, effect_payload))

    await db.flush()
    return record


async def import_studies(
    db: AsyncSession,
    *,
    project_id: UUID,
    studies: list[dict[str, Any]],
) -> list[ExtractedStudy]:
    """Bulk-import studies (each with embedded `effects`)."""
    if not studies:
        raise ValueError("No se proporcionaron estudios para importar")

    created: list[ExtractedStudy] = []
    for entry in studies:
        effects = entry.get("effects") or []
        if not isinstance(effects, list):
            raise ValueError("`effects` debe ser una lista")
        record = await create_study(
            db,
            project_id=project_id,
            paper_id=UUID(entry["paper_id"]) if entry.get("paper_id") else None,
            study=entry,
            effects=effects,
        )
        created.append(record)

    await db.commit()
    return created
