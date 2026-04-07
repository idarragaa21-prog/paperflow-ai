"""Project ZIP export worker job."""
from __future__ import annotations

import json
import re
import zipfile
from datetime import datetime
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


def export_project_zip_job(job_db_id: str, project_id: str) -> dict[str, Any]:
    """Export a project as a ZIP (papers + notes + presentations + meta exports + clinical sheets). SYNC wrapper."""

    async def _async_logic() -> dict[str, Any]:
        job_uuid = UUID(job_db_id)
        project_uuid = UUID(project_id)

        try:
            await job_mark_started(job_uuid)
            await job_set_progress(job_uuid, 5, status="started")

            async with async_session_maker() as db:
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
