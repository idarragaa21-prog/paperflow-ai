from __future__ import annotations

import asyncio
import threading
from collections.abc import Coroutine
from datetime import datetime
from pathlib import Path
from typing import Any, TypeVar
from uuid import UUID

from sqlalchemy import select

from app.database import async_session_maker
from app.models.note import Note
from app.models.paper import Paper
from app.models.presentation import Presentation
from app.services.llm.factory import llm_provider
from app.services.slide_generator import generate_presentation
from app.workers.job_tracker import (
    job_mark_completed,
    job_mark_failed,
    job_mark_started,
    job_set_progress,
)
from app.core.logger import logger


_T = TypeVar("_T")
_worker_loop: asyncio.AbstractEventLoop | None = None
_worker_loop_lock = threading.Lock()


def run_coro(coro: Coroutine[Any, Any, _T]) -> _T:
    """Run a coroutine in a stable event loop.

    On macOS we run RQ in SimpleWorker mode (no fork) to avoid ObjC fork crashes.
    Using asyncio.run() per job creates a new loop each time; combined with a global
    async SQLAlchemy engine/pool this can trigger:
    "Future attached to a different loop".
    """

    global _worker_loop

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # Expected: no running loop in sync RQ jobs.
        pass
    else:
        raise RuntimeError("run_coro() called from an async context")

    with _worker_loop_lock:
        if _worker_loop is None or _worker_loop.is_closed():
            _worker_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(_worker_loop)

    return _worker_loop.run_until_complete(coro)


def process_pdf_job(job_db_id: str, paper_id: str) -> dict[str, Any]:
    """RQ job - SYNC wrapper"""

    from app.services.pdf_processor import process_paper

    async def _async_logic() -> dict[str, Any]:
        job_uuid = UUID(job_db_id)
        paper_uuid = UUID(paper_id)

        try:
            await job_mark_started(job_uuid)
            await job_set_progress(job_uuid, 10, status="started")  # load

            async with async_session_maker() as db:
                await job_set_progress(job_uuid, 60, status="progress")  # extract
                result = await process_paper(paper_uuid, db)
                await job_set_progress(job_uuid, 90, status="progress")  # save

            await job_mark_completed(job_uuid, result={"paper_id": str(paper_uuid)})
            return result
        except Exception as e:
            await job_mark_failed(job_uuid, str(e))
            raise

    return run_coro(_async_logic())


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
                        "All judgements set to ‘unclear’ — requires manual review."
                    )
                    rob_auto_generated = True
                else:
                    rob_auto_generated = False

                # Versioning
                from sqlalchemy import select

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
                            a_events=es.a_events,
                            b_non_events=es.b_non_events,
                            c_events=es.c_events,
                            d_non_events=es.d_non_events,
                            or_value=es.or_value,
                            log_or=es.log_or,
                            se_log_or=es.se_log_or,
                            ci_lower_95=es.ci_lower_95,
                            ci_upper_95=es.ci_upper_95,
                            adjusted_or=es.adjusted_or,
                            adjusted_rr=es.adjusted_rr,
                            adjusted_hr=es.adjusted_hr,
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



def summarize_paper_job(job_db_id: str, paper_id: str, custom_instructions: str | None = None) -> dict[str, Any]:
    """RQ job - SYNC wrapper"""

    from app.services.summarizer import generate_summary_async

    async def _async_logic() -> dict[str, Any]:
        job_uuid = UUID(job_db_id)
        paper_uuid = UUID(paper_id)

        try:
            await job_mark_started(job_uuid)
            await job_set_progress(job_uuid, 10, status="started")  # fetch

            async with async_session_maker() as db:
                await job_set_progress(job_uuid, 40, status="progress")  # ensure text
                await job_set_progress(job_uuid, 70, status="progress")  # llm
                result = await generate_summary_async(
                    paper_id=paper_uuid,
                    custom_instructions=custom_instructions,
                    db=db,
                )
                await job_set_progress(job_uuid, 90, status="progress")  # save note

            await job_mark_completed(job_uuid, result={"note_id": result.get("note_id"), "paper_id": str(paper_uuid)})
            return result
        except Exception as e:
            await job_mark_failed(job_uuid, str(e))
            raise

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


