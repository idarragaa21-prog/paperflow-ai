"""Books indexing worker job."""
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
