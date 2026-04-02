from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import storage_manager
from app.models.meta_export import MetaExport
from app.models.meta_extractor import ExtractedEffectSize, ExtractedRiskOfBias, ExtractedStudy
from app.models.paper import Paper
from app.services.meta_extractor.excel_export import ExcelExportInput, build_meta_csv_bundle, build_meta_xlsx


def _json_text(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False)


def _effect_key_from_payload(raw: dict[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        str(raw.get("outcome_name") or ""),
        str(raw.get("timepoint") or ""),
        str(raw.get("arm_intervention") or ""),
        str(raw.get("arm_control") or ""),
        str(raw.get("effect_measure") or ""),
    )


def _effect_key_from_model(effect: ExtractedEffectSize) -> tuple[str, str, str, str, str]:
    return (
        str(effect.outcome_name or ""),
        str(effect.timepoint or ""),
        str(effect.arm_intervention or ""),
        str(effect.arm_control or ""),
        str(effect.effect_measure or ""),
    )


def _effect_fallback_key_from_payload(raw: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(raw.get("outcome_name") or ""),
        str(raw.get("timepoint") or ""),
        str(raw.get("arm_intervention") or ""),
        str(raw.get("arm_control") or ""),
    )


def _effect_fallback_key_from_model(effect: ExtractedEffectSize) -> tuple[str, str, str, str]:
    return (
        str(effect.outcome_name or ""),
        str(effect.timepoint or ""),
        str(effect.arm_intervention or ""),
        str(effect.arm_control or ""),
    )


def _rob_key_from_payload(raw: dict[str, Any]) -> tuple[str, str]:
    return (str(raw.get("tool") or ""), str(raw.get("domain_name") or ""))


def _rob_key_from_model(rob: ExtractedRiskOfBias) -> tuple[str, str]:
    return (str(rob.tool or ""), str(rob.domain or ""))


def _claim_first_unused(candidates: list[tuple[int, dict[str, Any]]], used_indexes: set[int]) -> dict[str, Any] | None:
    for index, row in candidates:
        if index not in used_indexes:
            used_indexes.add(index)
            return row
    return None


def _raw_effect_row(*, study_id: UUID, raw: dict[str, Any], effect_id: str) -> dict[str, Any]:
    source_locator = {
        "table_id": raw.get("table_id"),
        "figure_id": raw.get("figure_id"),
        "page_number": raw.get("page_number"),
    }
    source_locator = {k: v for k, v in source_locator.items() if v is not None}
    return {
        "effect_id": effect_id,
        "study_id": str(study_id),
        "outcome_name": raw.get("outcome_name"),
        "timepoint": raw.get("timepoint"),
        "arm_intervention": raw.get("arm_intervention"),
        "arm_control": raw.get("arm_control"),
        "effect_measure": raw.get("effect_measure"),
        "a_events": raw.get("a_events"),
        "b_non_events": raw.get("b_non_events"),
        "c_events": raw.get("c_events"),
        "d_non_events": raw.get("d_non_events"),
        "continuity_correction_used": raw.get("continuity_correction_used"),
        "or_value": raw.get("or_value"),
        "log_or": raw.get("log_or"),
        "se_log_or": raw.get("se_log_or"),
        "ci_lower_95": raw.get("ci_lower_95"),
        "ci_upper_95": raw.get("ci_upper_95"),
        "adjusted_or": raw.get("adjusted_or"),
        "adjusted_rr": raw.get("adjusted_rr"),
        "adjusted_hr": raw.get("adjusted_hr"),
        "adjustment_variables": raw.get("adjustment_variables"),
        "is_adjusted": raw.get("is_adjusted"),
        "raw_extracted_value": raw.get("raw_extracted_value"),
        "page_number": raw.get("page_number"),
        "table_id": raw.get("table_id"),
        "figure_id": raw.get("figure_id"),
        "source_locator_json": _json_text(source_locator) if source_locator else None,
        "source_type": raw.get("source_type"),
        "extraction_confidence": raw.get("extraction_confidence"),
        "comments": raw.get("comments"),
        "manually_edited": False,
        "edited_at": None,
        "p_value": raw.get("p_value"),
        "n_intervention_for_outcome": raw.get("n_intervention_for_outcome"),
        "n_control_for_outcome": raw.get("n_control_for_outcome"),
        "events_intervention": raw.get("events_intervention"),
        "events_control": raw.get("events_control"),
        "mean_intervention": raw.get("mean_intervention"),
        "sd_intervention": raw.get("sd_intervention"),
        "mean_control": raw.get("mean_control"),
        "sd_control": raw.get("sd_control"),
        "median_intervention": raw.get("median_intervention"),
        "iqr_intervention": raw.get("iqr_intervention"),
        "median_control": raw.get("median_control"),
        "iqr_control": raw.get("iqr_control"),
        "mean_difference": raw.get("mean_difference"),
        "sd_difference": raw.get("sd_difference"),
        "nnt": raw.get("nnt"),
        "absolute_risk_reduction": raw.get("absolute_risk_reduction"),
        "relative_risk_reduction": raw.get("relative_risk_reduction"),
        "heterogeneity_subgroup": raw.get("heterogeneity_subgroup"),
        "sensitivity_analysis": raw.get("sensitivity_analysis"),
        "analysis_method": raw.get("analysis_method"),
        "model_type": raw.get("model_type"),
        "intention_to_treat": raw.get("intention_to_treat"),
        "raw_effect_json": _json_text(raw),
    }


def _raw_rob_row(*, study_id: UUID, raw: dict[str, Any], rob_id: str) -> dict[str, Any]:
    return {
        "rob_id": rob_id,
        "study_id": str(study_id),
        "tool": raw.get("tool"),
        "domain_name": raw.get("domain_name"),
        "judgement": raw.get("judgement"),
        "support_for_judgement": raw.get("support_for_judgement"),
        "auto_generated": False,
        "manually_edited": False,
        "edited_at": None,
        "raw_rob_json": _json_text(raw),
    }


async def build_export_payload(
    *,
    db: AsyncSession,
    project_id: UUID,
    batch_id: UUID | None,
    only_completed: bool = True,
) -> ExcelExportInput:
    stmt = select(ExtractedStudy).where(ExtractedStudy.project_id == project_id).where(ExtractedStudy.is_current == True)  # noqa
    if batch_id:
        stmt = stmt.where(ExtractedStudy.batch_id == batch_id)

    q = await db.execute(stmt)
    studies = q.scalars().all()

    if not studies:
        raise ValueError("No extracted studies available for export")

    study_rows: list[dict[str, Any]] = []
    arm_rows: list[dict[str, Any]] = []
    outcome_rows: list[dict[str, Any]] = []
    effect_rows: list[dict[str, Any]] = []
    rob_rows: list[dict[str, Any]] = []
    tables_raw_rows: list[dict[str, Any]] = []
    images_ocr_raw_rows: list[dict[str, Any]] = []
    log_rows: list[dict[str, Any]] = []

    paper_map: dict[UUID, Paper] = {}
    paper_ids = [s.paper_id for s in studies if getattr(s, "paper_id", None)]
    if paper_ids:
        papers_result = await db.execute(select(Paper).where(Paper.id.in_(paper_ids)))
        paper_map = {p.id: p for p in papers_result.scalars().all()}

    study_ids = [s.id for s in studies]
    effects_by_study: dict[UUID, list[ExtractedEffectSize]] = defaultdict(list)
    robs_by_study: dict[UUID, list[ExtractedRiskOfBias]] = defaultdict(list)

    if study_ids:
        effects_result = await db.execute(
            select(ExtractedEffectSize).where(ExtractedEffectSize.extracted_study_id.in_(study_ids))
        )
        for effect in effects_result.scalars().all():
            effects_by_study[effect.extracted_study_id].append(effect)

        robs_result = await db.execute(
            select(ExtractedRiskOfBias).where(ExtractedRiskOfBias.extracted_study_id.in_(study_ids))
        )
        for rob in robs_result.scalars().all():
            robs_by_study[rob.extracted_study_id].append(rob)

    for s in studies:
        sj = s.study_json or {}
        paper = paper_map.get(s.paper_id)
        provenance = {
            "pages_used": sj.get("_pages_used") or [],
            "tables_used": sj.get("_tables_used") or [],
            "ocr_used": bool(sj.get("_ocr_used", False)),
            "warnings": sj.get("_extraction_warnings") or [],
        }
        study_rows.append(
            {
                "study_id": str(s.id),
                "paper_id": str(s.paper_id),
                "batch_id": str(s.batch_id) if s.batch_id else None,
                "paper_title": getattr(paper, "title", None),
                "paper_filename": getattr(paper, "filename", None),
                "paper_authors": getattr(paper, "authors", None),
                "paper_doi": getattr(paper, "doi", None),
                "paper_pmid": getattr(paper, "pmid", None),
                "paper_pmcid": getattr(paper, "pmcid", None),
                "paper_journal": getattr(paper, "journal", None),
                "paper_publication_year": getattr(paper, "publication_year", None),
                "paper_source_provider": getattr(paper, "source_provider", None),
                "paper_oa_url": getattr(paper, "oa_url", None),
                "citation_key": sj.get("citation_key"),
                "title": sj.get("title"),
                "first_author": sj.get("first_author"),
                "year": sj.get("year"),
                "journal": sj.get("journal"),
                "doi": sj.get("doi"),
                "pmid": sj.get("pmid"),
                "pmcid": sj.get("pmcid"),
                "country": sj.get("country"),
                "centers": sj.get("centers"),
                "study_design": sj.get("study_design"),
                "recruitment_dates": sj.get("recruitment_dates"),
                "follow_up_duration": sj.get("follow_up_duration"),
                "population_description": sj.get("population_description"),
                "inclusion_criteria": sj.get("inclusion_criteria"),
                "exclusion_criteria": sj.get("exclusion_criteria"),
                "baseline_balance_notes": sj.get("baseline_balance_notes"),
                "funding": sj.get("funding"),
                "conflicts_of_interest": sj.get("conflicts_of_interest"),
                "registration": sj.get("registration"),
                "notes": sj.get("notes"),
                "total_sample_size": sj.get("total_sample_size"),
                "total_n_intervention": sj.get("total_n_intervention"),
                "total_n_control": sj.get("total_n_control"),
                "mean_age_total": sj.get("mean_age_total"),
                "percent_female_total": sj.get("percent_female_total"),
                "setting": sj.get("setting"),
                "geographic_region": sj.get("geographic_region"),
                "income_level": sj.get("income_level"),
                "language_of_publication": sj.get("language_of_publication"),
                "peer_reviewed": sj.get("peer_reviewed"),
                "extraction_confidence": s.extraction_confidence,
                "provenance": json.dumps(provenance, ensure_ascii=False),
                "study_created_at": s.created_at.isoformat() if getattr(s, "created_at", None) else None,
                "study_updated_at": s.updated_at.isoformat() if getattr(s, "updated_at", None) else None,
                "raw_study_json": json.dumps(sj, ensure_ascii=False),
            }
        )

        # arms/outcomes from study_json (write only known keys)
        for idx, a in enumerate(sj.get("arms") or [], 1):
            arm_rows.append(
                {
                    "arm_id": f"{s.id}-A{idx}",
                    "study_id": str(s.id),
                    "arm_name": a.get("arm_name"),
                    "intervention_description": a.get("intervention_description"),
                    "dose_intensity": a.get("dose_intensity"),
                    "cointerventions": a.get("cointerventions"),
                    "n_randomized": a.get("n_randomized"),
                    "n_analyzed": a.get("n_analyzed"),
                    "losses_to_followup_n": a.get("losses_to_followup_n"),
                    "losses_to_followup_reasons": a.get("losses_to_followup_reasons"),
                    "mean_age": a.get("mean_age"),
                    "sd_age": a.get("sd_age"),
                    "median_age": a.get("median_age"),
                    "iqr_age": a.get("iqr_age"),
                    "age_range": a.get("age_range"),
                    "percent_female": a.get("percent_female"),
                    "percent_male": a.get("percent_male"),
                    "n_female": a.get("n_female"),
                    "n_male": a.get("n_male"),
                    "mean_bmi": a.get("mean_bmi"),
                    "sd_bmi": a.get("sd_bmi"),
                    "comorbidities": a.get("comorbidities"),
                    "disease_severity": a.get("disease_severity"),
                    "disease_duration": a.get("disease_duration"),
                    "baseline_outcome_value": a.get("baseline_outcome_value"),
                    "previous_treatments": a.get("previous_treatments"),
                    "smoking_status": a.get("smoking_status"),
                    "ethnicity_distribution": a.get("ethnicity_distribution"),
                    "followup_duration_months": a.get("followup_duration_months"),
                    "completion_rate": a.get("completion_rate"),
                    "withdrawal_reasons": a.get("withdrawal_reasons"),
                }
            )

        for idx, o in enumerate(sj.get("outcomes") or [], 1):
            outcome_rows.append(
                {
                    "outcome_id": f"{s.id}-O{idx}",
                    "study_id": str(s.id),
                    "outcome_name": o.get("outcome_name"),
                    "outcome_type": o.get("outcome_type"),
                    "definition": o.get("definition"),
                    "timepoint": o.get("timepoint"),
                    "measurement_instrument": o.get("measurement_instrument"),
                    "outcome_category": o.get("outcome_category"),
                    "direction_of_benefit": o.get("direction_of_benefit"),
                    "how_measured": o.get("how_measured"),
                    "measurement_timepoints": o.get("measurement_timepoints"),
                    "missing_data_handling": o.get("missing_data_handling"),
                }
            )

        raw_effects = list(sj.get("effect_sizes") or [])
        raw_effects_by_key: dict[tuple[str, str, str, str, str], list[tuple[int, dict[str, Any]]]] = defaultdict(list)
        raw_effects_by_fallback: dict[tuple[str, str, str, str], list[tuple[int, dict[str, Any]]]] = defaultdict(list)
        for idx, raw_effect in enumerate(raw_effects):
            raw_effects_by_key[_effect_key_from_payload(raw_effect)].append((idx, raw_effect))
            raw_effects_by_fallback[_effect_fallback_key_from_payload(raw_effect)].append((idx, raw_effect))

        used_raw_effect_indexes: set[int] = set()
        db_effects = effects_by_study.get(s.id, [])
        for e in db_effects:
            raw_effect = _claim_first_unused(raw_effects_by_key[_effect_key_from_model(e)], used_raw_effect_indexes)
            if raw_effect is None:
                raw_effect = _claim_first_unused(raw_effects_by_fallback[_effect_fallback_key_from_model(e)], used_raw_effect_indexes)

            row = _raw_effect_row(study_id=s.id, raw=raw_effect or {}, effect_id=str(e.id))
            row.update(
                {
                    "effect_id": str(e.id),
                    "outcome_name": e.outcome_name,
                    "timepoint": e.timepoint,
                    "arm_intervention": e.arm_intervention,
                    "arm_control": e.arm_control,
                    "effect_measure": e.effect_measure,
                    "a_events": e.a_events,
                    "b_non_events": e.b_non_events,
                    "c_events": e.c_events,
                    "d_non_events": e.d_non_events,
                    "or_value": e.or_value,
                    "log_or": e.log_or,
                    "se_log_or": e.se_log_or,
                    "ci_lower_95": e.ci_lower_95,
                    "ci_upper_95": e.ci_upper_95,
                    "adjusted_or": e.adjusted_or,
                    "adjusted_rr": e.adjusted_rr,
                    "adjusted_hr": e.adjusted_hr,
                    "adjustment_variables": e.adjustment_variables,
                    "is_adjusted": e.is_adjusted,
                    "raw_extracted_value": e.raw_extracted_value,
                    "page_number": e.source_page,
                    "table_id": (e.source_locator or {}).get("table_id") if isinstance(e.source_locator, dict) else None,
                    "figure_id": (e.source_locator or {}).get("figure_id") if isinstance(e.source_locator, dict) else None,
                    "source_locator_json": json.dumps(e.source_locator, ensure_ascii=False) if isinstance(e.source_locator, dict) else None,
                    "source_type": e.source_type,
                    "extraction_confidence": e.confidence,
                    "comments": e.comments,
                    "manually_edited": bool(e.manually_edited),
                    "edited_at": e.edited_at.isoformat() if e.edited_at else None,
                }
            )
            effect_rows.append(row)

        for idx, raw_effect in enumerate(raw_effects):
            if idx in used_raw_effect_indexes:
                continue
            effect_rows.append(
                _raw_effect_row(
                    study_id=s.id,
                    raw=raw_effect,
                    effect_id=f"{s.id}-RAW-E{idx + 1}",
                )
            )

        raw_robs = list(sj.get("risk_of_bias") or [])
        raw_robs_by_key: dict[tuple[str, str], list[tuple[int, dict[str, Any]]]] = defaultdict(list)
        for idx, raw_rob in enumerate(raw_robs):
            raw_robs_by_key[_rob_key_from_payload(raw_rob)].append((idx, raw_rob))

        used_raw_rob_indexes: set[int] = set()
        db_robs = robs_by_study.get(s.id, [])
        for r in db_robs:
            raw_rob = _claim_first_unused(raw_robs_by_key[_rob_key_from_model(r)], used_raw_rob_indexes)
            row = _raw_rob_row(study_id=s.id, raw=raw_rob or {}, rob_id=str(r.id))
            row.update(
                {
                    "rob_id": str(r.id),
                    "tool": r.tool,
                    "domain_name": r.domain,
                    "judgement": r.judgement,
                    "support_for_judgement": r.support_text,
                    "auto_generated": bool(getattr(r, "auto_generated", False)),
                    "manually_edited": bool(r.manually_edited),
                    "edited_at": r.edited_at.isoformat() if r.edited_at else None,
                }
            )
            rob_rows.append(row)

        for idx, raw_rob in enumerate(raw_robs):
            if idx in used_raw_rob_indexes:
                continue
            rob_rows.append(
                _raw_rob_row(
                    study_id=s.id,
                    raw=raw_rob,
                    rob_id=f"{s.id}-RAW-R{idx + 1}",
                )
            )

        for idx, raw_table in enumerate(sj.get("_tables_raw") or [], 1):
            table_row = {
                "table_id": raw_table.get("table_id") or f"{s.id}-T{idx}",
                "study_id": str(s.id),
                "page": raw_table.get("page"),
                "extracted_markdown": raw_table.get("extracted_markdown"),
            }
            if table_row["extracted_markdown"]:
                tables_raw_rows.append(table_row)

        for idx, raw_image in enumerate(sj.get("_images_ocr_raw") or [], 1):
            image_row = {
                "image_id": raw_image.get("image_id") or f"{s.id}-OCR{idx}",
                "study_id": str(s.id),
                "page": raw_image.get("page"),
                "ocr_text": raw_image.get("ocr_text"),
            }
            if image_row["ocr_text"]:
                images_ocr_raw_rows.append(image_row)

        raw_logs = list(sj.get("_extraction_logs") or [])
        if not raw_logs:
            raw_logs = [
                {"level": "warning", "message": warning}
                for warning in (sj.get("_extraction_warnings") or [])
            ]
        for log in raw_logs:
            log_rows.append(
                {
                    "timestamp": log.get("timestamp"),
                    "job_id": log.get("job_id"),
                    "study_id": str(s.id),
                    "level": log.get("level"),
                    "message": log.get("message"),
                }
            )

    return ExcelExportInput(
        studies=study_rows,
        arms=arm_rows,
        outcomes=outcome_rows,
        effects=effect_rows,
        rob=rob_rows,
        tables_raw=tables_raw_rows,
        images_ocr_raw=images_ocr_raw_rows,
        logs=log_rows,
    )


async def create_meta_export(
    *,
    db: AsyncSession,
    project_id: UUID,
    batch_id: UUID | None,
    export_format: Literal["xlsx", "csv"] = "xlsx",
) -> MetaExport:
    payload = await build_export_payload(db=db, project_id=project_id, batch_id=batch_id)
    if export_format == "csv":
        export_bytes = build_meta_csv_bundle(payload)
        extension = "zip"
        format_suffix = "csv_bundle"
    else:
        export_bytes = build_meta_xlsx(payload)
        extension = "xlsx"
        format_suffix = "excel"

    safe_filename = f"meta_export_{project_id}_{format_suffix}_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}.{extension}"
    rel_dir = Path("meta_exports") / str(project_id)
    abs_dir = (storage_manager.base_dir / rel_dir).resolve()
    abs_dir.mkdir(parents=True, exist_ok=True)

    abs_path = (abs_dir / safe_filename).resolve()
    abs_path.relative_to(storage_manager.base_dir)
    abs_path.write_bytes(export_bytes)

    export = MetaExport(
        project_id=project_id,
        batch_id=batch_id,
        filename=safe_filename,
        file_path=str(abs_path.relative_to(storage_manager.base_dir)),
    )
    db.add(export)
    await db.commit()
    await db.refresh(export)
    return export