def batch_download_papers_job(job_db_id: str, project_id: str, papers: list[dict[str, Any]]) -> dict[str, Any]:
    """Batch download Open-Access PDFs from identifiers. SYNC wrapper."""

    async def _async_logic() -> dict[str, Any]:
        job_uuid = UUID(job_db_id)
        project_uuid = UUID(project_id)

        try:
            await job_mark_started(job_uuid)
            await job_set_progress(
                job_uuid,
                5,
                status="started",
                result_patch={
                    "output": {"downloaded": [], "already_exists": [], "not_available": [], "failed": []},
                    "warnings": [],
                    "errors": [],
                },
            )

            async with async_session_maker() as db:
                from app.models.job import Job
                from app.models.project import Project
                from app.models.user import User
                from app.services.paper_repo import SQLPaperRepository
                from app.services.paper_service import PaperDownloadService
                from app.services.batch_download import batch_download_papers

                job = await db.get(Job, job_uuid)
                if not job:
                    raise ValueError("Job not found")

                proj = await db.get(Project, project_uuid)
                if not proj or proj.user_id != job.user_id:
                    raise ValueError("Project not found")

                user = await db.get(User, job.user_id)
                if not user:
                    raise ValueError("User not found")

                repo = SQLPaperRepository(db)
                downloader = PaperDownloadService()

                import httpx

                async def _progress(done: int, total: int) -> None:
                    pct = 5 + int((done / max(total, 1)) * 90)
                    await job_set_progress(job_uuid, pct, status="progress")

                async with httpx.AsyncClient() as client:
                    res = await batch_download_papers(
                        repo=repo,
                        downloader=downloader,
                        client=client,
                        user=user,
                        project_id=project_uuid,
                        papers=papers,
                        progress_cb=_progress,
                    )

            out = {
                "downloaded": res.downloaded,
                "already_exists": res.already_exists,
                "not_available": res.not_available,
                "failed": res.failed,
            }

            await job_mark_completed(job_uuid, result={"output": out, "warnings": [], "errors": []})
            return out
        except Exception as e:
            await job_mark_failed(job_uuid, str(e))
            return {"output": {}, "warnings": [], "errors": [str(e)]}

    return run_coro(_async_logic())



# private_source_index_job removed by scope change

def books_index_job(job_db_id: str, book_id: str) -> dict[str, Any]:
    """Index a book PDF into BookIndex (chapters + keywords). SYNC wrapper."""

    async def _async_logic() -> dict[str, Any]:
        job_uuid = UUID(job_db_id)
        book_uuid = UUID(book_id)

        try:
            await job_mark_started(job_uuid)
            await job_set_progress(job_uuid, 5, status="started")

            async with async_session_maker() as db:
                from app.models.book_index import BookIndex
                from app.core.storage import storage_manager
                from app.services.books.indexer import index_book_pdf

                b = await db.get(BookIndex, book_uuid)
                if not b:
                    raise ValueError("Book not found")

                abs_path = (storage_manager.base_dir / b.file_path).resolve()
                abs_path.relative_to(storage_manager.base_dir)
                if not abs_path.exists():
                    raise FileNotFoundError("Book PDF not found")

                await job_set_progress(job_uuid, 20, status="progress")
                idx = index_book_pdf(abs_path)

                b.title = idx.get("title")
                b.total_pages = idx.get("total_pages")
                b.chapters = idx.get("chapters")
                b.indexed_at = datetime.utcnow()
                await db.commit()

            await job_mark_completed(job_uuid, result={"output": {"book_id": book_id}, "warnings": [], "errors": []})
            return {"book_id": book_id}
        except Exception as e:
            await job_mark_failed(job_uuid, str(e))
            return {"output": {}, "warnings": [], "errors": [str(e)]}

    return run_coro(_async_logic())



