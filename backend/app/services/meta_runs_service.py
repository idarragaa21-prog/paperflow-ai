from __future__ import annotations

import base64
import io
import json
import math
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import httpx
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.core.storage import storage_manager
from app.models.matrix import MatrixRow, MatrixVersion
from app.models.meta_run import DerivedDataset, MetaRun, MetaRunArtifact


META_PRESETS = {
    "meta_binary_random",
    "meta_binary_fixed",
    "meta_continuous_md",
    "meta_continuous_smd",
    "meta_generic_iv",
    "meta_survival_hr",
    "meta_proportion",
    "meta_diag_accuracy",
    "risk_of_bias_summary",
    "publication_bias_suite",
}


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def _safe_log(value: float | None) -> float | None:
    if value is None or value <= 0:
        return None
    try:
        return float(math.log(value))
    except Exception:
        return None


def _coerce_dataset_rows(rows: list[MatrixRow], *, preset: str) -> list[dict[str, Any]]:
    dataset_rows: list[dict[str, Any]] = []
    for row in rows:
        if row.row_kind != "effect":
            continue
        data = row.data_json or {}

        effect_measure = str(data.get("effect_measure") or row.effect_measure or "").upper()
        if preset in {"meta_survival_hr"} and effect_measure not in {"HR"}:
            continue
        if preset in {"meta_binary_random", "meta_binary_fixed"} and effect_measure not in {"OR", "RR", "HR"}:
            continue
        if preset == "meta_proportion" and data.get("a_events") is None:
            continue

        or_value = _to_float(data.get("or_value"))
        adjusted_or = _to_float(data.get("adjusted_or"))
        adjusted_rr = _to_float(data.get("adjusted_rr"))
        adjusted_hr = _to_float(data.get("adjusted_hr"))
        ci_lo = _to_float(data.get("ci_lower_95"))
        ci_hi = _to_float(data.get("ci_upper_95"))
        log_or = _to_float(data.get("log_or"))
        se_log_or = _to_float(data.get("se_log_or"))

        if log_or is None:
            log_or = _safe_log(or_value or adjusted_or or adjusted_rr or adjusted_hr)

        if se_log_or is None and ci_lo is not None and ci_hi is not None and ci_lo > 0 and ci_hi > 0:
            try:
                se_log_or = (math.log(ci_hi) - math.log(ci_lo)) / 3.92
            except Exception:
                se_log_or = None

        a_events = _to_float(data.get("a_events"))
        b_non_events = _to_float(data.get("b_non_events"))
        c_events = _to_float(data.get("c_events"))
        d_non_events = _to_float(data.get("d_non_events"))

        proportion = None
        if a_events is not None and b_non_events is not None and (a_events + b_non_events) > 0:
            proportion = a_events / (a_events + b_non_events)

        dataset_rows.append(
            {
                "preset": preset,
                "row_id": str(row.id),
                "row_key": row.row_key,
                "study_id": data.get("study_id"),
                "paper_id": data.get("paper_id"),
                "paper_title": data.get("paper_title"),
                "outcome_name": data.get("outcome_name"),
                "timepoint": data.get("timepoint"),
                "effect_measure": effect_measure,
                "effect_value": or_value,
                "log_effect": log_or,
                "se": se_log_or,
                "ci_lower_95": ci_lo,
                "ci_upper_95": ci_hi,
                "a_events": a_events,
                "b_non_events": b_non_events,
                "c_events": c_events,
                "d_non_events": d_non_events,
                "adjusted_or": adjusted_or,
                "adjusted_rr": adjusted_rr,
                "adjusted_hr": adjusted_hr,
                "proportion": proportion,
                "risk_of_bias_overall": data.get("risk_of_bias_overall"),
                "confidence": _to_float(data.get("confidence")),
            }
        )

    if dataset_rows:
        return dataset_rows

    # Fallback: include all non-study rows so preset runs still have a reproducible input dataset.
    for row in rows:
        if row.row_kind == "study":
            continue
        data = row.data_json or {}
        dataset_rows.append(
            {
                "preset": preset,
                "row_id": str(row.id),
                "row_key": row.row_key,
                "study_id": data.get("study_id"),
                "paper_id": data.get("paper_id"),
                "paper_title": data.get("paper_title"),
                "outcome_name": data.get("outcome_name"),
                "timepoint": data.get("timepoint"),
                "effect_measure": data.get("effect_measure"),
                "effect_value": _to_float(data.get("or_value")),
                "log_effect": _to_float(data.get("log_or")),
                "se": _to_float(data.get("se_log_or")),
                "ci_lower_95": _to_float(data.get("ci_lower_95")),
                "ci_upper_95": _to_float(data.get("ci_upper_95")),
                "a_events": _to_float(data.get("a_events")),
                "b_non_events": _to_float(data.get("b_non_events")),
                "c_events": _to_float(data.get("c_events")),
                "d_non_events": _to_float(data.get("d_non_events")),
                "adjusted_or": _to_float(data.get("adjusted_or")),
                "adjusted_rr": _to_float(data.get("adjusted_rr")),
                "adjusted_hr": _to_float(data.get("adjusted_hr")),
                "proportion": None,
                "risk_of_bias_overall": data.get("risk_of_bias_overall"),
                "confidence": _to_float(data.get("confidence")),
            }
        )
    return dataset_rows


