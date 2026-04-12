"""Project export worker jobs."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import async_session_maker
from app.workers._run_coro import run_coro
from app.workers.job_tracker import (
    job_mark_completed,
    job_mark_failed,
    job_mark_started,
    job_set_progress,
)


def export_project_zip_job(job_db_id: str, project_id: str) -> dict[str, Any]:
    """Export a project as a ZIP (papers + notes + matrix/meta/writing/consult artifacts)."""

    async def _async_logic() -> dict[str, Any]:
        job_uuid = UUID(job_db_id)
        project_uuid = UUID(project_id)

        try:
            await job_mark_started(job_uuid)
            await job_set_progress(job_uuid, 5, status="started")

            async with async_session_maker() as db:
                import json
                import re
                import zipfile
                from datetime import datetime
                from pathlib import Path

                from app.core.storage import storage_manager
                from app.models.clinical import ClinicalConsult
                from app.models.matrix import MatrixVersion
                from app.models.meta_export import MetaExport
                from app.models.meta_run import MetaRun
                from app.models.note import Note
                from app.models.paper import Paper
                from app.models.project import Project
                from app.models.reference_item import ReferenceItem
                from app.models.writing import WritingDocument

                proj = await db.get(Project, project_uuid)
                if not proj:
                    raise ValueError("Project not found")

                qp = await db.execute(select(Paper).where(Paper.project_id == project_uuid).order_by(Paper.created_at.desc()))
                papers = qp.scalars().all()

                qn = await db.execute(select(Note).where(Note.project_id == project_uuid).order_by(Note.created_at.desc()))
                notes = qn.scalars().all()

                qmx = await db.execute(
                    select(MatrixVersion).where(MatrixVersion.project_id == project_uuid).order_by(MatrixVersion.version_number.desc())
                )
                matrix_versions = qmx.scalars().all()

                qexp = await db.execute(select(MetaExport).where(MetaExport.project_id == project_uuid).order_by(MetaExport.created_at.desc()))
                meta_exports = qexp.scalars().all()

                qmr = await db.execute(
                    select(MetaRun)
                    .where(MetaRun.project_id == project_uuid)
                    .order_by(MetaRun.created_at.desc())
                    .options(selectinload(MetaRun.artifacts))
                )
                meta_runs = qmr.scalars().all()

                qwd = await db.execute(
                    select(WritingDocument)
                    .where(WritingDocument.project_id == project_uuid)
                    .order_by(WritingDocument.created_at.desc())
                    .options(selectinload(WritingDocument.sections))
                )
                writing_documents = qwd.scalars().all()

                qcc = await db.execute(
                    select(ClinicalConsult)
                    .where(ClinicalConsult.project_id == project_uuid)
                    .order_by(ClinicalConsult.created_at.desc())
                )
                clinical_consults = qcc.scalars().all()

                qrefs = await db.execute(
                    select(ReferenceItem)
                    .where(ReferenceItem.project_id == project_uuid)
                    .order_by(ReferenceItem.created_at.desc())
                )
                references = qrefs.scalars().all()

                await job_set_progress(job_uuid, 20, status="progress")

                def _safe_name(value: str) -> str:
                    safe = re.sub(r"[^a-zA-Z0-9 _\-.]", "", value or "").strip()
                    safe = safe.replace("..", ".")
                    return safe or "item"

                ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                filename = f"project_export_{project_uuid}_{ts}.zip"

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
                        "matrix_versions": len(matrix_versions),
                        "meta_runs": len(meta_runs),
                        "writing_documents": len(writing_documents),
                        "clinical_consults": len(clinical_consults),
                        "references": len(references),
                        "meta_exports": len(meta_exports),
                    },
                }

                with zipfile.ZipFile(str(out_abs), "w", compression=zipfile.ZIP_DEFLATED) as archive:
                    archive.writestr(f"{root}/manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))

                    for note in notes:
                        safe_title = _safe_name(note.title)[:80]
                        archive.writestr(f"{root}/notes/{note.id}_{safe_title}.md", note.content or "")

                    for i, paper in enumerate(papers, 1):
                        rel = paper.file_path
                        if not rel:
                            continue
                        abs_path = (storage_manager.base_dir / rel).resolve()
                        try:
                            abs_path.relative_to(storage_manager.base_dir)
                        except ValueError:
                            continue
                        if not abs_path.exists():
                            continue
                        arc = f"{root}/papers/{paper.id}_{_safe_name(paper.filename)}"
                        archive.write(str(abs_path), arcname=arc)
                        if i % 5 == 0:
                            await job_set_progress(job_uuid, 20 + int((i / max(len(papers), 1)) * 35), status="progress")

                    for export_item in meta_exports:
                        if not export_item.file_path:
                            continue
                        abs_path = (storage_manager.base_dir / export_item.file_path).resolve()
                        try:
                            abs_path.relative_to(storage_manager.base_dir)
                        except ValueError:
                            continue
                        if not abs_path.exists():
                            continue
                        archive.write(str(abs_path), arcname=f"{root}/meta_exports/{export_item.id}_{_safe_name(export_item.filename)}")

                    for run in meta_runs:
                        for artifact in run.artifacts or []:
                            if not artifact.file_path:
                                continue
                            abs_path = (storage_manager.base_dir / artifact.file_path).resolve()
                            try:
                                abs_path.relative_to(storage_manager.base_dir)
                            except ValueError:
                                continue
                            if not abs_path.exists():
                                continue
                            arc = f"{root}/meta_runs/{run.id}/{artifact.artifact_type}_{_safe_name(artifact.filename)}"
                            archive.write(str(abs_path), arcname=arc)

                    for document in writing_documents:
                        safe_title = _safe_name(document.title)[:80]
                        prefix = f"{root}/writing/{document.id}_{safe_title}"
                        for section in document.sections or []:
                            safe_section = _safe_name(section.section_key or section.heading)[:64]
                            archive.writestr(f"{prefix}/{safe_section}.md", section.content_markdown or "")

                    for consult in clinical_consults:
                        safe_question = _safe_name((consult.question or "consult"))[:80]
                        archive.writestr(
                            f"{root}/clinical_consults/{consult.id}_{safe_question}.md",
                            consult.answer_markdown or "",
                        )

                size_kb = out_abs.stat().st_size // 1024 if out_abs.exists() else None

            output = {"zip_file_path": out_rel, "filename": filename, "size_kb": size_kb}
            await job_mark_completed(job_uuid, result={"output": output, "warnings": [], "errors": []})
            return output
        except Exception as exc:
            await job_mark_failed(job_uuid, str(exc))
            return {"output": {}, "warnings": [], "errors": [str(exc)]}

    return run_coro(_async_logic())
