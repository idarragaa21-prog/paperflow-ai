from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO, StringIO
from typing import Any
from uuid import UUID
from zipfile import ZIP_DEFLATED, ZipFile

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

from app.core.logger import logger


SHEETS = [
    "STUDIES",
    "ARMS",
    "OUTCOMES",
    "EFFECT_SIZES",
    "RISK_OF_BIAS",
    "TABLES_RAW",
    "IMAGES_OCR_RAW",
    "LOGS",
]


STUDIES_COLS = [
    "study_id",
    "paper_id",
    "batch_id",
    "paper_title",
    "paper_filename",
    "paper_authors",
    "paper_doi",
    "paper_pmid",
    "paper_pmcid",
    "paper_journal",
    "paper_publication_year",
    "paper_source_provider",
    "paper_oa_url",
    "citation_key",
    "title",
    "first_author",
    "year",
    "journal",
    "doi",
    "pmid",
    "pmcid",
    "country",
    "centers",
    "study_design",
    "recruitment_dates",
    "follow_up_duration",
    "population_description",
    "inclusion_criteria",
    "exclusion_criteria",
    "baseline_balance_notes",
    "funding",
    "conflicts_of_interest",
    "registration",
    "notes",
    "total_sample_size",
    "total_n_intervention",
    "total_n_control",
    "mean_age_total",
    "percent_female_total",
    "setting",
    "geographic_region",
    "income_level",
    "language_of_publication",
    "peer_reviewed",
    "extraction_confidence",
    "provenance",
    "study_created_at",
    "study_updated_at",
    "raw_study_json",
]

ARMS_COLS = [
    "arm_id",
    "study_id",
    "arm_name",
    "intervention_description",
    "dose_intensity",
    "cointerventions",
    "n_randomized",
    "n_analyzed",
    "losses_to_followup_n",
    "losses_to_followup_reasons",
    "mean_age",
    "sd_age",
    "median_age",
    "iqr_age",
    "age_range",
    "percent_female",
    "percent_male",
    "n_female",
    "n_male",
    "mean_bmi",
    "sd_bmi",
    "comorbidities",
    "disease_severity",
    "disease_duration",
    "baseline_outcome_value",
    "previous_treatments",
    "smoking_status",
    "ethnicity_distribution",
    "followup_duration_months",
    "completion_rate",
    "withdrawal_reasons",
]

OUTCOMES_COLS = [
    "outcome_id",
    "study_id",
    "outcome_name",
    "outcome_type",
    "definition",
    "timepoint",
    "measurement_instrument",
    "outcome_category",
    "direction_of_benefit",
    "how_measured",
    "measurement_timepoints",
    "missing_data_handling",
]

EFFECTS_COLS = [
    "effect_id",
    "study_id",
    "outcome_name",
    "timepoint",
    "arm_intervention",
    "arm_control",
    "effect_measure",
    "a_events",
    "b_non_events",
    "c_events",
    "d_non_events",
    "continuity_correction_used",
    "or_value",
    "log_or",
    "se_log_or",
    "ci_lower_95",
    "ci_upper_95",
    "adjusted_or",
    "adjusted_rr",
    "adjusted_hr",
    "adjustment_variables",
    "is_adjusted",
    "raw_extracted_value",
    "page_number",
    "table_id",
    "figure_id",
    "source_locator_json",
    "source_type",
    "extraction_confidence",
    "comments",
    "manually_edited",
    "edited_at",
    "p_value",
    "n_intervention_for_outcome",
    "n_control_for_outcome",
    "events_intervention",
    "events_control",
    "mean_intervention",
    "sd_intervention",
    "mean_control",
    "sd_control",
    "median_intervention",
    "iqr_intervention",
    "median_control",
    "iqr_control",
    "mean_difference",
    "sd_difference",
    "nnt",
    "absolute_risk_reduction",
    "relative_risk_reduction",
    "heterogeneity_subgroup",
    "sensitivity_analysis",
    "analysis_method",
    "model_type",
    "intention_to_treat",
    "raw_effect_json",
]

ROB_COLS = [
    "rob_id",
    "study_id",
    "tool",
    "domain_name",
    "judgement",
    "support_for_judgement",
    "auto_generated",
    "manually_edited",
    "edited_at",
    "raw_rob_json",
]

TABLES_RAW_COLS = ["table_id", "study_id", "page", "extracted_markdown"]
IMAGES_OCR_RAW_COLS = ["image_id", "study_id", "page", "ocr_text"]
LOGS_COLS = ["timestamp", "job_id", "study_id", "level", "message"]

HEADER_FONT = Font(bold=True)
HEADER_FILL = PatternFill(fill_type="solid", fgColor="EEF3FF")


