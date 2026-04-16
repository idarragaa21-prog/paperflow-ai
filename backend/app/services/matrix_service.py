from __future__ import annotations

import io
import json
from collections import Counter
from datetime import datetime, timezone
from typing import Any
from uuid import UUID
import xml.etree.ElementTree as ET

import pandas as pd
from collections import defaultdict
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


from sqlalchemy.orm import selectinload

from app.models.extraction import ExtractionFieldValue, ExtractionRecord
from app.models.matrix import MatrixProvenance, MatrixRow, MatrixValidationIssue, MatrixVersion
from app.models.meta_extractor import ExtractedEffectSize, ExtractedRiskOfBias, ExtractedStudy
from app.models.paper import Paper


SUPPORTED_MATRIX_EXPORTS = {"xlsx", "csv", "json", "xml"}


def _jsonable(value: Any) -> Any:
    if isinstance(value, (dict, list, str, int, float, bool)) or value is None:
        return value
    if isinstance(value, UUID):
        return str(value)
    return str(value)


def _score_rob(rows: list[ExtractedRiskOfBias]) -> dict[str, Any]:
    if not rows:
        return {"overall": "unclear", "domains": []}
    by_domain = [
        {
            "domain": item.domain,
            "tool": item.tool,
            "judgement": item.judgement,
            "support_text": item.support_text,
        }
        for item in rows
    ]
    counts = Counter((item.judgement or "unclear").lower() for item in rows)
    if counts.get("high", 0) > 0:
        overall = "high"
    elif counts.get("some concerns", 0) > 0:
        overall = "some_concerns"
    elif counts.get("low", 0) > 0 and sum(counts.values()) == counts.get("low", 0):
        overall = "low"
    else:
        overall = "unclear"
    return {"overall": overall, "domains": by_domain}


