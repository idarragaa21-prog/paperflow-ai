from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from statistics import mean
from typing import Any
from uuid import UUID

import httpx
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.core.logger import logger
from app.core.storage import storage_manager
from app.models.analytics import AnalysisArtifact, AnalysisRun, Dataset, DatasetColumn, FigureArtifact


def _normalize_text_value(value: Any) -> str:
    """Flatten a list of text fragments into a single string, or pass through str."""
    if isinstance(value, list):
        return "\n\n".join(str(v) for v in value)
    return str(value) if value is not None else ""


def _normalize_figure_payload(payload: dict | None) -> dict:
    """Normalize a figure payload dict: flatten single-element lists and handle missing payload."""
    if payload is None:
        return {
            "title": "Summary figure unavailable (degraded fallback)",
            "caption": "",
            "degraded": True,
        }
    out: dict = {}
    for k, v in payload.items():
        out[k] = v[0] if isinstance(v, list) and len(v) == 1 else v
    out.setdefault("degraded", False)
    return out


def _infer_dtype(series: pd.Series) -> str:
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_integer_dtype(series):
        return "integer"
    if pd.api.types.is_numeric_dtype(series):
        return "number"
    return "string"


async def create_dataset(
    db: AsyncSession,
    *,
    project_id: UUID,
    title: str,
    description: str | None,
    rows: list[dict],
) -> Dataset:
    if not rows:
        raise ValueError("rows cannot be empty")

    df = pd.DataFrame(rows)
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    saved = await storage_manager.save_dataset_bytes(data=csv_bytes, filename=f"{title}.csv", project_id=project_id)

    dataset = Dataset(
        project_id=project_id,
        title=title,
        description=description,
        source_type="manual",
        file_path=saved["file_path"],
        row_count=len(df.index),
        column_count=len(df.columns),
        schema_json={"columns": list(df.columns)},
    )
    db.add(dataset)
    await db.flush()

    for position, column_name in enumerate(df.columns):
        series = df[column_name]
        summary = {
            "nulls": int(series.isna().sum()),
            "unique": int(series.nunique(dropna=True)),
        }
        if pd.api.types.is_numeric_dtype(series):
            numeric = pd.to_numeric(series, errors="coerce").dropna()
            if not numeric.empty:
                summary["mean"] = float(numeric.mean())
        db.add(
            DatasetColumn(
                dataset_id=dataset.id,
                name=str(column_name),
                data_type=_infer_dtype(series),
                position=position,
                is_nullable=bool(series.isna().any()),
                summary_json=summary,
            )
        )

    await db.commit()
    stmt = select(Dataset).where(Dataset.id == dataset.id).options(selectinload(Dataset.columns))
    hydrated = await db.execute(stmt)
    return hydrated.scalars().first()


def _load_dataset_frame(dataset: Dataset) -> pd.DataFrame:
    if not dataset.file_path:
        return pd.DataFrame()
    with storage_manager.local_path(dataset.file_path, suffix=".csv") as local_path:
        return pd.read_csv(local_path)


def _local_analysis(df: pd.DataFrame, analysis_type: str, input_params: dict) -> dict:
    analysis_type = analysis_type.lower()
    summary: dict = {"analysis_type": analysis_type, "row_count": int(len(df.index)), "column_count": int(len(df.columns))}
    warnings: list[str] = []

    if analysis_type == "descriptives":
        summary["columns"] = {
            column: {
                "type": _infer_dtype(df[column]),
                "non_null": int(df[column].notna().sum()),
                "unique": int(df[column].nunique(dropna=True)),
            }
            for column in df.columns
        }
    elif analysis_type == "group_comparison":
        group_col = input_params.get("group_column")
        value_col = input_params.get("value_column")
        if group_col in df.columns and value_col in df.columns:
            grouped = df.groupby(group_col)[value_col].agg(["count", "mean"]).reset_index()
            summary["groups"] = grouped.to_dict(orient="records")
        else:
            warnings.append("Missing group_column or value_column for group comparison")
    elif analysis_type in {"linear_regression", "logistic_regression"}:
        target = input_params.get("target_column")
        features = input_params.get("feature_columns") or []
        summary["target_column"] = target
        summary["feature_columns"] = features
        summary["note"] = "Regression fallback executed locally without coefficient fitting. Use r-engine for full model output."
        warnings.append("Local fallback does not fit coefficients; r-engine recommended.")
    else:
        summary["note"] = "Analysis type accepted but currently summarized via generic local fallback."
        warnings.append("Advanced analysis delegated to r-engine when available.")

    return {"summary": summary, "warnings": warnings, "script": f"# local fallback analysis\n# type: {analysis_type}\n# params: {json.dumps(input_params)}"}


