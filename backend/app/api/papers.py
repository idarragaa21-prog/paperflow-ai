from datetime import datetime
from pathlib import Path
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.storage import storage_manager
from app.middleware.rate_limit import limiter
from app.models.document import PaperCitationSpan, PaperFile, PaperParseRun
from app.models.job import Job
from app.models.paper import Paper
from app.models.user import User
from app.schemas.papers import (
    BatchDownloadPaperRef,
    PaperDeleteResponse,
    PaperDownloadRequest,
    PaperRecordResponse,
    PapersBatchDownloadRequest,
)
from app.services.audit import log_audit
from app.services.jobs import enqueue_process_pdf, get_job_queue
from app.services.paper_repo import SQLPaperRepository
from app.services.paper_service import PaperDownloadService, PaperServiceError, sha256_hex
from app.services.pdf_processor import process_paper
from app.services.vector_index import vector_index

router = APIRouter(prefix="/papers", tags=["papers"])


def _safe_abs_path(relative_path: str) -> Path:
    if storage_manager.is_s3:
        raise HTTPException(status_code=400, detail="S3-backed files do not have a local path")
    full_path = (storage_manager.base_dir / relative_path).resolve()
    try:
        full_path.relative_to(storage_manager.base_dir)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid file path")
    return full_path


def get_repo(db: AsyncSession = Depends(get_db)) -> SQLPaperRepository:
    return SQLPaperRepository(db)


def get_downloader() -> PaperDownloadService:
    return PaperDownloadService()


async def _require_owned_project(repo: SQLPaperRepository, *, project_id: UUID, user: User) -> None:
    project = await repo.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    if project.user_id != user.id:
        raise HTTPException(status_code=403, detail="Proyecto no pertenece al usuario")


def _paper_to_response(p: Paper, *, duplicate: bool = False) -> PaperRecordResponse:
    return PaperRecordResponse(
        id=p.id,
        project_id=p.project_id,
        title=p.title,
        doi=getattr(p, "doi", None),
        pmid=getattr(p, "pmid", None),
        pmcid=getattr(p, "pmcid", None),
        journal=getattr(p, "journal", None),
        publication_year=getattr(p, "publication_year", None),
        language=getattr(p, "language", None),
        abstract_text=getattr(p, "abstract_text", None),
        source_provider=getattr(p, "source_provider", None),
        source_type=getattr(p, "source_type", None),
        is_open_access=bool(getattr(p, "is_open_access", False)),
        oa_url=getattr(p, "oa_url", None),
        filename=p.filename,
        file_path=p.file_path,
        file_size_kb=getattr(p, "file_size_kb", None),
        content_hash=p.content_hash,
        processing_status=getattr(p, "processing_status", "uploaded") or "uploaded",
        duplicate=duplicate,
    )


