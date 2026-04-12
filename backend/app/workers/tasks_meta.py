"""Meta-analysis extraction and export worker jobs."""
from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.database import async_session_maker
from app.workers._run_coro import run_coro
from app.workers.job_tracker import (
    job_mark_completed,
    job_mark_failed,
    job_mark_started,
    job_set_progress,
)
from app.core.logger import logger


def meta_extract_paper_job(job_db_id: str, batch_id: str, item_id: str, paper_id: str) -> dict[str, Any]:
    """RQ job - SYNC wrapper"""

    from app.config import settings
    from app.services.meta_extractor.quality_gate import quality_gate
    from app.services.meta_extractor.extractor import MetaExtractorInput, extract_and_validate
    from app.services.pdf_processor import extract_text, check_if_scanned

    async def _async_logic() -> dict[str, Any]:
        job_uuid = UUID(job_db_id)
        paper_uuid = UUID(paper_id)
        batch_uuid = UUID(batch_id)
        item_uuid = UUID(item_id)

        warnings: list[str] = []

        try:
            await job_mark_started(job_uuid)
            await job_set_progress(job_uuid, 5, status="started", result_patch={"warnings": [], "errors": []})

            async with async_session_maker() as db:
                from app.models.paper import Paper
                from app.models.meta_extractor import (
                    ExtractedStudy,
                    ExtractedEffectSize,
                    ExtractedRiskOfBias,
                    MetaExtractionItem,
                    MetaExtractionBatch,
                )
                from app.core.storage import storage_manager

                paper = await db.get(Paper, paper_uuid)
                if not paper:
                    raise ValueError("Paper no encontrado")

                # Validate file exists and encrypted
                abs_path = (storage_manager.base_dir / paper.file_path).resolve()
                try:
                    abs_path.relative_to(storage_manager.base_dir)
                except ValueError:
                    raise ValueError("Invalid paper file path")

                if not abs_path.exists():
                    raise FileNotFoundError("Archivo PDF no existe")

                import fitz

                try:
                    doc = fitz.open(abs_path)
                    if doc.is_encrypted:
                        raise ValueError("PDF protegido, no se puede procesar")
                    doc.close()
                except Exception as e:
                    raise ValueError(str(e))

                item = await db.get(MetaExtractionItem, item_uuid)
                if item:
                    item.status = "started"
                    await db.commit()

                await job_set_progress(job_uuid, 20, status="progress")

                text = extract_text(abs_path)
                scanned = check_if_scanned(abs_path, min_chars=100)

                await job_set_progress(job_uuid, 40, status="progress")

                # Tables
                tables_md_parts: list[str] = []
                try:
                    import pdfplumber

                    with pdfplumber.open(str(abs_path)) as pdf:
                        for i, page in enumerate(pdf.pages, 1):
                            tbs = page.extract_tables() or []
                            for ti, tbl in enumerate(tbs, 1):
                                tables_md_parts.append(f"\n\n### Table p{i}-{ti}\n" + "\n".join(["\t".join([str(c) if c is not None else "" for c in row]) for row in tbl]))
                except Exception as _tbl_err:
                    logger.warning(f"[meta_extract_paper_job] pdfplumber table extraction failed for paper={paper_id}: {_tbl_err!r}")

                tables_markdown = "\n".join(tables_md_parts)

                await job_set_progress(job_uuid, 55, status="progress")

                # OCR decision tree (optional)
                from app.services.meta_extractor.ocr import (
                    detect_ocr_availability,
                    ocr_pages_best_effort,
                    ocrmypdf_preprocess,
                )

                ocr_snippets = ""
                ocr_used = False

                ocr_av = detect_ocr_availability(ocr_enabled=bool(getattr(settings, "OCR_ENABLED", False)))

                # a) If full PDF seems scanned -> try ocrmypdf preprocessing (if enabled + available)
                text_for_llm = text
                if scanned and ocr_av.ocr_enabled and ocr_av.ocrmypdf_available:
                    import tempfile

                    with tempfile.TemporaryDirectory() as td:
                        out_pdf = Path(td) / "ocr.pdf"
                        ok = ocrmypdf_preprocess(abs_path, out_pdf)
                        if ok and out_pdf.exists():
                            try:
                                text_for_llm = extract_text(out_pdf)
                                ocr_snippets, ocr_used = ocr_pages_best_effort(out_pdf, max_pages=3)
                            except Exception as _ocr_err:
                                logger.warning(f"[meta_extract_paper_job] OCR text extraction failed for paper={paper_id}: {_ocr_err!r}")
                        else:
                            warnings.append("Scanned PDF preprocessing disabled or failed.")
                elif scanned and ocr_av.ocr_enabled and not ocr_av.ocrmypdf_available:
                    warnings.append("ocrmypdf not installed. Scanned PDF preprocessing disabled.")

                # b) If PDF has text but might include tables/data in images -> OCR few pages best-effort
                if (not scanned) and ocr_av.ocr_enabled and ocr_av.tesseract_available:
                    # only if we extracted very few tables
                    if len(tables_md_parts) == 0:
                        ocr_snippets2, used2 = ocr_pages_best_effort(abs_path, max_pages=2)
                        if used2:
                            ocr_snippets = (ocr_snippets + "\n\n" + ocr_snippets2).strip()
                            ocr_used = True
                elif ocr_av.ocr_enabled and not ocr_av.tesseract_available:
                    warnings.append("Tesseract not installed. OCR disabled. Install with: brew install tesseract")

                await job_set_progress(job_uuid, 70, status="progress")

                # LLM structuring
                inp = MetaExtractorInput(text=text_for_llm, tables_markdown=tables_markdown, ocr_snippets=ocr_snippets)
                extracted = await extract_and_validate(inp)

                await job_set_progress(job_uuid, 95, status="progress")

                extracted, q_warnings = quality_gate(extracted)
                warnings.extend(q_warnings)

                # If LLM returned no ROB rows, auto-generate defaults by study design
                if not (extracted.risk_of_bias or []):
                    from app.services.meta_extractor.rob_defaults import generate_default_rob

                    tool, rob_rows = generate_default_rob(getattr(extracted, "study_design", None))
                    extracted.risk_of_bias = rob_rows
                    warnings.append(
                        f"ROB domains auto-generated (study design: {getattr(extracted, 'study_design', None)}, tool: {tool}). "
                        "All judgements set to 'unclear' — requires manual review."
                    )
                    rob_auto_generated = True
                else:
                    rob_auto_generated = False

                # Versioning
                q = await db.execute(
                    select(ExtractedStudy).where(ExtractedStudy.paper_id == paper_uuid).where(ExtractedStudy.is_current == True)  # noqa
                )
                prev = q.scalars().first()
                next_version = 1
                if prev:
                    prev.is_current = False
                    next_version = int(prev.version) + 1

                study = ExtractedStudy(
                    project_id=paper.project_id,
                    paper_id=paper_uuid,
                    batch_id=batch_uuid,
                    version=next_version,
                    is_current=True,
                    study_json=extracted.model_dump(),
                    extraction_confidence=float(extracted.extraction_confidence or 0.0),
                )
                db.add(study)
                await db.commit()
                await db.refresh(study)

                # Clear and add effects/rob
                for es in extracted.effect_sizes:
                    db.add(
                        ExtractedEffectSize(
                            extracted_study_id=study.id,
                            outcome_name=es.outcome_name,
                            timepoint=es.timepoint,
                            arm_intervention=es.arm_intervention,
                            arm_control=es.arm_control,
                            effect_measure=es.effect_measure,
                            outcome_type=es.outcome_type or "binary",
                            outcome_unit=es.outcome_unit,
                            comparator_type=es.comparator_type,
                            effect_direction=es.effect_direction,
                            a_events=es.a_events,
                            b_non_events=es.b_non_events,
                            c_events=es.c_events,
                            d_non_events=es.d_non_events,
                            events_total=es.events_total,
                            total_n=es.total_n,
                            or_value=es.or_value,
                            log_or=es.log_or,
                            se_log_or=es.se_log_or,
                            effect_value=es.effect_value,
                            effect_se=es.effect_se,
                            weight=es.weight,
                            ci_lower_95=es.ci_lower_95,
                            ci_upper_95=es.ci_upper_95,
                            adjusted_or=es.adjusted_or,
                            adjusted_rr=es.adjusted_rr,
                            adjusted_hr=es.adjusted_hr,
                            n_intervention=es.n_intervention,
                            n_control=es.n_control,
                            mean_intervention=es.mean_intervention,
                            sd_intervention=es.sd_intervention,
                            mean_control=es.mean_control,
                            sd_control=es.sd_control,
                            median_intervention=es.median_intervention,
                            iqr_intervention=es.iqr_intervention,
                            median_control=es.median_control,
                            iqr_control=es.iqr_control,
                            followup_time=es.followup_time,
                            followup_unit=es.followup_unit,
                            person_time_intervention=es.person_time_intervention,
                            person_time_control=es.person_time_control,
                            tp=es.tp,
                            fp=es.fp,
                            fn=es.fn,
                            tn=es.tn,
                            sensitivity_value=es.sensitivity_value,
                            specificity_value=es.specificity_value,
                            subgroup_label=es.subgroup_label,
                            subgroup_level=es.subgroup_level,
                            subgroup_order=es.subgroup_order,
                            sensitivity_flag=bool(es.sensitivity_flag or False),
                            sensitivity_reason=es.sensitivity_reason,
                            analysis_population=es.analysis_population,
                            model_type=es.model_type,
                            covariates_json=es.covariates_json,
                            adjustment_variables=es.adjustment_variables,
                            is_adjusted=es.is_adjusted,
                            raw_extracted_value=es.raw_extracted_value,
                            source_type=es.source_type,
                            source_page=es.page_number,
                            source_locator={"table_id": es.table_id, "figure_id": es.figure_id},
                            confidence=float(es.extraction_confidence or 0.0),
                            comments=es.comments,
                        )
                    )

                for r in extracted.risk_of_bias:
                    db.add(
                        ExtractedRiskOfBias(
                            extracted_study_id=study.id,
                            tool=r.tool,
                            domain=r.domain_name,
                            judgement=r.judgement,
                            support_text=r.support_for_judgement,
                            auto_generated=bool(rob_auto_generated),
                        )
                    )

                if item:
                    item.status = "completed"
                    item.result_summary = {
                        "study_id": str(study.id),
                        "extraction_confidence": study.extraction_confidence,
                        "ocr_used": ocr_used,
                    }
                    item.error_message = None

                await db.commit()

                # Finalize batch status when last item finishes (single-worker friendly)
                try:
                    qst = await db.execute(select(MetaExtractionItem.status).where(MetaExtractionItem.batch_id == batch_uuid))
                    statuses = [s for (s,) in qst.all()]
                    if statuses and all(s in ("completed", "failed") for s in statuses):
                        b = await db.get(MetaExtractionBatch, batch_uuid)
                        if b:
                            b.status = "failed" if any(s == "failed" for s in statuses) else "completed"
                            await db.commit()
                except Exception as _fin_err:
                    logger.warning(f"[meta_extract_paper_job] batch finalization failed for batch={batch_id}: {_fin_err!r}")

            study_id = str(study.id)
            await job_mark_completed(
                job_uuid,
                result={
                    "output": {"study_id": study_id, "paper_id": paper_id},
                    "warnings": warnings,
                    "errors": [],
                },
            )
            return {"study_id": study_id, "warnings": warnings}
        except Exception as e:
            # Persist failure on item too (UI relies on item.status)
            try:
                async with async_session_maker() as db2:
                    from app.models.meta_extractor import MetaExtractionBatch, MetaExtractionItem

                    it2 = await db2.get(MetaExtractionItem, item_uuid)
                    if it2:
                        it2.status = "failed"
                        it2.error_message = str(e)
                        await db2.commit()

                    # Finalize batch status if this was the last pending item
                    try:
                        qst = await db2.execute(select(MetaExtractionItem.status).where(MetaExtractionItem.batch_id == batch_uuid))
                        statuses = [s for (s,) in qst.all()]
                        if statuses and all(s in ("completed", "failed") for s in statuses):
                            b = await db2.get(MetaExtractionBatch, batch_uuid)
                            if b:
                                b.status = "failed" if any(s == "failed" for s in statuses) else "completed"
                                await db2.commit()
                    except Exception as _fin2_err:
                        logger.warning(f"[meta_extract_paper_job] failure-path batch finalization failed for batch={batch_id}: {_fin2_err!r}")
            except Exception as _item_err:
                # Best-effort; don't mask the original failure.
                logger.warning(f"[meta_extract_paper_job] failed to persist item failure for item={item_id}: {_item_err!r}")

            await job_mark_failed(job_uuid, str(e))
            return {"output": {}, "warnings": warnings, "errors": [str(e)]}

    return run_coro(_async_logic())


