"""Presentation generation worker job."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.database import async_session_maker
from app.models.note import Note
from app.models.paper import Paper
from app.models.presentation import Presentation
from app.services.llm.factory import llm_provider
from app.services.slide_generator import generate_presentation
from app.workers._run_coro import run_coro
from app.workers.job_tracker import (
    job_mark_completed,
    job_mark_failed,
    job_mark_started,
    job_set_progress,
)


@dataclass
class GeneratePresentationParams:
    job_db_id: str
    project_id: str
    topic: str
    duration: int
    audience: str
    paper_ids: list[str]
    num_slides: int = 35


def generate_presentation_job(params: GeneratePresentationParams) -> dict[str, Any]:
    """RQ job - SYNC wrapper"""

    async def _async_logic() -> dict[str, Any]:
        job_uuid = UUID(params.job_db_id)
        try:
            await job_mark_started(job_uuid)
            await job_set_progress(job_uuid, 5, status="started")

            async with async_session_maker() as db:
                # 1) Obtener papers + resumen más reciente si existe
                paper_uuids = [UUID(pid) for pid in params.paper_ids]
                q_papers = await db.execute(select(Paper).where(Paper.id.in_(paper_uuids)))
                papers_map = {p.id: p for p in q_papers.scalars().all()}

                # Fetch all summary notes for these papers to avoid N+1
                q_notes = await db.execute(
                    select(Note)
                    .where(Note.paper_id.in_(list(papers_map.keys())), Note.note_type == "summary")
                    .order_by(Note.paper_id, Note.created_at.desc())
                )
                notes_by_paper: dict[UUID, Note] = {}
                for n in q_notes.scalars().all():
                    if n.paper_id not in notes_by_paper:
                        notes_by_paper[n.paper_id] = n

                papers: list[dict[str, Any]] = []
                for pid in params.paper_ids:
                    p_uuid = UUID(pid)
                    paper = papers_map.get(p_uuid)
                    if not paper:
                        continue

                    note = notes_by_paper.get(p_uuid)
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
                        topic=params.topic,
                        duration_minutes=params.duration,
                        audience=params.audience,
                        papers=papers,
                        num_slides=int(params.num_slides),
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
                    project_id=UUID(params.project_id),
                )

                await job_set_progress(job_uuid, 90, status="progress")

                # 5) Guardar en DB
                presentation = Presentation(
                    project_id=UUID(params.project_id),
                    title=params.topic,
                    topic=params.topic,
                    duration_minutes=params.duration,
                    audience=params.audience,
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

                insert_vals = [
                    {"presentation_id": presentation.id, "paper_id": UUID(pid)}
                    for pid in params.paper_ids
                    if UUID(pid) in papers_map
                ]
                if insert_vals:
                    await db.execute(presentation_papers.insert().values(insert_vals))

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
