"""PDF processing and paper summarization worker jobs."""
from __future__ import annotations

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