def clinical_query_job(job_db_id: str, sheet_id: str) -> dict[str, Any]:
    """Generate a ClinicalSheet (UpToDate-like query) using allowed sources. SYNC wrapper."""

    async def _async_logic() -> dict[str, Any]:
        job_uuid = UUID(job_db_id)
        sheet_uuid = UUID(sheet_id)

        try:
            await job_mark_started(job_uuid)
            await job_set_progress(job_uuid, 5, status="started")

            async with async_session_maker() as db:
                from app.models.clinical import ClinicalSheet

                sheet = await db.get(ClinicalSheet, sheet_uuid)
                if not sheet:
                    raise ValueError("Sheet not found")

                await job_set_progress(job_uuid, 10, status="progress")

                from app.services.clinical.generator import generate_clinical_sheet

                out = await generate_clinical_sheet(db=db, sheet=sheet, progress_cb=lambda p: job_set_progress(job_uuid, p, status="progress"))

                # persist
                sheet.content_markdown = out["content_markdown"]
                sheet.content_json = out.get("content_json")
                sheet.format_version = out.get("format_version")
                sheet.references_json = out.get("references_json")
                sheet.sources_used = out.get("sources_used")
                sheet.llm_model = out.get("llm_model")
                sheet.llm_usage = out.get("llm_usage")
                sheet.updated_at = datetime.utcnow()
                # keep input_params, but set status completed
                sheet.input_params = {**(sheet.input_params or {}), "status": "completed"}

                # auto-generate exports
                await job_set_progress(job_uuid, 95, status="progress")
                try:
                    from app.services.clinical.exporters import export_docx, export_pdf

                    docx_path = export_docx(
                        user_id=sheet.user_id,
                        sheet_id=sheet.id,
                        version=sheet.version,
                        topic=sheet.topic,
                        content_markdown=sheet.content_markdown,
                    )
                    pdf_path = export_pdf(
                        user_id=sheet.user_id,
                        sheet_id=sheet.id,
                        version=sheet.version,
                        topic=sheet.topic,
                        content_markdown=sheet.content_markdown,
                    )

                    su = dict(sheet.sources_used or {})
                    su["exports"] = {"docx": docx_path, "pdf": pdf_path}
                    sheet.sources_used = su
                except Exception as ex:
                    # don't fail the clinical sheet if export fails
                    su = dict(sheet.sources_used or {})
                    su["exports_error"] = str(ex)
                    sheet.sources_used = su

                await db.commit()

            await job_mark_completed(job_uuid, result={"output": {"sheet_id": sheet_id}, "warnings": out.get("warnings", []), "errors": []})
            return {"sheet_id": sheet_id}
        except Exception as e:
            # persist best-effort error on sheet
            try:
                async with async_session_maker() as db2:
                    from app.models.clinical import ClinicalSheet

                    s2 = await db2.get(ClinicalSheet, sheet_uuid)
                    if s2:
                        s2.input_params = {**(s2.input_params or {}), "status": "failed", "error": str(e)}
                        s2.updated_at = datetime.utcnow()
                        await db2.commit()
            except Exception as _sheet_err:
                logger.warning(f"[clinical_query_job] failed to persist error state on sheet={sheet_id}: {_sheet_err!r}")

            await job_mark_failed(job_uuid, str(e))
            raise

    return run_coro(_async_logic())



def clinical_generate_sheet_job(job_db_id: str, sheet_id: str) -> dict[str, Any]:
    """Back-compat alias for the new /clinical/query behavior."""

    return clinical_query_job(job_db_id, sheet_id)