@dataclass
class ExcelExportInput:
    studies: list[dict[str, Any]]
    arms: list[dict[str, Any]]
    outcomes: list[dict[str, Any]]
    effects: list[dict[str, Any]]
    rob: list[dict[str, Any]]
    tables_raw: list[dict[str, Any]]
    images_ocr_raw: list[dict[str, Any]]
    logs: list[dict[str, Any]]


def iter_meta_export_tables(data: ExcelExportInput):
    yield ("studies", "STUDIES", STUDIES_COLS, data.studies)
    yield ("arms", "ARMS", ARMS_COLS, data.arms)
    yield ("outcomes", "OUTCOMES", OUTCOMES_COLS, data.outcomes)
    yield ("effect_sizes", "EFFECT_SIZES", EFFECTS_COLS, data.effects)
    yield ("risk_of_bias", "RISK_OF_BIAS", ROB_COLS, data.rob)
    yield ("tables_raw", "TABLES_RAW", TABLES_RAW_COLS, data.tables_raw)
    yield ("images_ocr_raw", "IMAGES_OCR_RAW", IMAGES_OCR_RAW_COLS, data.images_ocr_raw)
    yield ("logs", "LOGS", LOGS_COLS, data.logs)


def _add_sheet(wb: Workbook, name: str, cols: list[str]) -> None:
    ws = wb.create_sheet(title=name)
    ws.append(cols)
    ws.freeze_panes = "A2"
    for cell in ws[1]:
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL


def _xlsx_value(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    return value


def _append_rows(ws, cols: list[str], rows: list[dict[str, Any]]) -> None:
    for r in rows:
        ws.append([_xlsx_value(r.get(c)) for c in cols])


def _finalize_sheet(ws, cols: list[str]) -> None:
    ws.auto_filter.ref = f"A1:{get_column_letter(len(cols))}{max(ws.max_row, 1)}"
    for idx, col_name in enumerate(cols, start=1):
        max_len = len(str(col_name))
        for row in ws.iter_rows(min_row=2, min_col=idx, max_col=idx, values_only=True):
            value = row[0]
            if value is None:
                continue
            max_len = max(max_len, len(str(value)))
        ws.column_dimensions[get_column_letter(idx)].width = min(max(max_len + 2, 12), 42)


def build_meta_xlsx(data: ExcelExportInput) -> bytes:
    wb = Workbook()
    # remove default
    default = wb.active
    wb.remove(default)

    # Create sheets
    _add_sheet(wb, "STUDIES", STUDIES_COLS)
    _add_sheet(wb, "ARMS", ARMS_COLS)
    _add_sheet(wb, "OUTCOMES", OUTCOMES_COLS)
    _add_sheet(wb, "EFFECT_SIZES", EFFECTS_COLS)
    _add_sheet(wb, "RISK_OF_BIAS", ROB_COLS)
    _add_sheet(wb, "TABLES_RAW", TABLES_RAW_COLS)
    _add_sheet(wb, "IMAGES_OCR_RAW", IMAGES_OCR_RAW_COLS)
    _add_sheet(wb, "LOGS", LOGS_COLS)

    # Fill
    _append_rows(wb["STUDIES"], STUDIES_COLS, data.studies)
    _append_rows(wb["ARMS"], ARMS_COLS, data.arms)
    _append_rows(wb["OUTCOMES"], OUTCOMES_COLS, data.outcomes)
    _append_rows(wb["EFFECT_SIZES"], EFFECTS_COLS, data.effects)
    _append_rows(wb["RISK_OF_BIAS"], ROB_COLS, data.rob)
    _append_rows(wb["TABLES_RAW"], TABLES_RAW_COLS, data.tables_raw)
    _append_rows(wb["IMAGES_OCR_RAW"], IMAGES_OCR_RAW_COLS, data.images_ocr_raw)
    _append_rows(wb["LOGS"], LOGS_COLS, data.logs)
    for _csv_name, sheet_name, cols, _rows in iter_meta_export_tables(data):
        _finalize_sheet(wb[sheet_name], cols)

    bio = BytesIO()
    wb.save(bio)
    return bio.getvalue()


def _csv_value(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    return value


def build_meta_csv_bundle(data: ExcelExportInput) -> bytes:
    bio = BytesIO()

    with ZipFile(bio, mode="w", compression=ZIP_DEFLATED) as zf:
        manifest = {
            "format": "csv_bundle",
            "tables": {
                csv_name: {
                    "sheet": sheet_name,
                    "columns": cols,
                    "rows": len(rows),
                }
                for csv_name, sheet_name, cols, rows in iter_meta_export_tables(data)
            },
        }
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))

        for csv_name, _sheet_name, cols, rows in iter_meta_export_tables(data):
            sio = StringIO(newline="")
            writer = csv.DictWriter(sio, fieldnames=cols, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow({col: _csv_value(row.get(col)) for col in cols})
            zf.writestr(f"{csv_name}.csv", sio.getvalue().encode("utf-8"))

    return bio.getvalue()