@router.post("/download", response_model=PaperRecordResponse)
@limiter.limit("3/minute")
async def download_paper(
    request: Request,
    payload: PaperDownloadRequest,
    repo: SQLPaperRepository = Depends(get_repo),
    downloader: PaperDownloadService = Depends(get_downloader),
    user: User = Depends(get_current_user),
):
    await _require_owned_project(repo, project_id=payload.project_id, user=user)

    if not payload.doi and not payload.pmid:
        raise HTTPException(status_code=400, detail="Debe indicar doi o pmid")

    # Dedup 1: by (project_id, pmid/doi) BEFORE downloading.
    dup = await repo.find_duplicate_by_identifiers(project_id=payload.project_id, pmid=payload.pmid, doi=payload.doi)
    if dup:
        return _paper_to_response(dup, duplicate=True)

    async with httpx.AsyncClient() as client:
        try:
            dl = await downloader.download_open_access_pdf(doi=payload.doi, pmid=payload.pmid, client=client)
        except PaperServiceError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except httpx.HTTPError:
            raise HTTPException(status_code=502, detail="No se pudo descargar el PDF")

    # Validate + hash
    content_hash = sha256_hex(dl.pdf_bytes)

    # Dedup 2: by (project_id, content_hash) ALWAYS.
    dup2 = await repo.find_duplicate_by_hash(project_id=payload.project_id, content_hash=content_hash)
    if dup2:
        return _paper_to_response(dup2, duplicate=True)

    # Persist file
    try:
        saved = await storage_manager.save_paper_bytes(
            data=dl.pdf_bytes,
            project_id=payload.project_id,
            suggested_filename=(payload.title or "paper") + ".pdf" if payload.title else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    paper = Paper(
        project_id=payload.project_id,
        title=payload.title or payload.doi or payload.pmid or "Paper",
        authors=None,
        doi=payload.doi,
        pmid=payload.pmid,
        pmcid=None,
        source_provider=dl.source,
        source_type="download",
        is_open_access=True,
        filename=saved["filename"],
        file_path=saved["file_path"],
        file_size_kb=saved["size_kb"],
        content_hash=saved["content_hash"],
        downloaded_at=datetime.utcnow(),
    )

    paper = await repo.create_paper(paper)
    repo.db.add(
        PaperFile(
            paper_id=paper.id,
            filename=paper.filename,
            storage_path=paper.file_path,
            size_kb=paper.file_size_kb,
            checksum=paper.content_hash,
            is_primary=True,
        )
    )
    await repo.db.commit()

    await log_audit(
        repo.db,
        user=user,
        action="download",
        entity_type="paper",
        entity_id=paper.id,
        details={
            "project_id": str(paper.project_id),
            "source": dl.source,
            "doi": paper.doi,
            "pmid": paper.pmid,
            "filename": paper.filename,
            "size_kb": paper.file_size_kb,
            "content_hash": paper.content_hash,
        },
        request=request,
    )

    return _paper_to_response(paper)


@router.post("/batch-download")
@limiter.limit("3/minute")
async def batch_download(
    request: Request,
    payload: PapersBatchDownloadRequest,
    repo: SQLPaperRepository = Depends(get_repo),
    user: User = Depends(get_current_user),
):
    await _require_owned_project(repo, project_id=payload.project_id, user=user)

    papers = [p.model_dump() for p in (payload.papers or [])]
    if not papers:
        raise HTTPException(status_code=400, detail="papers requerido")
    if len(papers) > 50:
        raise HTTPException(status_code=400, detail="Máximo 50 papers por batch")

    # Create DB job
    job_record = Job(
        user_id=user.id,
        job_type="batch_download_papers",
        status="queued",
        input_params={"project_id": str(payload.project_id), "count": len(papers)},
        result={},
        progress_percent=0,
    )
    repo.db.add(job_record)
    await repo.db.commit()
    await repo.db.refresh(job_record)

    try:
        from app.workers.tasks import batch_download_papers_job

        q = get_job_queue()
        rq_job = q.enqueue(batch_download_papers_job, args=(str(job_record.id), str(payload.project_id), papers), job_timeout="60m")
    except Exception:
        job_record.status = "failed"
        job_record.error_message = "No se pudo encolar job (Redis no disponible?)"
        await repo.db.commit()
        raise HTTPException(status_code=503, detail="No se pudo encolar job")

    job_record.result = {"rq_job_id": rq_job.id}
    await repo.db.commit()

    await log_audit(
        repo.db,
        user=user,
        action="batch_download",
        entity_type="project",
        entity_id=payload.project_id,
        details={"count": len(papers)},
        request=request,
    )

    return {"job_id": str(job_record.id)}


@router.post("/upload", response_model=PaperRecordResponse)
@limiter.limit("10/minute")
async def upload_paper(
    request: Request,
    project_id: UUID = Form(...),
    file: UploadFile = File(...),
    repo: SQLPaperRepository = Depends(get_repo),
    user: User = Depends(get_current_user),
):
    await _require_owned_project(repo, project_id=project_id, user=user)

    data = await file.read()
    if not storage_manager.validate_pdf(data):
        raise HTTPException(status_code=400, detail="Archivo no es un PDF válido")

    content_hash = sha256_hex(data)

    dup = await repo.find_duplicate_by_hash(project_id=project_id, content_hash=content_hash)
    if dup:
        return _paper_to_response(dup, duplicate=True)

    # Persist file
    try:
        saved = await storage_manager.save_paper_bytes(
            data=data,
            project_id=project_id,
            suggested_filename=file.filename or None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    paper = Paper(
        project_id=project_id,
        title=(file.filename or "Uploaded paper"),
        authors=None,
        doi=None,
        pmid=None,
        pmcid=None,
        source_provider="manual_upload",
        source_type="upload",
        is_open_access=False,
        filename=saved["filename"],
        file_path=saved["file_path"],
        file_size_kb=saved["size_kb"],
        content_hash=saved["content_hash"],
        downloaded_at=datetime.utcnow(),
    )
    paper = await repo.create_paper(paper)
    repo.db.add(
        PaperFile(
            paper_id=paper.id,
            filename=paper.filename,
            storage_path=paper.file_path,
            size_kb=paper.file_size_kb,
            checksum=paper.content_hash,
            is_primary=True,
        )
    )
    await repo.db.commit()

    await log_audit(
        repo.db,
        user=user,
        action="create",
        entity_type="paper",
        entity_id=paper.id,
        details={
            "project_id": str(paper.project_id),
            "filename": paper.filename,
            "size_kb": paper.file_size_kb,
            "content_hash": paper.content_hash,
        },
        request=request,
    )

    return _paper_to_response(paper)


@router.get("/projects/{project_id}")
async def list_papers(
    project_id: UUID,
    repo: SQLPaperRepository = Depends(get_repo),
    user: User = Depends(get_current_user),
):
    await _require_owned_project(repo, project_id=project_id, user=user)

    from sqlalchemy import select

    q = await repo.db.execute(select(Paper).where(Paper.project_id == project_id).order_by(Paper.created_at.desc()))
    items = q.scalars().all()
    return [
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
            "processing_status": p.processing_status,
            "processing_warnings": p.processing_warnings or [],
            "journal": p.journal,
            "publication_year": p.publication_year,
            "language": p.language,
            "source_provider": p.source_provider,
            "source_type": p.source_type,
            "is_open_access": p.is_open_access,
            "oa_url": p.oa_url,
            "favorite": p.favorite,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in items
    ]


@router.get("/{paper_id}")
async def get_paper(
    paper_id: UUID,
    repo: SQLPaperRepository = Depends(get_repo),
    user: User = Depends(get_current_user),
):
    paper = await repo.get_paper(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    await _require_owned_project(repo, project_id=paper.project_id, user=user)
    return {
        "id": str(paper.id),
        "project_id": str(paper.project_id),
        "title": paper.title,
        "authors": paper.authors,
        "doi": paper.doi,
        "pmid": paper.pmid,
        "pmcid": paper.pmcid,
        "filename": paper.filename,
        "file_path": paper.file_path,
        "file_size_kb": paper.file_size_kb,
        "content_hash": paper.content_hash,
        "is_processed": paper.is_processed,
        "processing_status": paper.processing_status,
        "processing_error": paper.processing_error,
        "processing_warnings": paper.processing_warnings or [],
        "journal": paper.journal,
        "publication_year": paper.publication_year,
        "language": paper.language,
        "abstract_text": paper.abstract_text,
        "source_provider": paper.source_provider,
        "source_type": paper.source_type,
        "is_open_access": paper.is_open_access,
        "oa_url": paper.oa_url,
        "favorite": paper.favorite,
        "full_text_extracted": paper.full_text_extracted,
        "downloaded_at": paper.downloaded_at.isoformat() if paper.downloaded_at else None,
        "created_at": paper.created_at.isoformat() if paper.created_at else None,
    }


@router.get("/{paper_id}/download")
async def download_paper_file(
    paper_id: UUID,
    repo: SQLPaperRepository = Depends(get_repo),
    user: User = Depends(get_current_user),
):
    paper = await repo.get_paper(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    # ownership via project
    await _require_owned_project(repo, project_id=paper.project_id, user=user)

    if not paper.file_path or not paper.filename:
        raise HTTPException(status_code=404, detail="Paper file missing")

    if storage_manager.is_s3:
        try:
            data = storage_manager.read_bytes(paper.file_path)
        except Exception as exc:
            raise HTTPException(status_code=404, detail=f"File not found: {exc}") from exc
        return Response(
            content=data,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{paper.filename}"'},
        )

    abs_path = _safe_abs_path(paper.file_path)
    if not abs_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(abs_path, filename=paper.filename, media_type="application/pdf")


@router.post("/{paper_id}/process")
@limiter.limit("10/minute")
async def process_paper_endpoint(
    request: Request,
    paper_id: UUID,
    repo: SQLPaperRepository = Depends(get_repo),
    user: User = Depends(get_current_user),
):
    paper = await repo.get_paper(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    await _require_owned_project(repo, project_id=paper.project_id, user=user)

    # Create DB job record
    job_record = Job(
        user_id=user.id,
        job_type="process_pdf",
        status="queued",
        input_params={"paper_id": str(paper_id)},
        result={},
        progress_percent=0,
    )
    repo.db.add(job_record)
    await repo.db.commit()
    await repo.db.refresh(job_record)

    # Enqueue RQ
    try:
        rq_job_id = enqueue_process_pdf(job_record.id, paper_id)
    except Exception:
        result = await process_paper(paper_id, repo.db)
        await vector_index.index_paper(repo.db, paper_id=paper_id)
        job_record.status = "completed"
        job_record.progress_percent = 100
        job_record.result = {"mode": "sync_fallback", "output": result}
        await repo.db.commit()
        return {"job_id": str(job_record.id), "mode": "sync_fallback", "result": result}

    job_record.result = {"rq_job_id": rq_job_id}
    await repo.db.commit()

    return {"job_id": str(job_record.id)}


@router.get("/{paper_id}/content")
async def get_paper_content(
    paper_id: UUID,
    repo: SQLPaperRepository = Depends(get_repo),
    user: User = Depends(get_current_user),
):
    paper = await repo.get_paper(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    await _require_owned_project(repo, project_id=paper.project_id, user=user)

    from sqlalchemy import select

    parse_q = await repo.db.execute(
        select(PaperParseRun).where(PaperParseRun.paper_id == paper.id).order_by(PaperParseRun.created_at.desc())
    )
    parse_run = parse_q.scalars().first()
    if not parse_run:
        return {"paper_id": str(paper.id), "status": paper.processing_status, "pages": [], "full_text": paper.full_text_extracted}

    from app.models.document import PaperChunk

    chunks_q = await repo.db.execute(
        select(PaperChunk).where(PaperChunk.parse_run_id == parse_run.id).order_by(PaperChunk.page_number.asc(), PaperChunk.chunk_index.asc())
    )
    chunks = chunks_q.scalars().all()
    pages: dict[int, list[dict]] = {}
    for chunk in chunks:
        pages.setdefault(chunk.page_number, []).append(
            {
                "id": str(chunk.id),
                "chunk_index": chunk.chunk_index,
                "text": chunk.text,
                "locator": chunk.locator,
                "token_count": chunk.token_count,
            }
        )

    return {
        "paper_id": str(paper.id),
        "status": paper.processing_status,
        "parse_run_id": str(parse_run.id),
        "warnings": parse_run.warnings or [],
        "pages": parse_run.metadata_json.get("pages") if parse_run.metadata_json else [{"page_number": page_number, "chunks": items} for page_number, items in sorted(pages.items())],
        "blocks": parse_run.metadata_json.get("blocks", []) if parse_run.metadata_json else [],
        "tables": parse_run.metadata_json.get("tables", []) if parse_run.metadata_json else [],
        "figures": parse_run.metadata_json.get("figures", []) if parse_run.metadata_json else [],
        "sections": parse_run.metadata_json.get("sections", []) if parse_run.metadata_json else [],
        "references": parse_run.metadata_json.get("references", []) if parse_run.metadata_json else [],
        "ocr": parse_run.metadata_json.get("ocr", {}) if parse_run.metadata_json else {},
        "failure_classification": parse_run.metadata_json.get("failure_classification", []) if parse_run.metadata_json else [],
        "full_text": paper.full_text_extracted,
    }


@router.get("/{paper_id}/citations")
async def get_paper_citations(
    paper_id: UUID,
    repo: SQLPaperRepository = Depends(get_repo),
    user: User = Depends(get_current_user),
):
    paper = await repo.get_paper(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    await _require_owned_project(repo, project_id=paper.project_id, user=user)

    from sqlalchemy import select

    q = await repo.db.execute(
        select(PaperCitationSpan).where(PaperCitationSpan.paper_id == paper.id).order_by(PaperCitationSpan.page_number.asc())
    )
    citations = q.scalars().all()
    return [
        {
            "id": str(c.id),
            "page_number": c.page_number,
            "label": c.label,
            "locator": c.locator,
            "quoted_text": c.quoted_text,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in citations
    ]


@router.get("/{paper_id}/parse-runs")
async def get_paper_parse_runs(
    paper_id: UUID,
    repo: SQLPaperRepository = Depends(get_repo),
    user: User = Depends(get_current_user),
):
    paper = await repo.get_paper(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    await _require_owned_project(repo, project_id=paper.project_id, user=user)

    from sqlalchemy import select

    q = await repo.db.execute(
        select(PaperParseRun).where(PaperParseRun.paper_id == paper.id).order_by(PaperParseRun.created_at.desc())
    )
    runs = q.scalars().all()
    return [
        {
            "id": str(run.id),
            "status": run.status,
            "parser_name": run.parser_name,
            "parser_version": run.parser_version,
            "used_ocr": run.used_ocr,
            "pages_count": run.pages_count,
            "chars_extracted": run.chars_extracted,
            "warnings": run.warnings or [],
            "metadata": run.metadata_json or {},
            "created_at": run.created_at.isoformat() if run.created_at else None,
        }
        for run in runs
    ]


@router.delete("/{paper_id}", response_model=PaperDeleteResponse)
async def delete_paper(
    request: Request,
    paper_id: UUID,
    repo: SQLPaperRepository = Depends(get_repo),
    user: User = Depends(get_current_user),
):
    paper = await repo.get_paper(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    await _require_owned_project(repo, project_id=paper.project_id, user=user)

    if paper.file_path:
        try:
            storage_manager.delete_file(paper.file_path)
        except Exception:
            pass

    await repo.delete_paper(paper)

    await log_audit(
        repo.db,
        user=user,
        action="delete",
        entity_type="paper",
        entity_id=paper_id,
        details={"project_id": str(paper.project_id)},
        request=request,
    )

    return PaperDeleteResponse(ok=True)