async def create_analysis_run(
    db: AsyncSession,
    *,
    project_id: UUID,
    dataset: Dataset | None,
    title: str,
    analysis_type: str,
    input_params: dict,
) -> AnalysisRun:
    rows: list[dict] = []
    if dataset is not None:
        df = _load_dataset_frame(dataset)
        rows = df.to_dict(orient="records")
    else:
        df = pd.DataFrame()

    payload = {
        "analysis_type": analysis_type,
        "input_params": input_params,
        "rows": rows,
    }
    response_data: dict | None = None
    warnings: list[str] = []
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(f"{settings.R_ENGINE_URL}/run-analysis", json=payload)
            resp.raise_for_status()
            response_data = resp.json()
    except Exception as _r_err:
        logger.warning(f"[analysis_service] r-engine call failed: {_r_err!r} — falling back to local analysis")
        response_data = _local_analysis(df, analysis_type, input_params)
        warnings.append("r-engine unavailable, local fallback used")

    warnings.extend(response_data.get("warnings") or [])
    artifact_manifest: list[dict] = []
    run = AnalysisRun(
        project_id=project_id,
        dataset_id=dataset.id if dataset else None,
        title=title,
        analysis_type=analysis_type,
        status="completed",
        input_params=input_params,
        runtime_metadata={
            "engine": "r-engine" if "engine_version" in response_data else "local_fallback",
            "dataset_snapshot": {
                "dataset_id": str(dataset.id) if dataset else None,
                "row_count": len(rows),
                "column_count": len(rows[0].keys()) if rows else 0,
            },
            "artifact_manifest": artifact_manifest,
        },
        script_text=response_data.get("script"),
        warnings=warnings,
        result_summary=response_data.get("summary"),
        engine_version=response_data.get("engine_version") or "local-fallback",
    )
    db.add(run)
    await db.flush()

    report_body = json.dumps(response_data.get("summary") or {}, indent=2, ensure_ascii=False)
    report_saved = await storage_manager.save_text_artifact(
        text=report_body,
        filename=f"{run.id}_summary.json",
        project_id=project_id,
    )
    db.add(
        AnalysisArtifact(
            analysis_run_id=run.id,
            artifact_type="summary",
            filename=report_saved["filename"],
            file_path=report_saved["file_path"],
            mime_type="application/json",
            metadata_json={"analysis_type": analysis_type},
        )
    )
    artifact_manifest.append({"artifact_type": "summary", "filename": report_saved["filename"], "file_path": report_saved["file_path"]})

    chart_data = response_data.get("figure") or {"title": "Summary figure placeholder", "caption": "Generated from analysis summary"}
    chart_saved = await storage_manager.save_text_artifact(
        text=json.dumps(chart_data, indent=2, ensure_ascii=False),
        filename=f"{run.id}_figure.json",
        project_id=project_id,
    )
    db.add(
        FigureArtifact(
            analysis_run_id=run.id,
            title=chart_data.get("title", "Summary figure"),
            caption=chart_data.get("caption"),
            filename=chart_saved["filename"],
            file_path=chart_saved["file_path"],
            metadata_json=chart_data,
        )
    )
    artifact_manifest.append({"artifact_type": "figure", "filename": chart_saved["filename"], "file_path": chart_saved["file_path"]})

    await db.commit()
    stmt = (
        select(AnalysisRun)
        .where(AnalysisRun.id == run.id)
        .options(selectinload(AnalysisRun.artifacts))
    )
    hydrated = await db.execute(stmt)
    return hydrated.scalars().first()


async def export_analysis_run(db: AsyncSession, *, run: AnalysisRun, fmt: str) -> tuple[bytes, str, str]:
    if run.status != "completed":
        raise ValueError(f"AnalysisRun {run.id} is not completed (status={run.status!r})")

    artifact_type = f"report_{fmt}"
    artifact = next(
        (a for a in (run.artifacts or []) if getattr(a, "artifact_type", None) == artifact_type),
        None,
    )
    if artifact is None:
        raise ValueError(f"No persisted {fmt} artifact found for run {run.id}")

    try:
        data = storage_manager.read_bytes(artifact.file_path)
    except FileNotFoundError as exc:
        raise ValueError(f"Artifact {artifact.filename!r} is missing from storage: {exc}") from exc

    return data, artifact.mime_type, artifact.filename