def meta_extract_batch_job(job_db_id: str, batch_id: str) -> dict[str, Any]:
    """Enqueue per-paper extraction jobs for a batch. SYNC wrapper.

    IMPORTANT (dev ergonomics): this job MUST NOT block waiting for child jobs.
    Waiting would deadlock when running with a single worker.

    Batch completion is finalized by `meta_extract_paper_job` when the last item finishes.
    """

    async def _async_logic() -> dict[str, Any]:
        job_uuid = UUID(job_db_id)
        batch_uuid = UUID(batch_id)

        try:
            await job_mark_started(job_uuid)
            await job_set_progress(job_uuid, 5, status="started")

            async with async_session_maker() as db:
                from app.models.meta_extractor import MetaExtractionBatch, MetaExtractionItem
                from app.models.job import Job

                batch = await db.get(MetaExtractionBatch, batch_uuid)
                if not batch:
                    raise ValueError("Batch no encontrado")

                batch.status = "processing"
                await db.commit()

                q = await db.execute(select(MetaExtractionItem).where(MetaExtractionItem.batch_id == batch_uuid))
                items = q.scalars().all()

                from app.services.jobs import get_job_queue

                rq = get_job_queue()

                enqueued = 0
                for it in items:
                    # create a DB job per item
                    job_rec = Job(
                        user_id=batch.user_id,
                        job_type="meta_extract_paper",
                        status="queued",
                        input_params={"batch_id": str(batch_uuid), "item_id": str(it.id), "paper_id": str(it.paper_id)},
                        result={},
                        progress_percent=0,
                    )
                    db.add(job_rec)
                    it.status = "queued"
                    it.error_message = None
                    await db.commit()
                    await db.refresh(job_rec)

                    rq_job = rq.enqueue(
                        meta_extract_paper_job,
                        args=(str(job_rec.id), str(batch_uuid), str(it.id), str(it.paper_id)),
                        job_timeout="30m",
                    )
                    job_rec.result = {"rq_job_id": rq_job.id}
                    await db.commit()

                    enqueued += 1
                    await job_set_progress(job_uuid, min(95, 5 + int((enqueued / max(len(items), 1)) * 90)), status="progress")

            await job_mark_completed(
                job_uuid,
                result={"output": {"batch_id": str(batch_uuid), "enqueued": enqueued}, "warnings": [], "errors": []},
            )
            return {"batch_id": str(batch_uuid), "enqueued": enqueued}
        except Exception as e:
            await job_mark_failed(job_uuid, str(e))
            return {"output": {}, "warnings": [], "errors": [str(e)]}

    return run_coro(_async_logic())