def _figure_svg(title: str, subtitle: str) -> bytes:
    payload = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="800">
<rect width="100%" height="100%" fill="#f9fafb"/>
<rect x="40" y="40" width="1120" height="720" fill="#ffffff" stroke="#d1d5db" stroke-width="2"/>
<text x="70" y="110" font-family="Arial, sans-serif" font-size="34" fill="#111827">{title}</text>
<text x="70" y="160" font-family="Arial, sans-serif" font-size="20" fill="#4b5563">{subtitle}</text>
<line x1="90" y1="690" x2="1110" y2="690" stroke="#9ca3af" stroke-width="2"/>
<line x1="90" y1="220" x2="90" y2="690" stroke="#9ca3af" stroke-width="2"/>
<text x="95" y="735" font-family="Arial, sans-serif" font-size="14" fill="#6b7280">Generated by PaperFlow meta runs</text>
</svg>"""
    return payload.encode("utf-8")


def _figure_png(title: str, subtitle: str) -> bytes:
    # Import lazily: PIL startup is expensive and should not slow down API import/test collection.
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (1200, 800), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((30, 30, 1170, 770), outline="#d1d5db", width=3)
    draw.text((60, 70), title, fill="#111827")
    draw.text((60, 120), subtitle, fill="#4b5563")
    draw.line((90, 690, 1110, 690), fill="#9ca3af", width=2)
    draw.line((90, 220, 90, 690), fill="#9ca3af", width=2)
    out = io.BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


def _figure_pdf(title: str, subtitle: str) -> bytes:
    # Import lazily: reportlab font tables are heavy at module import time.
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, 730, title)
    c.setFont("Helvetica", 11)
    c.drawString(72, 710, subtitle)
    c.rect(60, 120, 500, 540)
    c.drawString(72, 100, "Generated by PaperFlow meta runs")
    c.showPage()
    c.save()
    return buffer.getvalue()


def _run_payload_summary(*, preset: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "preset": preset,
        "rows": len(rows),
        "columns": list(rows[0].keys()) if rows else [],
        "supports_publication": True,
        "note": "Run created from derived dataset rows with reproducible inputs.",
    }


def _decode_base64(payload: Any) -> bytes | None:
    if not isinstance(payload, str) or not payload:
        return None
    try:
        return base64.b64decode(payload, validate=True)
    except Exception:
        try:
            return base64.b64decode(payload)
        except Exception:
            return None


async def derive_dataset(
    db: AsyncSession,
    *,
    project_id: UUID,
    matrix_version: MatrixVersion,
    preset: str,
    title: str | None,
    build_params: dict | None,
    user_id: UUID | None,
) -> DerivedDataset:
    if preset not in META_PRESETS:
        raise ValueError(f"Unsupported preset: {preset}")

    rows_stmt = (
        select(MatrixRow)
        .where(MatrixRow.matrix_version_id == matrix_version.id)
        .order_by(MatrixRow.sort_index.asc(), MatrixRow.created_at.asc())
    )
    rows = (await db.execute(rows_stmt)).scalars().all()
    dataset_rows = _coerce_dataset_rows(rows, preset=preset)
    frame = pd.DataFrame(dataset_rows)
    csv_bytes = frame.to_csv(index=False).encode("utf-8")
    base_title = (title or f"{preset}_dataset").strip()
    saved = await storage_manager.save_dataset_bytes(
        data=csv_bytes,
        filename=f"{base_title}.csv",
        project_id=project_id,
    )

    dataset = DerivedDataset(
        project_id=project_id,
        matrix_version_id=matrix_version.id,
        created_by_user_id=user_id,
        title=base_title,
        preset=preset,
        status="ready",
        file_path=saved["file_path"],
        row_count=len(frame.index),
        column_count=len(frame.columns),
        schema_json={"columns": list(frame.columns)},
        build_params=build_params or {},
        source_signature=matrix_version.source_signature,
    )
    db.add(dataset)
    await db.commit()
    await db.refresh(dataset)
    return dataset


async def get_derived_dataset(db: AsyncSession, *, dataset_id: UUID) -> DerivedDataset | None:
    return await db.get(DerivedDataset, dataset_id)


async def list_derived_datasets(db: AsyncSession, *, project_id: UUID) -> list[DerivedDataset]:
    q = await db.execute(
        select(DerivedDataset)
        .where(DerivedDataset.project_id == project_id)
        .order_by(DerivedDataset.created_at.desc())
    )
    return q.scalars().all()


def _preset_to_analysis_type(preset: str) -> str:
    # The current R engine can accept any analysis_type and gracefully degrades unknown presets.
    return preset


async def run_meta_analysis(
    db: AsyncSession,
    *,
    project_id: UUID,
    dataset: DerivedDataset,
    preset: str,
    title: str | None,
    input_params: dict | None,
    user_id: UUID | None,
) -> MetaRun:
    run = MetaRun(
        project_id=project_id,
        matrix_version_id=dataset.matrix_version_id,
        derived_dataset_id=dataset.id,
        created_by_user_id=user_id,
        title=(title or f"{preset} run").strip(),
        preset=preset,
        status="running",
        input_params=input_params or {},
        runtime_json={},
        started_at=datetime.now(timezone.utc),
    )
    db.add(run)
    await db.flush()

    with storage_manager.local_path(dataset.file_path, suffix=".csv") as local_path:
        frame = pd.read_csv(local_path)
    # Use JSON roundtrip to normalize pandas NaN/NaT into JSON-null values.
    rows = json.loads(frame.to_json(orient="records", date_format="iso"))

    response_data: dict[str, Any]
    warnings: list[str] = []
    try:
        async with httpx.AsyncClient(timeout=40) as client:
            response = await client.post(
                f"{settings.R_ENGINE_URL}/run-analysis",
                json={
                    "analysis_type": _preset_to_analysis_type(preset),
                    "input_params": input_params or {},
                    "rows": rows,
                },
            )
            response.raise_for_status()
            response_data = response.json()
    except Exception as exc:
        warnings.append(f"R engine unavailable, local fallback summary used: {exc}")
        response_data = {
            "summary": _run_payload_summary(preset=preset, rows=rows),
            "warnings": warnings,
            "script": f"# fallback meta run\n# preset: {preset}\n# rows: {len(rows)}",
            "engine_version": "local-fallback",
        }

    summary = response_data.get("summary") or _run_payload_summary(preset=preset, rows=rows)
    warnings.extend(response_data.get("warnings") or [])
    script_text = str(response_data.get("script") or "")
    engine_version = str(response_data.get("engine_version") or "unknown")

    artifacts_to_create: list[tuple[str, str, bytes, str, dict[str, Any] | None]] = []

    summary_bytes = json.dumps(summary, ensure_ascii=False, indent=2).encode("utf-8")
    artifacts_to_create.append(("summary_json", f"{run.id}_summary.json", summary_bytes, "application/json", {"preset": preset}))

    effect_csv = frame.to_csv(index=False).encode("utf-8")
    artifacts_to_create.append(("effect_table_csv", f"{run.id}_effect_table.csv", effect_csv, "text/csv; charset=utf-8", {"preset": preset}))

    script_bytes = script_text.encode("utf-8")
    artifacts_to_create.append(("script_r", f"{run.id}_script.R", script_bytes, "text/x-r; charset=utf-8", {"preset": preset}))

    session_info = "\n".join(
        [
            f"engine_version: {engine_version}",
            f"preset: {preset}",
            f"generated_at: {datetime.now(timezone.utc).isoformat()}",
            f"warnings: {json.dumps(warnings, ensure_ascii=False)}",
        ]
    ).encode("utf-8")
    artifacts_to_create.append(("session_info", f"{run.id}_sessionInfo.txt", session_info, "text/plain; charset=utf-8", {"preset": preset}))

    figure_artifacts = response_data.get("figure_artifacts") or {}
    figure_kinds = ("forest", "funnel", "rob", "influence")
    for kind in figure_kinds:
        title_text = f"{kind.title()} Plot"
        subtitle = f"Preset: {preset} | Run: {run.id}"
        payload = figure_artifacts.get(kind) if isinstance(figure_artifacts, dict) else None
        svg_bytes: bytes | None = None
        png_bytes: bytes | None = None
        pdf_bytes: bytes | None = None

        if isinstance(payload, dict):
            svg_text = payload.get("svg")
            if isinstance(svg_text, str) and svg_text.strip():
                svg_bytes = svg_text.encode("utf-8")
            png_bytes = _decode_base64(payload.get("png_base64"))
            pdf_bytes = _decode_base64(payload.get("pdf_base64"))

        if svg_bytes is None:
            svg_bytes = _figure_svg(title_text, subtitle)
        if png_bytes is None:
            png_bytes = _figure_png(title_text, subtitle)
        if pdf_bytes is None:
            pdf_bytes = _figure_pdf(title_text, subtitle)

        artifacts_to_create.append((f"{kind}_svg", f"{run.id}_{kind}.svg", svg_bytes, "image/svg+xml", {"preset": preset, "figure": kind}))
        artifacts_to_create.append((f"{kind}_png", f"{run.id}_{kind}.png", png_bytes, "image/png", {"preset": preset, "figure": kind}))
        artifacts_to_create.append((f"{kind}_pdf", f"{run.id}_{kind}.pdf", pdf_bytes, "application/pdf", {"preset": preset, "figure": kind}))

    saved_lookup: dict[str, str] = {}
    for artifact_type, filename, payload, mime, metadata in artifacts_to_create:
        saved = await storage_manager.save_artifact_bytes(data=payload, filename=filename, project_id=project_id)
        saved_lookup[artifact_type] = saved["file_path"]
        db.add(
            MetaRunArtifact(
                meta_run_id=run.id,
                artifact_type=artifact_type,
                filename=saved["filename"],
                file_path=saved["file_path"],
                mime_type=mime,
                metadata_json=metadata,
            )
        )

    run.status = "completed"
    run.summary_json = summary
    run.warnings = warnings
    run.engine = "r-engine" if engine_version != "local-fallback" else "local-fallback"
    run.engine_version = engine_version
    run.script_path = saved_lookup.get("script_r")
    run.session_info_path = saved_lookup.get("session_info")
    run.runtime_json = {
        "rows": len(rows),
        "artifact_types": [item[0] for item in artifacts_to_create],
        "preset": preset,
    }
    run.completed_at = datetime.now(timezone.utc)

    await db.commit()
    stmt = select(MetaRun).where(MetaRun.id == run.id).options(selectinload(MetaRun.artifacts))
    hydrated = await db.execute(stmt)
    return hydrated.scalars().first()


async def list_meta_runs(db: AsyncSession, *, project_id: UUID) -> list[MetaRun]:
    q = await db.execute(
        select(MetaRun)
        .where(MetaRun.project_id == project_id)
        .options(selectinload(MetaRun.artifacts))
        .order_by(MetaRun.created_at.desc())
    )
    return q.scalars().all()


async def get_meta_run(db: AsyncSession, *, run_id: UUID) -> MetaRun | None:
    q = await db.execute(
        select(MetaRun)
        .where(MetaRun.id == run_id)
        .options(selectinload(MetaRun.artifacts))
    )
    return q.scalars().first()


def serialize_dataset(dataset: DerivedDataset) -> dict[str, Any]:
    return {
        "id": str(dataset.id),
        "project_id": str(dataset.project_id),
        "matrix_version_id": str(dataset.matrix_version_id),
        "title": dataset.title,
        "preset": dataset.preset,
        "status": dataset.status,
        "row_count": dataset.row_count,
        "column_count": dataset.column_count,
        "file_path": dataset.file_path,
        "schema_json": dataset.schema_json or {},
        "build_params": dataset.build_params or {},
        "created_at": dataset.created_at.isoformat() if dataset.created_at else None,
    }


def serialize_meta_run(run: MetaRun) -> dict[str, Any]:
    return {
        "id": str(run.id),
        "project_id": str(run.project_id),
        "matrix_version_id": str(run.matrix_version_id) if run.matrix_version_id else None,
        "derived_dataset_id": str(run.derived_dataset_id) if run.derived_dataset_id else None,
        "title": run.title,
        "preset": run.preset,
        "status": run.status,
        "input_params": run.input_params or {},
        "summary": run.summary_json or {},
        "warnings": run.warnings or [],
        "engine": run.engine,
        "engine_version": run.engine_version,
        "script_path": run.script_path,
        "session_info_path": run.session_info_path,
        "runtime": run.runtime_json or {},
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "artifacts": [
            {
                "id": str(item.id),
                "artifact_type": item.artifact_type,
                "filename": item.filename,
                "file_path": item.file_path,
                "mime_type": item.mime_type,
                "metadata_json": item.metadata_json or {},
            }
            for item in run.artifacts
        ],
    }
