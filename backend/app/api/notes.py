from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.middleware.rate_limit import limiter
from app.models.job import Job
from app.models.note import Note
from app.models.paper import Paper
from app.models.project import Project
from app.models.user import User
from app.schemas.notes import NoteCreate, NotePatch, NoteResponse, SummarizeNoteRequest
from app.services.jobs import get_job_queue

router = APIRouter(prefix="/notes", tags=["notes"])


@router.post("/summarize")
@limiter.limit("5/minute")
async def summarize_paper(
    request: Request,
    payload: SummarizeNoteRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    paper = await db.get(Paper, payload.paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    project = await db.get(Project, paper.project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Paper not found")

    job_record = Job(
        user_id=user.id,
        job_type="summarize_paper",
        status="queued",
        input_params={"paper_id": str(paper.id), "custom_instructions": payload.custom_instructions},
        result={},
        progress_percent=0,
    )
    db.add(job_record)
    await db.commit()
    await db.refresh(job_record)

    # enqueue
    try:
        from app.workers.tasks import summarize_paper_job

        q = get_job_queue()
        rq_job = q.enqueue(
            summarize_paper_job,
            args=(str(job_record.id), str(paper.id), payload.custom_instructions),
            job_timeout="10m",
        )
    except Exception:
        job_record.status = "failed"
        job_record.error_message = "No se pudo encolar job (Redis no disponible?)"
        await db.commit()
        raise HTTPException(status_code=503, detail="No se pudo encolar job")

    job_record.result = {"rq_job_id": rq_job.id}
    await db.commit()

    return {"job_id": str(job_record.id)}


@router.get("/{note_id}", response_model=NoteResponse)
async def get_note(
    note_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    note = await db.get(Note, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    project = await db.get(Project, note.project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Note not found")

    return NoteResponse(
        id=note.id,
        project_id=note.project_id,
        paper_id=note.paper_id,
        title=note.title,
        content=note.content,
        note_type=note.note_type,
        llm_model=note.llm_model,
        llm_usage=note.llm_usage,
    )


@router.get("/projects/{project_id}")
async def list_notes(
    project_id: UUID,
    paper_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = await db.get(Project, project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    stmt = select(Note).where(Note.project_id == project_id)
    if paper_id:
        stmt = stmt.where(Note.paper_id == paper_id)
    stmt = stmt.order_by(Note.created_at.desc())

    q = await db.execute(stmt)
    items = q.scalars().all()
    return [
        {
            "id": str(n.id),
            "title": n.title,
            "note_type": n.note_type,
            "paper_id": str(n.paper_id) if n.paper_id else None,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in items
    ]


@router.post("", response_model=NoteResponse)
async def create_note(
    payload: NoteCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = await db.get(Project, payload.project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    note = Note(
        project_id=payload.project_id,
        paper_id=payload.paper_id,
        title=payload.title,
        content=payload.content,
        note_type=payload.note_type or "general",
        updated_at=datetime.now(timezone.utc),
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return NoteResponse(id=note.id, project_id=note.project_id, paper_id=note.paper_id,
                        title=note.title, content=note.content, note_type=note.note_type,
                        llm_model=note.llm_model, llm_usage=note.llm_usage)


@router.patch("/{note_id}", response_model=NoteResponse)
async def patch_note(
    note_id: UUID,
    payload: NotePatch,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    note = await db.get(Note, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    project = await db.get(Project, note.project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Note not found")

    if payload.title is not None:
        note.title = payload.title
    if payload.content is not None:
        note.content = payload.content
    if payload.note_type is not None:
        note.note_type = payload.note_type
    note.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(note)
    return NoteResponse(id=note.id, project_id=note.project_id, paper_id=note.paper_id,
                        title=note.title, content=note.content, note_type=note.note_type,
                        llm_model=note.llm_model, llm_usage=note.llm_usage)


@router.delete("/{note_id}", status_code=204)
async def delete_note(
    note_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    note = await db.get(Note, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    project = await db.get(Project, note.project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Note not found")
    await db.delete(note)
    await db.commit()
