from __future__ import annotations

import base64
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


def _derive_se_from_ci(ci_low: float | None, ci_high: float | None, *, log_scale: bool = True) -> float | None:
    if ci_low is None or ci_high is None:
        return None
    try:
        if log_scale:
            if ci_low <= 0 or ci_high <= 0:
                return None
            return float((math.log(ci_high) - math.log(ci_low)) / 3.92)
        return float((ci_high - ci_low) / 3.92)
    except Exception:
        return None


def _resolve_log_effect(data: dict[str, Any]) -> float | None:
    log_effect = _to_float(data.get("log_or")) or _to_float(data.get("log_effect"))
    if log_effect is not None:
        return log_effect
    candidate = (
        _to_float(data.get("effect_value"))
        or _to_float(data.get("or_value"))
        or _to_float(data.get("adjusted_or"))
        or _to_float(data.get("adjusted_rr"))
        or _to_float(data.get("adjusted_hr"))
    )
    return _safe_log(candidate)


def _resolve_se(data: dict[str, Any], *, log_scale: bool = True) -> float | None:
    se = _to_float(data.get("effect_se")) or _to_float(data.get("se_log_or")) or _to_float(data.get("se"))
    if se is not None:
        return se
    return _derive_se_from_ci(_to_float(data.get("ci_lower_95")), _to_float(data.get("ci_upper_95")), log_scale=log_scale)


def _covariates_as_json(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False)
    except Exception:
        return str(value)


def _base_dataset_row(*, row: MatrixRow, data: dict[str, Any], preset: str, effect_measure: str, outcome_type: str) -> dict[str, Any]:
    return {
        "preset": preset,
        "row_id": str(row.id),
        "row_key": row.row_key,
        "canonical_key": data.get("canonical_key"),
        "study_id": data.get("study_id"),
        "paper_id": data.get("paper_id"),
        "paper_title": data.get("paper_title"),
        "outcome_name": data.get("outcome_name"),
        "timepoint": data.get("timepoint"),
        "effect_measure": effect_measure,
        "outcome_type": outcome_type,
        "subgroup_label": data.get("subgroup_label"),
        "subgroup_level": data.get("subgroup_level"),
        "subgroup_order": _to_float(data.get("subgroup_order")),
        "sensitivity_flag": bool(data.get("sensitivity_flag") or False),
        "sensitivity_reason": data.get("sensitivity_reason"),
        "analysis_population": data.get("analysis_population"),
        "model_type": data.get("model_type"),
        "covariates_json": _covariates_as_json(data.get("covariates_json")),
        "risk_of_bias_overall": data.get("risk_of_bias_overall"),
        "confidence": _to_float(data.get("confidence")),
    }