def _validate_effect(effect_data: dict[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    measure = str(effect_data.get("effect_measure") or "").upper()
    outcome_type = str(effect_data.get("outcome_type") or "").lower()
    is_binary = measure in {"OR", "RR"} or outcome_type == "binary"
    is_survival = measure in {"HR"} or outcome_type in {"time_to_event", "time-to-event", "survival"}
    is_continuous = measure in {"MD", "SMD"} or outcome_type == "continuous"
    is_proportion = measure in {"PROPORTION", "PLOGIT"} or outcome_type == "proportion"
    is_diagnostic = measure in {"DOR", "SENS", "SPEC"} or outcome_type == "diagnostic"

    if is_binary:
        has_event_table = all(effect_data.get(field) is not None for field in ("a_events", "b_non_events", "c_events", "d_non_events"))
        has_generic = effect_data.get("log_or") is not None and effect_data.get("se_log_or") is not None
        if not has_event_table and not has_generic:
            issues.append(
                {
                    "severity": "warning",
                    "code": "binary_effect_missing_inputs",
                    "message": "Binary/time-to-event effect requires event table or log effect + SE.",
                    "field_name": "effect_measure",
                }
            )

    if is_survival:
        has_hr = effect_data.get("adjusted_hr") is not None or effect_data.get("effect_value") is not None
        has_log = effect_data.get("log_or") is not None and effect_data.get("se_log_or") is not None
        if not has_hr and not has_log:
            issues.append(
                {
                    "severity": "warning",
                    "code": "survival_effect_missing_inputs",
                    "message": "Survival effect requires HR/effect_value or log effect + SE.",
                    "field_name": "effect_measure",
                }
            )

    if is_continuous:
        has_arm_stats = all(
            effect_data.get(field) is not None
            for field in ("n_intervention", "n_control", "mean_intervention", "sd_intervention", "mean_control", "sd_control")
        )
        has_generic = effect_data.get("effect_value") is not None and (
            effect_data.get("effect_se") is not None or effect_data.get("se_log_or") is not None
        )
        if not has_arm_stats and not has_generic:
            issues.append(
                {
                    "severity": "warning",
                    "code": "continuous_effect_missing_inputs",
                    "message": "Continuous effect requires arm summary statistics or effect + SE.",
                    "field_name": "effect_measure",
                }
            )

    if is_proportion:
        has_totals = effect_data.get("events_total") is not None and effect_data.get("total_n") is not None
        has_events = effect_data.get("a_events") is not None and effect_data.get("b_non_events") is not None
        if not has_totals and not has_events:
            issues.append(
                {
                    "severity": "warning",
                    "code": "proportion_missing_inputs",
                    "message": "Proportion effect requires events/total or intervention event counts.",
                    "field_name": "effect_measure",
                }
            )

    if is_diagnostic:
        has_2x2 = all(effect_data.get(field) is not None for field in ("tp", "fp", "fn", "tn"))
        has_metrics = effect_data.get("sensitivity_value") is not None and effect_data.get("specificity_value") is not None
        if not has_2x2 and not has_metrics:
            issues.append(
                {
                    "severity": "warning",
                    "code": "diagnostic_missing_inputs",
                    "message": "Diagnostic effect requires TP/FP/FN/TN or sensitivity + specificity.",
                    "field_name": "effect_measure",
                }
            )

    if effect_data.get("effect_se") is not None:
        try:
            if float(effect_data["effect_se"]) <= 0:
                issues.append(
                    {
                        "severity": "warning",
                        "code": "invalid_effect_se",
                        "message": "Standard error must be > 0.",
                        "field_name": "effect_se",
                    }
                )
        except Exception:
            issues.append(
                {
                    "severity": "warning",
                    "code": "non_numeric_effect_se",
                    "message": "Standard error is not numeric.",
                    "field_name": "effect_se",
                }
            )

    if effect_data.get("ci_lower_95") is not None and effect_data.get("ci_upper_95") is not None:
        try:
            lo = float(effect_data["ci_lower_95"])
            hi = float(effect_data["ci_upper_95"])
            if lo > hi:
                issues.append(
                    {
                        "severity": "error",
                        "code": "invalid_confidence_interval",
                        "message": "Lower CI cannot exceed upper CI.",
                        "field_name": "ci_lower_95",
                    }
                )
        except Exception:
            issues.append(
                {
                    "severity": "warning",
                    "code": "non_numeric_confidence_interval",
                    "message": "Confidence interval values are not numeric.",
                    "field_name": "ci_lower_95",
                }
            )

    return issues


async def _next_matrix_version_number(db: AsyncSession, project_id: UUID) -> int:
    q = await db.execute(select(func.max(MatrixVersion.version_number)).where(MatrixVersion.project_id == project_id))
    current = q.scalar()
    return int(current or 0) + 1


async def _unset_current_matrix_versions(db: AsyncSession, project_id: UUID) -> None:
    q = await db.execute(select(MatrixVersion).where(MatrixVersion.project_id == project_id).where(MatrixVersion.is_current == True))  # noqa: E712
    for item in q.scalars().all():
        item.is_current = False
        item.updated_at = datetime.now(timezone.utc)


def _flatten_rows(rows: list[MatrixRow]) -> list[dict[str, Any]]:
    flattened: list[dict[str, Any]] = []
    for row in rows:
        payload = {
            "row_id": str(row.id),
            "matrix_version_id": str(row.matrix_version_id),
            "row_key": row.row_key,
            "row_kind": row.row_kind,
            "outcome_key": row.outcome_key,
            "effect_measure": row.effect_measure,
            "paper_id": str(row.paper_id) if row.paper_id else None,
            "extracted_study_id": str(row.extracted_study_id) if row.extracted_study_id else None,
        }
        for key, value in (row.data_json or {}).items():
            payload[key] = _jsonable(value)
        flattened.append(payload)
    return flattened


async def build_matrix_version(
    db: AsyncSession,
    *,
    project_id: UUID,
    user_id: UUID | None,
) -> MatrixVersion:
    await _unset_current_matrix_versions(db, project_id)
    version = MatrixVersion(
        project_id=project_id,
        created_by_user_id=user_id,
        version_number=await _next_matrix_version_number(db, project_id),
        status="building",
        is_current=True,
    )
    db.add(version)
    await db.flush()

    validation_issues: list[MatrixValidationIssue] = []
    row_count = 0
    effect_count = 0
    study_count = 0
    provenance_count = 0

    studies_q = await db.execute(
        select(ExtractedStudy, Paper)
        .join(Paper, Paper.id == ExtractedStudy.paper_id)
        .where(ExtractedStudy.project_id == project_id)
        .where(ExtractedStudy.is_current == True)  # noqa: E712
        .order_by(ExtractedStudy.created_at.asc())
    )
    studies = studies_q.all()

    study_ids = [study.id for study, _ in studies]

    # Pre-fetch all effects and rob rows for the relevant studies to avoid N+1 queries
    effects_by_study_id = defaultdict(list)
    rob_by_study_id = defaultdict(list)

    if study_ids:
        all_effects_q = await db.execute(
            select(ExtractedEffectSize)
            .where(ExtractedEffectSize.extracted_study_id.in_(study_ids))
            .order_by(ExtractedEffectSize.id.asc())
        )
        for effect in all_effects_q.scalars().all():
            effects_by_study_id[effect.extracted_study_id].append(effect)

        all_rob_q = await db.execute(
            select(ExtractedRiskOfBias)
            .where(ExtractedRiskOfBias.extracted_study_id.in_(study_ids))
            .order_by(ExtractedRiskOfBias.id.asc())
        )
        for rob in all_rob_q.scalars().all():
            rob_by_study_id[rob.extracted_study_id].append(rob)

    for study, paper in studies:
        effects = effects_by_study_id.get(study.id, [])
        rob_rows = rob_by_study_id.get(study.id, [])
        rob_summary = _score_rob(rob_rows)

        study_row = MatrixRow(
            matrix_version_id=version.id,
            project_id=project_id,
            paper_id=paper.id,
            extracted_study_id=study.id,
            row_key=f"study:{study.id}",
            row_kind="study",
            outcome_key=None,
            effect_measure=None,
            sort_index=row_count,
            data_json={
                "study_id": str(study.id),
                "paper_id": str(paper.id),
                "paper_title": paper.title,
                "pmid": paper.pmid,
                "doi": paper.doi,
                "study_version": study.version,
                "study_confidence": study.extraction_confidence,
                "study_json": study.study_json or {},
                "risk_of_bias_overall": rob_summary["overall"],
                "risk_of_bias_domains": rob_summary["domains"],
                "effect_count": len(effects),
            },
        )
        db.add(study_row)
        await db.flush()
        row_count += 1
        study_count += 1

        db.add(
            MatrixProvenance(
                matrix_row_id=study_row.id,
                field_name="study_json",
                source_type="extracted_study",
                source_id=str(study.id),
                source_locator={"kind": "meta_extractor_study"},
                excerpt=(paper.title or "")[:400],
                confidence=float(study.extraction_confidence or 0),
            )
        )
        provenance_count += 1

        if not effects:
            validation_issues.append(
                MatrixValidationIssue(
                    matrix_version_id=version.id,
                    matrix_row_id=study_row.id,
                    severity="warning",
                    code="study_without_effects",
                    message="Study has no extracted effect rows.",
                    field_name=None,
                )
            )

        for effect in effects:
            outcome_base = (effect.outcome_name or "outcome").strip().lower().replace(" ", "_")
            timepoint_key = (effect.timepoint or "not_reported").strip().lower().replace(" ", "_")
            comparison_key = f"{(effect.arm_intervention or 'arm_a').strip().lower().replace(' ', '_')}__vs__{(effect.arm_control or 'arm_b').strip().lower().replace(' ', '_')}"
            measure_key = (effect.effect_measure or "effect").strip().lower()
            outcome_key = f"{outcome_base}::{timepoint_key}::{comparison_key}::{measure_key}"
            canonical_key = (
                f"{paper.id}:{outcome_key}:"
                f"{(effect.subgroup_label or 'all').strip().lower().replace(' ', '_')}:"
                f"{'sens' if effect.sensitivity_flag else 'main'}"
            )
            effect_data = {
                "study_id": str(study.id),
                "effect_id": str(effect.id),
                "canonical_key": canonical_key,
                "paper_id": str(paper.id),
                "paper_title": paper.title,
                "pmid": paper.pmid,
                "doi": paper.doi,
                "outcome_name": effect.outcome_name,
                "timepoint": effect.timepoint,
                "arm_intervention": effect.arm_intervention,
                "arm_control": effect.arm_control,
                "effect_measure": effect.effect_measure,
                "outcome_type": effect.outcome_type,
                "outcome_unit": effect.outcome_unit,
                "comparator_type": effect.comparator_type,
                "effect_direction": effect.effect_direction,
                "a_events": effect.a_events,
                "b_non_events": effect.b_non_events,
                "c_events": effect.c_events,
                "d_non_events": effect.d_non_events,
                "events_total": effect.events_total,
                "total_n": effect.total_n,
                "or_value": effect.or_value,
                "log_or": effect.log_or,
                "se_log_or": effect.se_log_or,
                "effect_value": effect.effect_value,
                "effect_se": effect.effect_se,
                "weight": effect.weight,
                "ci_lower_95": effect.ci_lower_95,
                "ci_upper_95": effect.ci_upper_95,
                "adjusted_or": effect.adjusted_or,
                "adjusted_rr": effect.adjusted_rr,
                "adjusted_hr": effect.adjusted_hr,
                "n_intervention": effect.n_intervention,
                "n_control": effect.n_control,
                "mean_intervention": effect.mean_intervention,
                "sd_intervention": effect.sd_intervention,
                "mean_control": effect.mean_control,
                "sd_control": effect.sd_control,
                "median_intervention": effect.median_intervention,
                "iqr_intervention": effect.iqr_intervention,
                "median_control": effect.median_control,
                "iqr_control": effect.iqr_control,
                "followup_time": effect.followup_time,
                "followup_unit": effect.followup_unit,
                "person_time_intervention": effect.person_time_intervention,
                "person_time_control": effect.person_time_control,
                "tp": effect.tp,
                "fp": effect.fp,
                "fn": effect.fn,
                "tn": effect.tn,
                "sensitivity_value": effect.sensitivity_value,
                "specificity_value": effect.specificity_value,
                "subgroup_label": effect.subgroup_label,
                "subgroup_level": effect.subgroup_level,
                "subgroup_order": effect.subgroup_order,
                "sensitivity_flag": effect.sensitivity_flag,
                "sensitivity_reason": effect.sensitivity_reason,
                "analysis_population": effect.analysis_population,
                "model_type": effect.model_type,
                "covariates_json": effect.covariates_json or {},
                "adjustment_variables": effect.adjustment_variables,
                "is_adjusted": effect.is_adjusted,
                "source_page": effect.source_page,
                "source_locator": effect.source_locator or {},
                "confidence": effect.confidence,
                "risk_of_bias_overall": rob_summary["overall"],
            }
            row = MatrixRow(
                matrix_version_id=version.id,
                project_id=project_id,
                paper_id=paper.id,
                extracted_study_id=study.id,
                row_key=f"effect:{study.id}:{effect.id}",
                row_kind="effect",
                outcome_key=outcome_key,
                effect_measure=effect.effect_measure,
                sort_index=row_count,
                data_json=effect_data,
            )
            db.add(row)
            await db.flush()
            row_count += 1
            effect_count += 1

            db.add(
                MatrixProvenance(
                    matrix_row_id=row.id,
                    field_name="effect",
                    source_type="extracted_effect_size",
                    source_id=str(effect.id),
                    source_locator={
                        "source_page": effect.source_page,
                        "source_locator": effect.source_locator or {},
                    },
                    excerpt=(effect.raw_extracted_value or "")[:500],
                    confidence=float(effect.confidence or 0),
                )
            )
            provenance_count += 1

            for issue in _validate_effect(effect_data):
                validation_issues.append(
                    MatrixValidationIssue(
                        matrix_version_id=version.id,
                        matrix_row_id=row.id,
                        severity=issue["severity"],
                        code=issue["code"],
                        message=issue["message"],
                        field_name=issue.get("field_name"),
                    )
                )

    # If no meta rows are available yet, fallback to extraction records to keep the matrix operational.
    if row_count == 0:
        records_q = await db.execute(
            select(ExtractionRecord)
            .where(ExtractionRecord.project_id == project_id)
            .options(selectinload(ExtractionRecord.field_values))
            .order_by(ExtractionRecord.created_at.asc())
        )
        for record in records_q.scalars().all():
            values: dict[str, Any] = {}
            for field in record.field_values:
                values[field.field_name] = field.value_text
            row = MatrixRow(
                matrix_version_id=version.id,
                project_id=project_id,
                paper_id=record.paper_id,
                extracted_study_id=None,
                row_key=f"record:{record.id}",
                row_kind="extraction_record",
                outcome_key=None,
                effect_measure=None,
                sort_index=row_count,
                data_json={
                    "record_id": str(record.id),
                    "paper_id": str(record.paper_id) if record.paper_id else None,
                    "template_id": str(record.template_id),
                    "status": record.status,
                    "fields": values,
                },
            )
            db.add(row)
            await db.flush()
            row_count += 1
            db.add(
                MatrixProvenance(
                    matrix_row_id=row.id,
                    field_name="fields",
                    source_type="extraction_record",
                    source_id=str(record.id),
                    source_locator={"kind": "extraction_record"},
                    excerpt=json.dumps(values, ensure_ascii=False)[:500],
                    confidence=1.0,
                )
            )
            provenance_count += 1

    for issue in validation_issues:
        db.add(issue)

    validation_counter = Counter((item.severity or "warning").lower() for item in validation_issues)
    version.status = "ready"
    version.updated_at = datetime.now(timezone.utc)
    version.summary_json = {
        "rows_total": row_count,
        "studies": study_count,
        "effects": effect_count,
        "provenance_rows": provenance_count,
        "validation_issues": len(validation_issues),
    }
    version.validation_summary_json = dict(validation_counter)
    version.source_signature = f"studies:{study_count}|effects:{effect_count}|rows:{row_count}"

    await db.commit()
    await db.refresh(version)
    return version


async def list_matrix_versions(db: AsyncSession, *, project_id: UUID) -> list[MatrixVersion]:
    q = await db.execute(
        select(MatrixVersion)
        .where(MatrixVersion.project_id == project_id)
        .order_by(MatrixVersion.version_number.desc(), MatrixVersion.created_at.desc())
    )
    return q.scalars().all()


async def get_matrix_version(db: AsyncSession, *, version_id: UUID) -> MatrixVersion | None:
    q = await db.execute(
        select(MatrixVersion)
        .where(MatrixVersion.id == version_id)
        .options(
            selectinload(MatrixVersion.rows),
            selectinload(MatrixVersion.validation_issues),
        )
    )
    return q.scalars().first()


def serialize_matrix_version(version: MatrixVersion) -> dict[str, Any]:
    rows = sorted(version.rows, key=lambda item: (item.sort_index, item.created_at))
    return {
        "id": str(version.id),
        "project_id": str(version.project_id),
        "version_number": version.version_number,
        "status": version.status,
        "schema_version": version.schema_version,
        "is_current": version.is_current,
        "source_signature": version.source_signature,
        "summary": version.summary_json or {},
        "validation_summary": version.validation_summary_json or {},
        "created_at": version.created_at.isoformat() if version.created_at else None,
        "updated_at": version.updated_at.isoformat() if getattr(version, "updated_at", None) else None,
        "rows": _flatten_rows(rows),
        "validation_issues": [
            {
                "id": str(issue.id),
                "severity": issue.severity,
                "code": issue.code,
                "message": issue.message,
                "field_name": issue.field_name,
                "row_id": str(issue.matrix_row_id) if issue.matrix_row_id else None,
            }
            for issue in version.validation_issues
        ],
    }


def export_matrix_version(version: MatrixVersion, *, export_format: str) -> tuple[bytes, str, str]:
    fmt = export_format.lower().strip()
    if fmt not in SUPPORTED_MATRIX_EXPORTS:
        raise ValueError(f"Unsupported matrix export format: {export_format}")

    rows = sorted(version.rows, key=lambda item: (item.sort_index, item.created_at))
    flat_rows = _flatten_rows(rows)
    filename_base = f"matrix_v{version.version_number}_{version.id}"

    if fmt == "json":
        payload = serialize_matrix_version(version)
        data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        return data, "application/json", f"{filename_base}.json"

    if fmt == "xml":
        root = ET.Element("matrix")
        root.set("id", str(version.id))
        root.set("project_id", str(version.project_id))
        root.set("version_number", str(version.version_number))
        rows_node = ET.SubElement(root, "rows")
        for row in flat_rows:
            row_node = ET.SubElement(rows_node, "row")
            for key, value in row.items():
                cell = ET.SubElement(row_node, key)
                if value is None:
                    continue
                if isinstance(value, (dict, list)):
                    cell.text = json.dumps(value, ensure_ascii=False)
                else:
                    cell.text = str(value)
        issues_node = ET.SubElement(root, "validation_issues")
        for issue in version.validation_issues:
            issue_node = ET.SubElement(issues_node, "issue")
            issue_node.set("severity", str(issue.severity))
            issue_node.set("code", str(issue.code))
            issue_node.text = issue.message
        data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
        return data, "application/xml", f"{filename_base}.xml"

    frame = pd.DataFrame(flat_rows)
    if fmt == "csv":
        data = frame.to_csv(index=False).encode("utf-8")
        return data, "text/csv; charset=utf-8", f"{filename_base}.csv"

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        frame.to_excel(writer, index=False, sheet_name="matrix")
        issues = pd.DataFrame(
            [
                {
                    "severity": issue.severity,
                    "code": issue.code,
                    "message": issue.message,
                    "field_name": issue.field_name,
                    "row_id": str(issue.matrix_row_id) if issue.matrix_row_id else None,
                }
                for issue in version.validation_issues
            ]
        )
        issues.to_excel(writer, index=False, sheet_name="validation_issues")
    return (
        buffer.getvalue(),
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        f"{filename_base}.xlsx",
    )