def generate_presentation_job(
    job_db_id: str,
    project_id: str,
    topic: str,
    duration: int,
    audience: str,
    paper_ids: list[str],
    num_slides: int = 35,
) -> dict[str, Any]:
    """RQ job - SYNC wrapper"""

    async def _async_logic() -> dict[str, Any]:
        job_uuid = UUID(job_db_id)
        try:
            await job_mark_started(job_uuid)
            await job_set_progress(job_uuid, 5, status="started")

            async with async_session_maker() as db:
                # 1) Obtener papers + resumen más reciente si existe
                papers: list[dict[str, Any]] = []
                paper_uuids = [UUID(pid) for pid in paper_ids]

                # Batch fetch papers
                q_papers = await db.execute(select(Paper).where(Paper.id.in_(paper_uuids)))
                db_papers = {p.id: p for p in q_papers.scalars().all()}

                # Batch fetch notes
                q_notes = await db.execute(
                    select(Note)
                    .where(Note.paper_id.in_(paper_uuids), Note.note_type == "summary")
                    .order_by(Note.paper_id, Note.created_at.desc())
                )
                all_notes = q_notes.scalars().all()

                # Get latest note per paper
                latest_notes = {}
                for note in all_notes:
                    if note.paper_id not in latest_notes:
                        latest_notes[note.paper_id] = note

                for pid in paper_uuids:
                    paper = db_papers.get(pid)
                    if not paper:
                        continue

                    note = latest_notes.get(pid)

                    papers.append(
                        {
                            "id": str(paper.id),
                            "title": paper.title,
                            "authors": paper.authors,
                            "doi": paper.doi,
                            "pmid": paper.pmid,
                            "pmcid": paper.pmcid,
                            "summary": note.content if note else None,
                        }
                    )

                await job_set_progress(job_uuid, 20, status="progress")

                # 2) Outline con LLM
                from app.services.llm.schemas import GenerateOutlineInput

                llm = llm_provider()
                outline_result = await llm.generate_slide_outline(
                    GenerateOutlineInput(
                        topic=topic,
                        duration_minutes=duration,
                        audience=audience,
                        papers=papers,
                        num_slides=int(num_slides),
                    )
                )

                await job_set_progress(job_uuid, 55, status="progress")

                # 3) Referencias
                references = await llm.format_references_vancouver(papers)

                await job_set_progress(job_uuid, 70, status="progress")

                # 4) Generar PPTX
                pptx_result = await generate_presentation(
                    outline=outline_result["outline"],
                    references=references,
                    project_id=UUID(project_id),
                )

                await job_set_progress(job_uuid, 90, status="progress")

                # 5) Guardar en DB
                presentation = Presentation(
                    project_id=UUID(project_id),
                    title=topic,
                    topic=topic,
                    duration_minutes=duration,
                    audience=audience,
                    filename=pptx_result["filename"],
                    file_path=pptx_result["file_path"],
                    outline=outline_result["outline"],
                    references_used=references,
                    llm_model=outline_result.get("model"),
                    llm_usage=outline_result.get("usage"),
                )
                db.add(presentation)
                await db.flush()

                # M2M: avoid async lazy-loading on relationship collections (MissingGreenlet)
                from app.models.presentation import presentation_papers

                for pid in paper_ids:
                    paper_uuid = UUID(pid)
                    paper_obj = await db.get(Paper, paper_uuid)
                    if not paper_obj:
                        continue
                    await db.execute(
                        presentation_papers.insert().values(presentation_id=presentation.id, paper_id=paper_uuid)
                    )

                await db.commit()
                await db.refresh(presentation)

                result = {
                    "presentation_id": str(presentation.id),
                    "filename": presentation.filename,
                    "slide_count": pptx_result.get("slide_count"),
                }

                await job_mark_completed(job_uuid, result={"presentation_id": result["presentation_id"]})
                return result
        except Exception as e:
            await job_mark_failed(job_uuid, str(e))
            raise

    return run_coro(_async_logic())



