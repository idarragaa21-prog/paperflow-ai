from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.core.logger import logger
from app.core.storage import storage_manager
from app.database import async_session_maker
from app.services.books.indexer import index_book_pdf
from app.services.paper_service import sha256_hex
from app.workers.job_tracker import job_mark_completed, job_mark_failed, job_mark_started, job_set_progress
from app.workers.tasks import run_coro


def _safe_name(s: str) -> str:
    return storage_manager._sanitize_filename(s or "book.pdf")


def books_scan_folder_job(job_db_id: str) -> dict[str, Any]:
    """Scan storage/BOOKS folder for PDFs and index them as BookIndex records. SYNC wrapper."""

    async def _async_logic() -> dict[str, Any]:
        job_uuid = UUID(job_db_id)

        try:
            await job_mark_started(job_uuid)
            await job_set_progress(job_uuid, 5, status="started")

            warnings: list[str] = []
            errors: list[str] = []

            import_dir = (storage_manager.base_dir / "BOOKS").resolve()
            try:
                import_dir.relative_to(storage_manager.base_dir)
            except ValueError:
                raise ValueError("Invalid BOOKS import directory")

            if not import_dir.exists():
                import_dir.mkdir(parents=True, exist_ok=True)
                warnings.append("BOOKS folder did not exist; created it. Add PDFs and re-run scan.")

            pdf_files = sorted([p for p in import_dir.rglob("*.pdf") if p.is_file()])
            max_files = 25
            pdf_files = pdf_files[:max_files]

            await job_set_progress(job_uuid, 10, status="progress", result_patch={"output": {"found": len(pdf_files)}})

            imported = 0
            skipped = 0
            indexed = 0

            async with async_session_maker() as db:
                from app.models.book_index import BookIndex
                from app.models.job import Job

                job = await db.get(Job, job_uuid)
                if not job:
                    raise ValueError("Job not found")

                user_id = job.user_id

                # Existing filenames for user
                q = await db.execute(select(BookIndex.filename).where(BookIndex.user_id == user_id))
                existing_names = set([str(x) for x in q.scalars().all()])

                for i, src_path in enumerate(pdf_files, 1):
                    pct = 10 + int((i / max(len(pdf_files), 1)) * 80)
                    await job_set_progress(job_uuid, pct, status="progress")

                    try:
                        data = src_path.read_bytes()
                        if not storage_manager.validate_pdf(data):
                            skipped += 1
                            continue

                        # Copy into managed storage/books/<user_id>/
                        base = _safe_name(src_path.name)
                        name = base
                        # Avoid overwriting / collisions
                        if name in existing_names:
                            stem = Path(base).stem
                            ext = Path(base).suffix or ".pdf"
                            name = f"{stem}_{sha256_hex(data)[:8]}{ext}"

                        rel_path = Path("books") / str(user_id) / name
                        abs_path = (storage_manager.base_dir / rel_path).resolve()
                        abs_path.parent.mkdir(parents=True, exist_ok=True)
                        storage_manager._sanitize_path(abs_path).write_bytes(data)

                        b = BookIndex(
                            user_id=user_id,
                            filename=name,
                            file_path=str(rel_path),
                            title=None,
                            total_pages=None,
                            chapters=None,
                            indexed_at=None,
                            created_at=datetime.now(timezone.utc),
                        )
                        db.add(b)
                        await db.flush()

                        imported += 1
                        existing_names.add(name)

                        # Index immediately (still in this job)
                        try:
                            idx = index_book_pdf(abs_path)
                            b.title = idx.get("title")
                            b.total_pages = idx.get("total_pages")
                            b.chapters = idx.get("chapters")
                            b.indexed_at = datetime.now(timezone.utc)
                            indexed += 1
                        except Exception as e:
                            errors.append(f"Index failed for {src_path.name}: {e}")

                        await db.commit()
                    except Exception as e:
                        logger.warning(f"BOOKS scan failed for {src_path}: {e}")
                        errors.append(f"Scan failed for {src_path.name}: {e}")

            out = {
                "import_dir": str(import_dir.relative_to(storage_manager.base_dir)),
                "found": len(pdf_files),
                "imported": imported,
                "indexed": indexed,
                "skipped": skipped,
            }

            await job_mark_completed(job_uuid, result={"output": out, "warnings": warnings, "errors": errors})
            return out
        except Exception as e:
            await job_mark_failed(job_uuid, str(e))
            return {"output": {}, "warnings": [], "errors": [str(e)]}

    return run_coro(_async_logic())
