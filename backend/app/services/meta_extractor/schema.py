from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ArmSchema(BaseModel):
    model_config = {"protected_namespaces": ()}
    arm_name: str
    intervention_description: Optional[str] = None
    dose_intensity: Optional[str] = None
    cointerventions: Optional[str] = None
    n_randomized: Optional[int] = None
    n_analyzed: Optional[int] = None
    losses_to_followup_n: Optional[int] = None
    losses_to_followup_reasons: Optional[str] = None

    # Demographics (per arm)
    mean_age: Optional[float] = None
    sd_age: Optional[float] = None
    median_age: Optional[float] = None
    iqr_age: Optional[str] = None
    age_range: Optional[str] = None
    percent_female: Optional[float] = None
    percent_male: Optional[float] = None
    n_female: Optional[int] = None
    n_male: Optional[int] = None

    # Baseline clinical (per arm)
    mean_bmi: Optional[float] = None
    sd_bmi: Optional[float] = None
    comorbidities: Optional[str] = None
    disease_severity: Optional[str] = None
    disease_duration: Optional[str] = None
    baseline_outcome_value: Optional[str] = None
    previous_treatments: Optional[str] = None
    smoking_status: Optional[str] = None
    ethnicity_distribution: Optional[str] = None

    # Follow-up (per arm)
    followup_duration_months: Optional[float] = None
    completion_rate: Optional[float] = None
    withdrawal_reasons: Optional[str] = None


class OutcomeSchema(BaseModel):
    model_config = {"protected_namespaces": ()}
    outcome_name: str
    outcome_type: str = "binary"  # binary|continuous|time-to-event
    definition: Optional[str] = None
    timepoint: Optional[str] = None
    measurement_instrument: Optional[str] = None

    outcome_category: Optional[str] = None  # primary|secondary|exploratory|safety|not_specified
    direction_of_benefit: Optional[str] = None  # higher_is_better|lower_is_better|not_applicable
    how_measured: Optional[str] = None
    measurement_timepoints: Optional[str] = None
    missing_data_handling: Optional[str] = None


class EffectSizeSchema(BaseModel):
    model_config = {"protected_namespaces": ()}
    outcome_name: str
    timepoint: Optional[str] = None
    arm_intervention: str
    arm_control: str
    effect_measure: str = "OR"  # OR|RR|HR|MD|SMD

    # 2x2 (only if explicitly available)
    a_events: Optional[int] = None
    b_non_events: Optional[int] = None
    c_events: Optional[int] = None
    d_non_events: Optional[int] = None

    # Additional per-outcome numbers
    p_value: Optional[float] = None
    n_intervention_for_outcome: Optional[int] = None
    n_control_for_outcome: Optional[int] = None
    events_intervention: Optional[int] = None
    events_control: Optional[int] = None

    mean_intervention: Optional[float] = None
    sd_intervention: Optional[float] = None
    mean_control: Optional[float] = None
    sd_control: Optional[float] = None

    median_intervention: Optional[float] = None
    iqr_intervention: Optional[str] = None
    median_control: Optional[float] = None
    iqr_control: Optional[str] = None

    mean_difference: Optional[float] = None
    sd_difference: Optional[float] = None

    nnt: Optional[float] = None
    absolute_risk_reduction: Optional[float] = None
    relative_risk_reduction: Optional[float] = None

    heterogeneity_subgroup: Optional[str] = None
    sensitivity_analysis: Optional[str] = None
    analysis_method: Optional[str] = None
    model_type: Optional[str] = None  # fixed|random|mixed|not_applicable
    intention_to_treat: Optional[str] = None  # ITT|per_protocol|modified_ITT|as_treated|not_specified

    continuity_correction_used: Optional[str] = None

    # Values calculated or reported (generic container)
    or_value: Optional[float] = None
    log_or: Optional[float] = None
    se_log_or: Optional[float] = None
    ci_lower_95: Optional[float] = None
    ci_upper_95: Optional[float] = None

    # Adjusted effects (when no raw 2x2)
    adjusted_or: Optional[float] = None
    adjusted_rr: Optional[float] = None
    adjusted_hr: Optional[float] = None
    adjustment_variables: Optional[str] = None
    is_adjusted: bool = False

    # Provenance
    raw_extracted_value: Optional[str] = None
    page_number: Optional[int] = None
    table_id: Optional[str] = None
    figure_id: Optional[str] = None
    source_type: str = "text"  # text|table|ocr|figure
    extraction_confidence: float = 0.0
    comments: Optional[str] = None

    @field_validator("a_events", "b_non_events", "c_events", "d_non_events")
    @classmethod
    def non_negative_counts(cls, v):
        if v is None:
            return v
        if int(v) < 0:
            raise ValueError("counts cannot be negative")
        return int(v)


class RiskOfBiasSchema(BaseModel):
    model_config = {"protected_namespaces": ()}
    tool: str = "ROB2"  # ROB2|NOS|QUADAS2|ROBINS-I|other
    domain_name: str
    judgement: str = "unclear"  # low|some_concerns|high|unclear
    support_for_judgement: Optional[str] = None


class ExtractedStudySchema(BaseModel):
    model_config = {"protected_namespaces": ()}
    # required
    title: str
    first_author: str
    year: int
    journal: str

    # Quant summary (optional)
    total_sample_size: Optional[int] = None

    # Quant per main arms (optional)
    total_n_intervention: Optional[int] = None
    total_n_control: Optional[int] = None
    mean_age_total: Optional[float] = None
    percent_female_total: Optional[float] = None

    setting: Optional[str] = None
    geographic_region: Optional[str] = None
    income_level: Optional[str] = None
    language_of_publication: Optional[str] = None
    peer_reviewed: Optional[str] = None

    # optional identifiers
    citation_key: Optional[str] = None
    doi: Optional[str] = None
    pmid: Optional[str] = None
    pmcid: Optional[str] = None

    country: Optional[str] = None
    centers: Optional[str] = None
    study_design: str = "not_reported"

    recruitment_dates: Optional[str] = None
    follow_up_duration: Optional[str] = None
    population_description: Optional[str] = None
    inclusion_criteria: Optional[str] = None
    exclusion_criteria: Optional[str] = None
    baseline_balance_notes: Optional[str] = None
    funding: Optional[str] = None
    conflicts_of_interest: Optional[str] = None
    registration: Optional[str] = None
    notes: Optional[str] = None

    extraction_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    arms: list[ArmSchema] = Field(min_length=2)
    outcomes: list[OutcomeSchema] = Field(min_length=1)
    effect_sizes: list[EffectSizeSchema] = []
    risk_of_bias: list[RiskOfBiasSchema] = []
