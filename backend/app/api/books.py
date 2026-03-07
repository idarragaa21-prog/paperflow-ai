# (no future annotations - avoids forward-ref issues)

from datetime import datetime
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.storage import storage_manager
from app.middleware.rate_limit import limiter
from app.models.book_index import BookIndex
from app.models.job import Job
from app.models.user import User
from app.services.jobs import get_job_queue

router = APIRouter(prefix="/books", tags=["books"])


@router.post("/index")
@limiter.limit("3/minute")
async def index_book(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    content = await file.read()
    if not storage_manager.validate_pdf(content):
        raise HTTPException(status_code=400, detail="Archivo no es un PDF válido")

    # Save to storage (books/<user_id>/<filename>)
    safe_name = storage_manager._sanitize_filename(file.filename or "book.pdf")
    rel_path = Path("books") / str(user.id) / safe_name
    abs_path = (storage_manager.base_dir / rel_path).resolve()
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    storage_manager._sanitize_path(abs_path).write_bytes(content)

    book = BookIndex(
        user_id=user.id,
        filename=safe_name,
        file_path=str(rel_path),
        title=None,
        total_pages=None,
        chapters=None,
        indexed_at=None,
        created_at=datetime.utcnow(),
    )
    db.add(book)
    await db.commit()
    await db.refresh(book)

    job_record = Job(
        user_id=user.id,
        job_type="books_index",
        status="queued",
        input_params={"book_id": str(book.id)},
        result={},
        progress_percent=0,
    )
    db.add(job_record)
    await db.commit()
    await db.refresh(job_record)

    try:
        from app.workers.tasks import books_index_job

        q = get_job_queue()
        rq_job = q.enqueue(books_index_job, args=(str(job_record.id), str(book.id)), job_timeout="60m")
    except Exception:
        job_record.status = "failed"
        job_record.error_message = "Job queue unavailable. Redis is required."
        await db.commit()
        raise HTTPException(status_code=503, detail="Job queue unavailable. Redis is required.")

    job_record.result = {"rq_job_id": rq_job.id, "book_id": str(book.id)}
    await db.commit()

    return {"job_id": str(job_record.id), "book_id": str(book.id)}


@router.post("/scan-folder")
@limiter.limit("3/minute")
async def scan_books_folder(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Scan STORAGE_BASE_PATH/BOOKS for PDFs and index them (background job)."""

    job_record = Job(
        user_id=user.id,
        job_type="books_scan_folder",
        status="queued",
        input_params={},
        result={},
        progress_percent=0,
    )
    db.add(job_record)
    await db.commit()
    await db.refresh(job_record)

    try:
        from app.workers.books_scan_folder_job import books_scan_folder_job

        q = get_job_queue()
        rq_job = q.enqueue(books_scan_folder_job, args=(str(job_record.id),), job_timeout="60m")
    except Exception:
        job_record.status = "failed"
        job_record.error_message = "Job queue unavailable. Redis is required."
        await db.commit()
        raise HTTPException(status_code=503, detail="Job queue unavailable. Redis is required.")

    job_record.result = {"rq_job_id": rq_job.id}
    await db.commit()

    return {"job_id": str(job_record.id)}


@router.get("")
async def list_books(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = await db.execute(select(BookIndex).where(BookIndex.user_id == user.id).order_by(BookIndex.created_at.desc()))
    rows = q.scalars().all()
    return [
        {
            "id": str(b.id),
            "filename": b.filename,
            "file_path": b.file_path,
            "title": b.title,
            "total_pages": b.total_pages,
            "chapters_count": len(b.chapters or []),
            "indexed_at": b.indexed_at.isoformat() if b.indexed_at else None,
            "created_at": b.created_at.isoformat() if b.created_at else None,
        }
        for b in rows
    ]


@router.post("/{book_id}/reindex")
@limiter.limit("5/minute")
async def reindex_book(
    request: Request,
    book_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    b = await db.get(BookIndex, book_id)
    if not b or b.user_id != user.id:
        raise HTTPException(status_code=404, detail="Book not found")

    job_record = Job(
        user_id=user.id,
        job_type="books_index",
        status="queued",
        input_params={"book_id": str(b.id)},
        result={},
        progress_percent=0,
    )
    db.add(job_record)
    await db.commit()
    await db.refresh(job_record)

    try:
        from app.workers.tasks import books_index_job

        q = get_job_queue()
        rq_job = q.enqueue(books_index_job, args=(str(job_record.id), str(b.id)), job_timeout="60m")
    except Exception:
        job_record.status = "failed"
        job_record.error_message = "Job queue unavailable. Redis is required."
        await db.commit()
        raise HTTPException(status_code=503, detail="Job queue unavailable. Redis is required.")

    job_record.result = {"rq_job_id": rq_job.id, "book_id": str(b.id)}
    await db.commit()
    return {"job_id": str(job_record.id), "book_id": str(b.id)}


@router.delete("/{book_id}")
@limiter.limit("10/minute")
async def delete_book(
    request: Request,
    book_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    b = await db.get(BookIndex, book_id)
    if not b or b.user_id != user.id:
        raise HTTPException(status_code=404, detail="Book not found")

    # delete file
    try:
        storage_manager.delete_file(b.file_path)
    except Exception:
        pass

    await db.delete(b)
    await db.commit()
    return {"ok": True}
