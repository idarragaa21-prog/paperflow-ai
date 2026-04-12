from __future__ import annotations

from datetime import datetime
from typing import Literal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class EffectSizePatch(BaseModel):
    model_config = {"protected_namespaces": ()}

    # Text fields
    outcome_name: str | None = None
    timepoint: str | None = None
    arm_intervention: str | None = None
    arm_control: str | None = None
    effect_measure: str | None = None
    outcome_type: str | None = None
    outcome_unit: str | None = None
    comparator_type: str | None = None
    effect_direction: str | None = None

    # 2x2
    a_events: int | None = None
    b_non_events: int | None = None
    c_events: int | None = None
    d_non_events: int | None = None
    events_total: int | None = None
    total_n: int | None = None
    tp: int | None = None
    fp: int | None = None
    fn: int | None = None
    tn: int | None = None

    # Derived (optional)
    or_value: float | None = None
    log_or: float | None = None
    se_log_or: float | None = None
    effect_value: float | None = None
    effect_se: float | None = None
    weight: float | None = None
    ci_lower_95: float | None = None
    ci_upper_95: float | None = None

    # Adjusted
    adjusted_or: float | None = None
    adjusted_rr: float | None = None
    adjusted_hr: float | None = None
    adjustment_variables: str | None = None
    is_adjusted: bool | None = None
    covariates_json: dict[str, Any] | None = None

    # Continuous
    n_intervention: int | None = None
    n_control: int | None = None
    mean_intervention: float | None = None
    sd_intervention: float | None = None
    mean_control: float | None = None
    sd_control: float | None = None
    median_intervention: float | None = None
    iqr_intervention: str | None = None
    median_control: float | None = None
    iqr_control: str | None = None

    # Survival / incidence
    followup_time: float | None = None
    followup_unit: str | None = None
    person_time_intervention: float | None = None
    person_time_control: float | None = None

    # Diagnostic
    sensitivity_value: float | None = None
    specificity_value: float | None = None

    # Subgroup / sensitivity context
    subgroup_label: str | None = None
    subgroup_level: str | None = None
    subgroup_order: int | None = None
    sensitivity_flag: bool | None = None
    sensitivity_reason: str | None = None
    analysis_population: str | None = None
    model_type: str | None = None

    # Provenance / misc
    raw_extracted_value: str | None = None
    source_type: str | None = None
    source_page: int | None = None
    source_locator: dict[str, Any] | None = None
    confidence: float | None = None
    comments: str | None = None


class BatchEffectPatchItem(BaseModel):
    id: UUID
    patch: EffectSizePatch


class BatchEffectPatchRequest(BaseModel):
    updates: list[BatchEffectPatchItem] = Field(default_factory=list, min_length=1)


class MetaExportListRow(BaseModel):
    id: UUID
    project_id: UUID
    batch_id: UUID | None
    filename: str
    format: str
    created_at: datetime


class MetaExportRequest(BaseModel):
    project_id: UUID
    batch_id: UUID | None = None
    format: Literal["xlsx", "csv"] = "xlsx"
