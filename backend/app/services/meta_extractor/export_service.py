from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import storage_manager
from app.models.meta_export import MetaExport
from app.models.meta_extractor import ExtractedEffectSize, ExtractedRiskOfBias, ExtractedStudy
from app.services.meta_extractor.excel_export import ExcelExportInput, build_meta_xlsx


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

    study_rows: list[dict[str, Any]] = []
    arm_rows: list[dict[str, Any]] = []
    outcome_rows: list[dict[str, Any]] = []
    effect_rows: list[dict[str, Any]] = []
    rob_rows: list[dict[str, Any]] = []

    for s in studies:
        sj = s.study_json or {}
        provenance = {
            "pages_used": sj.get("_pages_used") or [],
            "tables_used": sj.get("_tables_used") or [],
            "ocr_used": bool(sj.get("_ocr_used", False)),
        }
        study_rows.append(
            {
                "study_id": str(s.id),
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
                "provenance": __import__("json").dumps(provenance, ensure_ascii=False),
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

        qeff = await db.execute(select(ExtractedEffectSize).where(ExtractedEffectSize.extracted_study_id == s.id))
        for e in qeff.scalars().all():
            effect_rows.append(
                {
                    "effect_id": str(e.id),
                    "study_id": str(s.id),
                    "outcome_name": e.outcome_name,
                    "timepoint": e.timepoint,
                    "arm_intervention": e.arm_intervention,
                    "arm_control": e.arm_control,
                    "effect_measure": e.effect_measure,
                    "a_events": e.a_events,
                    "b_non_events": e.b_non_events,
                    "c_events": e.c_events,
                    "d_non_events": e.d_non_events,
                    "continuity_correction_used": None,
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
                    "source_type": e.source_type,
                    "extraction_confidence": e.confidence,
                    "comments": e.comments,
                    "manually_edited": bool(e.manually_edited),
                    "edited_at": e.edited_at.isoformat() if e.edited_at else None,
                    "p_value": None,
                    "n_intervention_for_outcome": None,
                    "n_control_for_outcome": None,
                    "events_intervention": None,
                    "events_control": None,
                    "mean_intervention": None,
                    "sd_intervention": None,
                    "mean_control": None,
                    "sd_control": None,
                    "median_intervention": None,
                    "iqr_intervention": None,
                    "median_control": None,
                    "iqr_control": None,
                    "mean_difference": None,
                    "sd_difference": None,
                    "nnt": None,
                    "absolute_risk_reduction": None,
                    "relative_risk_reduction": None,
                    "heterogeneity_subgroup": None,
                    "sensitivity_analysis": None,
                    "analysis_method": None,
                    "model_type": None,
                    "intention_to_treat": None,
                }
            )

        qrob = await db.execute(select(ExtractedRiskOfBias).where(ExtractedRiskOfBias.extracted_study_id == s.id))
        for r in qrob.scalars().all():
            rob_rows.append(
                {
                    "rob_id": str(r.id),
                    "study_id": str(s.id),
                    "tool": r.tool,
                    "domain_name": r.domain,
                    "judgement": r.judgement,
                    "support_for_judgement": r.support_text,
                    "manually_edited": bool(r.manually_edited),
                    "edited_at": r.edited_at.isoformat() if r.edited_at else None,
                }
            )

    return ExcelExportInput(
        studies=study_rows,
        arms=arm_rows,
        outcomes=outcome_rows,
        effects=effect_rows,
        rob=rob_rows,
        tables_raw=[],
        images_ocr_raw=[],
        logs=[],
    )


async def create_meta_export(
    *,
    db: AsyncSession,
    project_id: UUID,
    batch_id: UUID | None,
) -> MetaExport:
    payload = await build_export_payload(db=db, project_id=project_id, batch_id=batch_id)
    xlsx_bytes = build_meta_xlsx(payload)

    # save under slides/?? We'll store under notes-like directory: meta_exports
    safe_filename = f"meta_export_{project_id}_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}.xlsx"
    # Use StorageManager base_dir directly
    rel_dir = Path("meta_exports") / str(project_id)
    abs_dir = (storage_manager.base_dir / rel_dir).resolve()
    abs_dir.mkdir(parents=True, exist_ok=True)

    abs_path = (abs_dir / safe_filename).resolve()
    abs_path.relative_to(storage_manager.base_dir)
    abs_path.write_bytes(xlsx_bytes)

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
