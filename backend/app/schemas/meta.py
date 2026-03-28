from __future__ import annotations

from datetime import datetime
from typing import Literal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class EffectSizePatch(BaseModel):
    # Text fields
    outcome_name: str | None = None
    timepoint: str | None = None
    arm_intervention: str | None = None
    arm_control: str | None = None
    effect_measure: str | None = None

    # 2x2
    a_events: int | None = None
    b_non_events: int | None = None
    c_events: int | None = None
    d_non_events: int | None = None

    # Derived (optional)
    or_value: float | None = None
    log_or: float | None = None
    se_log_or: float | None = None
    ci_lower_95: float | None = None
    ci_upper_95: float | None = None

    # Adjusted
    adjusted_or: float | None = None
    adjusted_rr: float | None = None
    adjusted_hr: float | None = None
    adjustment_variables: str | None = None
    is_adjusted: bool | None = None

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
