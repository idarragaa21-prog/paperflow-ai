from __future__ import annotations

import base64
import json
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.core.storage import storage_manager
from app.models.analytics import AnalysisArtifact, AnalysisRun, Dataset, DatasetColumn, FigureArtifact

REPORT_MIME_TYPES = {
    "html": "text/html",
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
CORE_ANALYSIS_TYPES = {"descriptives", "group_comparison", "linear_regression", "logistic_regression"}
ADVANCED_ANALYSIS_TYPES = {"survival", "meta_analysis", "meta_regression", "sensitivity", "heterogeneity", "funnel_plot"}
SUPPORTED_ANALYSIS_TYPES = CORE_ANALYSIS_TYPES | ADVANCED_ANALYSIS_TYPES


def _normalize_r_engine_value(value):
    if isinstance(value, dict):
        return {str(key): _normalize_r_engine_value(item) for key, item in value.items()}
    if isinstance(value, list):
        normalized = [_normalize_r_engine_value(item) for item in value]
        if len(normalized) == 1 and not isinstance(normalized[0], (dict, list)):
            return normalized[0]
        return normalized
    return value


def _stringify_scalar(value, default: str = "") -> str:
    normalized = _normalize_r_engine_value(value)
    if normalized in (None, ""):
        return default
    if isinstance(normalized, (dict, list)):
        return json.dumps(normalized, ensure_ascii=False)
    return str(normalized)


def _infer_dtype(series) -> str:
    import pandas as pd

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
    import pandas as pd

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


def _load_dataset_frame(dataset: Dataset):
    import pandas as pd

    if not dataset.file_path:
        return pd.DataFrame()
    with storage_manager.local_path(dataset.file_path, suffix=".csv") as local_path:
        return pd.read_csv(local_path)


async def create_analysis_run_record(
    db: AsyncSession,
    *,
    project_id: UUID,
    dataset: Dataset | None,
    title: str,
    analysis_type: str,
    input_params: dict,
) -> AnalysisRun:
    normalized_type = analysis_type.lower().strip()
    if normalized_type not in SUPPORTED_ANALYSIS_TYPES:
        raise ValueError(f"Unsupported analysis_type={analysis_type}")

    run = AnalysisRun(
        project_id=project_id,
        dataset_id=dataset.id if dataset else None,
        title=title,
        analysis_type=normalized_type,
        status="queued",
        input_params=input_params,
        runtime_metadata={
            "engine": "r-engine",
            "template_version": "analysis_report_v2",
            "dataset_snapshot": {
                "dataset_id": str(dataset.id) if dataset else None,
                "row_count": int(dataset.row_count or 0) if dataset else 0,
                "column_count": int(dataset.column_count or 0) if dataset else 0,
            },
            "artifact_manifest": [],
        },
        warnings=[],
    )
    db.add(run)
    await db.commit()
    stmt = select(AnalysisRun).where(AnalysisRun.id == run.id).options(selectinload(AnalysisRun.artifacts))
    hydrated = await db.execute(stmt)
    return hydrated.scalars().first()


def _decode_artifact(artifact: dict) -> tuple[bytes, str, str, dict]:
    content = base64.b64decode(_stringify_scalar(artifact["content_base64"]).encode("utf-8"))
    filename = _stringify_scalar(artifact["filename"])
    mime_type = _stringify_scalar(artifact["mime_type"])
    metadata = _normalize_r_engine_value(artifact.get("metadata_json") or {})
    return content, filename, mime_type, metadata


async def run_analysis_pipeline(db: AsyncSession, *, run_id: UUID) -> AnalysisRun:
    stmt = select(AnalysisRun).where(AnalysisRun.id == run_id).options(selectinload(AnalysisRun.artifacts))
    result = await db.execute(stmt)
    run = result.scalars().first()
    if run is None:
        raise ValueError("Analysis run not found")

    dataset = await db.get(Dataset, run.dataset_id) if run.dataset_id else None
    if run.dataset_id and dataset is None:
        run.status = "failed"
        run.warnings = ["Dataset not found"]
        await db.commit()
        raise ValueError("Dataset not found")

    run.status = "running"
    await db.commit()

    rows: list[dict] = []
    if dataset is not None:
        df = _load_dataset_frame(dataset)
        rows = df.to_dict(orient="records")

    payload = {
        "title": run.title,
        "analysis_type": run.analysis_type,
        "input_params": run.input_params or {},
        "rows": rows,
        "output_formats": ["html", "pdf", "docx"],
    }

    try:
        async with httpx.AsyncClient(timeout=180) as client:
            response = await client.post(f"{settings.R_ENGINE_URL.rstrip('/')}/run-analysis", json=payload)
            response.raise_for_status()
            response_data = response.json()
    except Exception as exc:
        run.status = "failed"
        run.warnings = [f"r-engine unavailable: {exc}"]
        run.result_summary = {"error": str(exc)}
        await db.commit()
        raise

    summary = _normalize_r_engine_value(response_data.get("summary") or {})
    raw_warnings = _normalize_r_engine_value(response_data.get("warnings") or [])
    if isinstance(raw_warnings, list):
        warnings = [str(item) for item in raw_warnings]
    elif raw_warnings in (None, ""):
        warnings = []
    else:
        warnings = [str(raw_warnings)]
    engine_version = _stringify_scalar(response_data.get("engine_version"), default="unknown")
    template_version = _stringify_scalar(response_data.get("template_version"), default="analysis_report_v2")
    figure = _normalize_r_engine_value(response_data.get("figure") or {})
    artifact_manifest: list[dict] = []

    for artifact in list(run.artifacts):
        await db.delete(artifact)

    summary_saved = await storage_manager.save_text_artifact(
        text=json.dumps(summary, indent=2, ensure_ascii=False),
        filename=f"{run.id}_summary.json",
        project_id=run.project_id,
    )
    db.add(
        AnalysisArtifact(
            analysis_run_id=run.id,
            artifact_type="summary",
            filename=summary_saved["filename"],
            file_path=summary_saved["file_path"],
            mime_type="application/json",
            metadata_json={"analysis_type": run.analysis_type, "template_version": template_version},
        )
    )
    artifact_manifest.append(
        {
            "artifact_type": "summary",
            "filename": summary_saved["filename"],
            "file_path": summary_saved["file_path"],
            "format": "json",
        }
    )

    for artifact in response_data.get("artifacts") or []:
        content, filename, mime_type, metadata = _decode_artifact(artifact)
        saved = await storage_manager.save_artifact_bytes(data=content, filename=filename, project_id=run.project_id)
        artifact_type = f"report_{metadata.get('format') or 'bin'}"
        db.add(
            AnalysisArtifact(
                analysis_run_id=run.id,
                artifact_type=artifact_type,
                filename=saved["filename"],
                file_path=saved["file_path"],
                mime_type=mime_type,
                metadata_json=metadata,
            )
        )
        artifact_manifest.append(
            {
                "artifact_type": artifact_type,
                "filename": saved["filename"],
                "file_path": saved["file_path"],
                "format": metadata.get("format"),
                "mime_type": mime_type,
            }
        )

    if figure:
        chart_saved = await storage_manager.save_text_artifact(
            text=json.dumps(figure, indent=2, ensure_ascii=False),
            filename=f"{run.id}_figure.json",
            project_id=run.project_id,
        )
        db.add(
            FigureArtifact(
                analysis_run_id=run.id,
                title=str(figure.get("title") or "Analysis figure"),
                caption=figure.get("caption"),
                filename=chart_saved["filename"],
                file_path=chart_saved["file_path"],
                metadata_json=figure,
            )
        )
        artifact_manifest.append(
            {
                "artifact_type": "figure",
                "filename": chart_saved["filename"],
                "file_path": chart_saved["file_path"],
                "format": "json",
            }
        )

    run.status = "completed"
    run.script_text = _stringify_scalar(response_data.get("script"))
    run.warnings = warnings
    run.result_summary = summary
    run.engine_version = engine_version
    run.runtime_metadata = {
        **(run.runtime_metadata or {}),
        "engine": "r-engine",
        "engine_version": engine_version,
        "template_version": template_version,
        "dataset_snapshot": {
            "dataset_id": str(dataset.id) if dataset else None,
            "row_count": len(rows),
            "column_count": len(rows[0].keys()) if rows else 0,
        },
        "artifact_manifest": artifact_manifest,
        "warnings": warnings,
    }
    await db.commit()

    hydrated = await db.execute(
        select(AnalysisRun).where(AnalysisRun.id == run.id).options(selectinload(AnalysisRun.artifacts))
    )
    return hydrated.scalars().first()


async def export_analysis_run(db: AsyncSession, *, run: AnalysisRun, fmt: str) -> tuple[bytes, str, str]:
    if run.status != "completed":
        raise ValueError("Analysis run is not completed")

    normalized = fmt.lower().strip()
    if normalized not in REPORT_MIME_TYPES:
        raise ValueError("Unsupported export format")

    stmt = select(AnalysisRun).where(AnalysisRun.id == run.id).options(selectinload(AnalysisRun.artifacts))
    hydrated = await db.execute(stmt)
    current = hydrated.scalars().first()
    if current is None:
        raise ValueError("Analysis run not found")

    artifact = next(
        (
            item
            for item in current.artifacts
            if item.artifact_type == f"report_{normalized}"
            or (item.metadata_json or {}).get("format") == normalized
        ),
        None,
    )
    if artifact is None:
        raise ValueError(f"No persisted {normalized} artifact found")

    data = storage_manager.read_bytes(artifact.file_path)
    return data, artifact.mime_type, artifact.filename
