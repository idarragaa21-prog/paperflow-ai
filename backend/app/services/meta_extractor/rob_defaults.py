from __future__ import annotations

from dataclasses import dataclass

from app.services.meta_extractor.schema import RiskOfBiasSchema


@dataclass(frozen=True)
class ROBDefaults:
    tool: str
    domains: list[str]


ROB_DEFAULTS: dict[str, ROBDefaults] = {
    "rct": ROBDefaults(
        tool="ROB2",
        domains=[
            "Randomization process",
            "Deviations from intended interventions",
            "Missing outcome data",
            "Measurement of the outcome",
            "Selection of the reported result",
        ],
    ),
    "cohort": ROBDefaults(
        tool="NOS",
        domains=[
            "Selection: Representativeness of the exposed cohort",
            "Selection: Selection of the non-exposed cohort",
            "Selection: Ascertainment of exposure",
            "Selection: Outcome not present at start",
            "Comparability",
            "Outcome: Assessment of outcome",
            "Outcome: Length of follow-up",
            "Outcome: Adequacy of follow-up",
        ],
    ),
    "case-control": ROBDefaults(
        tool="NOS",
        domains=[
            "Selection: Case definition adequate",
            "Selection: Representativeness of cases",
            "Selection: Selection of controls",
            "Selection: Definition of controls",
            "Comparability",
            "Exposure: Ascertainment of exposure",
            "Exposure: Same method for cases and controls",
            "Exposure: Non-response rate",
        ],
    ),
    "diagnostic": ROBDefaults(
        tool="QUADAS2",
        domains=[
            "Patient selection",
            "Index test",
            "Reference standard",
            "Flow and timing",
        ],
    ),
    "quasi-experimental": ROBDefaults(
        tool="ROBINS-I",
        domains=[
            "Confounding",
            "Selection of participants",
            "Classification of interventions",
            "Deviations from intended interventions",
            "Missing data",
            "Measurement of outcomes",
            "Selection of the reported result",
        ],
    ),
}


def _normalize_design(design: str | None) -> str:
    s = (design or "").strip().lower()
    # normalize common variants
    if any(k in s for k in ["rct", "random", "trial", "controlled"]):
        return "rct"
    if "cohort" in s:
        return "cohort"
    if "case" in s and "control" in s:
        return "case-control"
    if any(k in s for k in ["diagn", "accuracy", "quadas"]):
        return "diagnostic"
    if any(k in s for k in ["quasi", "nonrandom", "non-random", "robins"]):
        return "quasi-experimental"
    return "rct"


def generate_default_rob(study_design: str | None) -> tuple[str, list[RiskOfBiasSchema]]:
    """Generate default risk-of-bias domains when extraction returned none.

    Returns: (tool, list[RiskOfBiasSchema])
    """

    key = _normalize_design(study_design)
    cfg = ROB_DEFAULTS.get(key) or ROB_DEFAULTS["rct"]

    rows = [
        RiskOfBiasSchema(
            tool=cfg.tool,
            domain_name=d,
            judgement="unclear",
            support_for_judgement="Pending manual assessment",
        )
        for d in cfg.domains
    ]

    return cfg.tool, rows