def _coerce_dataset_rows(rows: list[MatrixRow], *, preset: str) -> tuple[list[dict[str, Any]], list[str]]:
    dataset_rows: list[dict[str, Any]] = []
    validation_warnings: list[str] = []

    for row in rows:
        if row.row_kind != "effect":
            continue

        data = row.data_json or {}
        effect_measure = str(data.get("effect_measure") or row.effect_measure or "").upper()
        outcome_type = str(data.get("outcome_type") or "").lower()
        base = _base_dataset_row(
            row=row,
            data=data,
            preset=preset,
            effect_measure=effect_measure,
            outcome_type=outcome_type,
        )

        if preset in {"meta_binary_random", "meta_binary_fixed"}:
            if effect_measure not in {"OR", "RR", "HR"} and outcome_type != "binary":
                continue
            a = _to_float(data.get("a_events"))
            b = _to_float(data.get("b_non_events"))
            c = _to_float(data.get("c_events"))
            d = _to_float(data.get("d_non_events"))
            log_effect = _resolve_log_effect(data)
            se = _resolve_se(data, log_scale=True)
            n_e = (a + b) if (a is not None and b is not None) else None
            n_c = (c + d) if (c is not None and d is not None) else None
            if (a is None or b is None or c is None or d is None) and (log_effect is None or se is None):
                validation_warnings.append(f"{row.row_key}: missing binary counts and log effect/SE")
                continue
            dataset_rows.append(
                {
                    **base,
                    "a_events": a,
                    "b_non_events": b,
                    "c_events": c,
                    "d_non_events": d,
                    "event_e": a,
                    "n_e": n_e,
                    "event_c": c,
                    "n_c": n_c,
                    "effect_value": _to_float(data.get("effect_value")) or _to_float(data.get("or_value")),
                    "log_effect": log_effect,
                    "se": se,
                    "ci_lower_95": _to_float(data.get("ci_lower_95")),
                    "ci_upper_95": _to_float(data.get("ci_upper_95")),
                }
            )
            continue

        if preset in {"meta_continuous_md", "meta_continuous_smd"}:
            if effect_measure not in {"MD", "SMD"} and outcome_type != "continuous":
                continue
            n_i = _to_float(data.get("n_intervention"))
            n_c = _to_float(data.get("n_control"))
            mean_i = _to_float(data.get("mean_intervention"))
            mean_c = _to_float(data.get("mean_control"))
            sd_i = _to_float(data.get("sd_intervention"))
            sd_c = _to_float(data.get("sd_control"))
            effect_value = _to_float(data.get("effect_value"))
            se = _resolve_se(data, log_scale=False)

            if effect_value is None and all(v is not None for v in (mean_i, mean_c)):
                raw_diff = float(mean_i - mean_c)
                if preset == "meta_continuous_smd":
                    if all(v is not None for v in (n_i, n_c, sd_i, sd_c)) and n_i > 1 and n_c > 1:
                        pooled_sd = math.sqrt((((n_i - 1) * (sd_i**2)) + ((n_c - 1) * (sd_c**2))) / max((n_i + n_c - 2), 1))
                        effect_value = (raw_diff / pooled_sd) if pooled_sd > 0 else None
                    else:
                        effect_value = None
                else:
                    effect_value = raw_diff

            if se is None and all(v is not None for v in (n_i, n_c, sd_i, sd_c)) and n_i > 0 and n_c > 0:
                se = math.sqrt((sd_i**2 / n_i) + (sd_c**2 / n_c))

            if effect_value is None or se is None:
                validation_warnings.append(f"{row.row_key}: missing continuous effect value/SE")
                continue

            dataset_rows.append(
                {
                    **base,
                    "n_intervention": n_i,
                    "n_control": n_c,
                    "mean_intervention": mean_i,
                    "sd_intervention": sd_i,
                    "mean_control": mean_c,
                    "sd_control": sd_c,
                    "effect_value": effect_value,
                    "log_effect": effect_value,
                    "se": se,
                    "ci_lower_95": _to_float(data.get("ci_lower_95")),
                    "ci_upper_95": _to_float(data.get("ci_upper_95")),
                }
            )
            continue

        if preset == "meta_generic_iv":
            log_effect = _resolve_log_effect(data)
            se = _resolve_se(data, log_scale=True)
            if log_effect is None or se is None:
                validation_warnings.append(f"{row.row_key}: missing generic inverse-variance effect/SE")
                continue
            dataset_rows.append(
                {
                    **base,
                    "effect_value": _to_float(data.get("effect_value")),
                    "log_effect": log_effect,
                    "se": se,
                    "ci_lower_95": _to_float(data.get("ci_lower_95")),
                    "ci_upper_95": _to_float(data.get("ci_upper_95")),
                }
            )
            continue

        if preset == "meta_survival_hr":
            if effect_measure not in {"HR"} and outcome_type not in {"time_to_event", "time-to-event", "survival"}:
                continue
            hr = _to_float(data.get("adjusted_hr")) or _to_float(data.get("effect_value"))
            log_effect = _resolve_log_effect(data)
            if log_effect is None:
                log_effect = _safe_log(hr)
            se = _resolve_se(data, log_scale=True)
            if log_effect is None or se is None:
                validation_warnings.append(f"{row.row_key}: missing survival HR/log-effect/SE")
                continue
            dataset_rows.append(
                {
                    **base,
                    "effect_value": hr,
                    "log_effect": log_effect,
                    "se": se,
                    "followup_time": _to_float(data.get("followup_time")),
                    "followup_unit": data.get("followup_unit"),
                    "person_time_intervention": _to_float(data.get("person_time_intervention")),
                    "person_time_control": _to_float(data.get("person_time_control")),
                    "ci_lower_95": _to_float(data.get("ci_lower_95")),
                    "ci_upper_95": _to_float(data.get("ci_upper_95")),
                }
            )
            continue

        if preset == "meta_proportion":
            if effect_measure not in {"PROPORTION", "PLOGIT"} and outcome_type != "proportion":
                continue
            events = _to_float(data.get("events_total")) or _to_float(data.get("a_events"))
            total = _to_float(data.get("total_n"))
            if total is None:
                a = _to_float(data.get("a_events"))
                b = _to_float(data.get("b_non_events"))
                if a is not None and b is not None:
                    total = a + b
            if events is None or total is None or total <= 0:
                validation_warnings.append(f"{row.row_key}: missing events/total for proportion analysis")
                continue
            proportion = events / total
            se = _to_float(data.get("effect_se"))
            if se is None:
                se = math.sqrt((proportion * (1 - proportion)) / total)
            dataset_rows.append(
                {
                    **base,
                    "events_total": events,
                    "total_n": total,
                    "effect_value": proportion,
                    "proportion": proportion,
                    "log_effect": _safe_log(proportion if proportion > 0 else None),
                    "se": se,
                }
            )
            continue

        if preset == "meta_diag_accuracy":
            tp = _to_float(data.get("tp")) or _to_float(data.get("a_events"))
            fp = _to_float(data.get("fp")) or _to_float(data.get("c_events"))
            fn = _to_float(data.get("fn")) or _to_float(data.get("b_non_events"))
            tn = _to_float(data.get("tn")) or _to_float(data.get("d_non_events"))
            sensitivity_value = _to_float(data.get("sensitivity_value"))
            specificity_value = _to_float(data.get("specificity_value"))
            if all(v is not None for v in (tp, fp, fn, tn)):
                sensitivity_value = sensitivity_value if sensitivity_value is not None else (tp / (tp + fn) if (tp + fn) > 0 else None)
                specificity_value = specificity_value if specificity_value is not None else (tn / (tn + fp) if (tn + fp) > 0 else None)
            if sensitivity_value is None or specificity_value is None:
                validation_warnings.append(f"{row.row_key}: missing diagnostic TP/FP/FN/TN or sensitivity/specificity")
                continue
            dataset_rows.append(
                {
                    **base,
                    "tp": tp,
                    "fp": fp,
                    "fn": fn,
                    "tn": tn,
                    "sensitivity": sensitivity_value,
                    "specificity": specificity_value,
                    "effect_value": sensitivity_value,
                    "log_effect": _safe_log(sensitivity_value),
                    "se": _to_float(data.get("effect_se")),
                }
            )
            continue

        if preset == "risk_of_bias_summary":
            if not data.get("risk_of_bias_overall"):
                continue
            dataset_rows.append(
                {
                    **base,
                    "risk_of_bias_overall": data.get("risk_of_bias_overall"),
                    "effect_value": _to_float(data.get("effect_value")),
                }
            )
            continue

        if preset == "publication_bias_suite":
            log_effect = _resolve_log_effect(data)
            se = _resolve_se(data, log_scale=True)
            if log_effect is None or se is None:
                validation_warnings.append(f"{row.row_key}: missing log effect/SE for publication-bias diagnostics")
                continue
            dataset_rows.append(
                {
                    **base,
                    "effect_value": _to_float(data.get("effect_value")),
                    "log_effect": log_effect,
                    "se": se,
                    "ci_lower_95": _to_float(data.get("ci_lower_95")),
                    "ci_upper_95": _to_float(data.get("ci_upper_95")),
                }
            )

    return dataset_rows, validation_warnings


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
    dataset_rows, validation_warnings = _coerce_dataset_rows(rows, preset=preset)
    if not dataset_rows:
        warning_text = "; ".join(validation_warnings[:8]) if validation_warnings else "No effect rows matched this preset."
        raise ValueError(f"Dataset derivation failed for preset `{preset}`: {warning_text}")

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
        schema_json={
            "columns": list(frame.columns),
            "preset_contract": preset,
            "validation_warnings": validation_warnings,
        },
        build_params={**(build_params or {}), "validation_warnings": validation_warnings},
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
        run.status = "failed"
        run.summary_json = {
            "preset": preset,
            "rows": len(rows),
            "supports_publication": False,
            "note": "R engine execution failed. No publication artifacts generated.",
        }
        run.warnings = [f"R engine request failed: {exc}"]
        run.engine = "r-engine"
        run.engine_version = None
        run.runtime_json = {"preset": preset, "rows": len(rows), "supports_publication": False}
        run.completed_at = datetime.now(timezone.utc)
        await db.commit()
        stmt = select(MetaRun).where(MetaRun.id == run.id).options(selectinload(MetaRun.artifacts))
        hydrated = await db.execute(stmt)
        return hydrated.scalars().first()

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

        if svg_bytes is None and png_bytes is None and pdf_bytes is None:
            warnings.append(f"Figure `{kind}` was not generated by the R engine.")
            continue

        if svg_bytes is not None:
            artifacts_to_create.append((f"{kind}_svg", f"{run.id}_{kind}.svg", svg_bytes, "image/svg+xml", {"preset": preset, "figure": kind}))
        if png_bytes is not None:
            artifacts_to_create.append((f"{kind}_png", f"{run.id}_{kind}.png", png_bytes, "image/png", {"preset": preset, "figure": kind}))
        if pdf_bytes is not None:
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
    run.engine = "r-engine"
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
