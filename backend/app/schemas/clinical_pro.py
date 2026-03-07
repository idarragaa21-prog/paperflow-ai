from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ClinicalProSection(BaseModel):
    id: str
    title: str
    content_markdown: str


class ClinicalProTable(BaseModel):
    title: str
    columns: list[str]
    rows: list[list[Any]]  # keep flexible; frontend will stringify


class ClinicalProChart(BaseModel):
    title: str
    type: Literal["bar", "line", "forest_like", "conceptual"]
    data: dict[str, Any]
    note: str | None = None


class ClinicalProMermaid(BaseModel):
    title: str
    code: str


class ClinicalEvidenceMapRow(BaseModel):
    question: str
    conclusion: str
    strength: Literal["high", "medium", "low"]
    key_papers: list[str] = Field(default_factory=list)  # e.g. ["PMID:123", "DOI:..."]
    limitations: str | None = None


class ClinicalProQuality(BaseModel):
    evidence_strength: Literal["high", "medium", "low"]
    gaps: list[str] = Field(default_factory=list)


class ClinicalProOutput(BaseModel):
    title: str
    sections: list[ClinicalProSection]

    tables: list[ClinicalProTable] = Field(default_factory=list)
    charts: list[ClinicalProChart] = Field(default_factory=list)
    mermaid: list[ClinicalProMermaid] = Field(default_factory=list)

    evidence_map: list[ClinicalEvidenceMapRow] = Field(default_factory=list)
    references_vancouver: list[str] = Field(default_factory=list)

    quality: ClinicalProQuality

    model_config = {"extra": "ignore"}
