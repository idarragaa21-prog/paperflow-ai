"""Clinical sheet generation worker jobs."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from app.database import async_session_maker
from app.workers._run_coro import run_coro
from app.workers.job_tracker import (
    job_mark_completed,
    job_mark_failed,
    job_mark_started,
    job_set_progress,
)
from app.core.logger import logger


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