def meta_export_excel_job(job_db_id: str, project_id: str, batch_id: str = "") -> dict[str, Any]:
    """Generate XLSX export for meta extractor. SYNC wrapper."""

    from app.services.meta_extractor.export_service import create_meta_export

    async def _async_logic() -> dict[str, Any]:
        job_uuid = UUID(job_db_id)
        proj_uuid = UUID(project_id)
        batch_uuid = UUID(batch_id) if batch_id else None

        try:
            await job_mark_started(job_uuid)
            await job_set_progress(job_uuid, 10, status="started")

            async with async_session_maker() as db:
                await job_set_progress(job_uuid, 60, status="progress")
                export = await create_meta_export(db=db, project_id=proj_uuid, batch_id=batch_uuid)
                await job_set_progress(job_uuid, 90, status="progress")

            await job_mark_completed(
                job_uuid,
                result={"output": {"export_id": str(export.id)}, "warnings": [], "errors": []},
            )
            return {"export_id": str(export.id)}
        except Exception as e:
            await job_mark_failed(job_uuid, str(e))
            return {"output": {}, "warnings": [], "errors": [str(e)]}

    return run_coro(_async_logic())


def meta_export_job(job_db_id: str, project_id: str, batch_id: str = "", fmt: str = "xlsx") -> dict[str, Any]:
    """Unified export job dispatcher — routes to xlsx or csv_bundle. SYNC wrapper."""
    return meta_export_excel_job(job_db_id, project_id, batch_id)