def export_project_zip_job(job_db_id: str, project_id: str) -> dict[str, Any]:
    """Export a project as a ZIP (papers + notes + presentations + meta exports + clinical sheets). SYNC wrapper."""

    async def _async_logic() -> dict[str, Any]:
        job_uuid = UUID(job_db_id)
        project_uuid = UUID(project_id)

        try:
            await job_mark_started(job_uuid)
            await job_set_progress(job_uuid, 5, status="started")

            async with async_session_maker() as db:
                from sqlalchemy import select

                from app.core.storage import storage_manager
                from app.models.clinical import ClinicalSheet
                from app.models.meta_export import MetaExport
                from app.models.note import Note
                from app.models.paper import Paper
                from app.models.presentation import Presentation
                from app.models.project import Project

                proj = await db.get(Project, project_uuid)
                if not proj:
                    raise ValueError("Project not found")

                qp = await db.execute(select(Paper).where(Paper.project_id == project_uuid).order_by(Paper.created_at.desc()))
                papers = qp.scalars().all()

                qn = await db.execute(select(Note).where(Note.project_id == project_uuid).order_by(Note.created_at.desc()))
                notes = qn.scalars().all()

                qpres = await db.execute(
                    select(Presentation).where(Presentation.project_id == project_uuid).order_by(Presentation.created_at.desc())
                )
                presentations = qpres.scalars().all()

                qexp = await db.execute(select(MetaExport).where(MetaExport.project_id == project_uuid).order_by(MetaExport.created_at.desc()))
                meta_exports = qexp.scalars().all()

                qcs = await db.execute(
                    select(ClinicalSheet)
                    .where(ClinicalSheet.project_id == project_uuid)
                    .where(ClinicalSheet.is_current == True)  # noqa
                    .order_by(ClinicalSheet.created_at.desc())
                )
                clinical_sheets = qcs.scalars().all()

                await job_set_progress(job_uuid, 20, status="progress")

                import json
                import re
                import zipfile
                from datetime import datetime
                from pathlib import Path

                def _safe_name(s: str) -> str:
                    s = re.sub(r"[^a-zA-Z0-9 _\-.]", "", s or "").strip()
                    s = s.replace("..", ".")
                    return s or "item"

                ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                filename = f"project_export_{project_uuid}_{ts}.zip"

                # Keep exports under storage/searches/<project_id>/exports
                out_rel = str(Path("searches") / str(project_uuid) / "exports" / filename)
                out_abs = (storage_manager.base_dir / out_rel).resolve()
                out_abs.relative_to(storage_manager.base_dir)
                out_abs.parent.mkdir(parents=True, exist_ok=True)

                root = "project_export"

                manifest = {
                    "generated_at": datetime.utcnow().isoformat(),
                    "project": {
                        "id": str(proj.id),
                        "title": proj.title,
                        "description": proj.description,
                        "clinical_area": proj.clinical_area,
                        "archived": proj.archived,
                        "created_at": proj.created_at.isoformat() if getattr(proj, "created_at", None) else None,
                        "updated_at": proj.updated_at.isoformat() if getattr(proj, "updated_at", None) else None,
                    },
                    "counts": {
                        "papers": len(papers),
                        "notes": len(notes),
                        "presentations": len(presentations),
                        "meta_exports": len(meta_exports),
                        "clinical_sheets": len(clinical_sheets),
                    },
                    "items": {
                        "papers": [
                            {
                                "id": str(p.id),
                                "title": p.title,
                                "doi": p.doi,
                                "pmid": p.pmid,
                                "pmcid": p.pmcid,
                                "filename": p.filename,
                                "file_path": p.file_path,
                                "file_size_kb": p.file_size_kb,
                                "content_hash": p.content_hash,
                                "is_processed": p.is_processed,
                                "created_at": p.created_at.isoformat() if p.created_at else None,
                            }
                            for p in papers
                        ],
                        "notes": [
                            {
                                "id": str(n.id),
                                "paper_id": str(n.paper_id) if n.paper_id else None,
                                "title": n.title,
                                "note_type": n.note_type,
                                "created_at": n.created_at.isoformat() if n.created_at else None,
                                "updated_at": n.updated_at.isoformat() if n.updated_at else None,
                            }
                            for n in notes
                        ],
                        "presentations": [
                            {
                                "id": str(pr.id),
                                "title": pr.title,
                                "topic": pr.topic,
                                "audience": pr.audience,
                                "duration_minutes": pr.duration_minutes,
                                "filename": pr.filename,
                                "file_path": pr.file_path,
                                "created_at": pr.created_at.isoformat() if pr.created_at else None,
                            }
                            for pr in presentations
                        ],
                        "meta_exports": [
                            {
                                "id": str(ex.id),
                                "batch_id": str(ex.batch_id) if ex.batch_id else None,
                                "filename": ex.filename,
                                "file_path": ex.file_path,
                                "created_at": ex.created_at.isoformat() if ex.created_at else None,
                            }
                            for ex in meta_exports
                        ],
                        "clinical_sheets": [
                            {
                                "id": str(cs.id),
                                "topic": cs.topic,
                                "version": cs.version,
                                "created_at": cs.created_at.isoformat() if cs.created_at else None,
                                "updated_at": cs.updated_at.isoformat() if cs.updated_at else None,
                                "exports": (cs.sources_used or {}).get("exports") if isinstance(cs.sources_used, dict) else None,
                            }
                            for cs in clinical_sheets
                        ],
                    },
                }

                with zipfile.ZipFile(str(out_abs), "w", compression=zipfile.ZIP_DEFLATED) as z:
                    z.writestr(f"{root}/manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))

                    # Notes
                    for n in notes:
                        safe_title = _safe_name(n.title)[:80]
                        z.writestr(f"{root}/notes/{n.id}_{safe_title}.md", n.content or "")

                    # Papers
                    for i, p in enumerate(papers, 1):
                        rel = p.file_path
                        if not rel:
                            continue
                        abs_path = (storage_manager.base_dir / rel).resolve()
                        try:
                            abs_path.relative_to(storage_manager.base_dir)
                        except ValueError:
                            continue
                        if not abs_path.exists():
                            continue
                        arc = f"{root}/papers/{p.id}_{_safe_name(p.filename)}"
                        z.write(str(abs_path), arcname=arc)
                        if i % 5 == 0:
                            await job_set_progress(job_uuid, 20 + int((i / max(len(papers), 1)) * 35), status="progress")

                    # Presentations
                    for pr in presentations:
                        if not pr.file_path:
                            continue
                        abs_path = (storage_manager.base_dir / pr.file_path).resolve()
                        try:
                            abs_path.relative_to(storage_manager.base_dir)
                        except ValueError:
                            continue
                        if not abs_path.exists():
                            continue
                        arc = f"{root}/presentations/{pr.id}_{_safe_name(pr.filename or 'presentation.pptx')}"
                        z.write(str(abs_path), arcname=arc)

                    # Meta exports
                    for ex in meta_exports:
                        if not ex.file_path:
                            continue
                        abs_path = (storage_manager.base_dir / ex.file_path).resolve()
                        try:
                            abs_path.relative_to(storage_manager.base_dir)
                        except ValueError:
                            continue
                        if not abs_path.exists():
                            continue
                        arc = f"{root}/meta_exports/{ex.id}_{_safe_name(ex.filename)}"
                        z.write(str(abs_path), arcname=arc)

                    # Clinical sheets (markdown + docx if exists)
                    for cs in clinical_sheets:
                        safe_topic = _safe_name(cs.topic)[:80]
                        base = f"{cs.id}_v{int(cs.version)}_{safe_topic}".strip("_")
                        z.writestr(f"{root}/clinical_sheets/{base}.md", cs.content_markdown or "")

                        exports = (cs.sources_used or {}).get("exports") if isinstance(cs.sources_used, dict) else None
                        docx_rel = (exports or {}).get("docx") if isinstance(exports, dict) else None
                        if docx_rel:
                            abs_path = (storage_manager.base_dir / str(docx_rel)).resolve()
                            try:
                                abs_path.relative_to(storage_manager.base_dir)
                            except ValueError:
                                abs_path = None
                            if abs_path and abs_path.exists():
                                z.write(str(abs_path), arcname=f"{root}/clinical_sheets/{base}.docx")

                size_kb = out_abs.stat().st_size // 1024 if out_abs.exists() else None

            out = {"zip_file_path": out_rel, "filename": filename, "size_kb": size_kb}
            await job_mark_completed(job_uuid, result={"output": out, "warnings": [], "errors": []})
            return out
        except Exception as e:
            await job_mark_failed(job_uuid, str(e))
            return {"output": {}, "warnings": [], "errors": [str(e)]}

    return run_coro(_async_logic())
