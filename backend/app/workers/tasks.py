"""Compatibility shim for worker tasks.

Domain worker implementations live in:
- tasks_pdf.py
- tasks_meta.py
- tasks_exports.py

Keep this module thin so legacy imports continue to resolve without growing a new monolith.
"""
from __future__ import annotations

from app.workers._run_coro import run_coro
from app.workers.tasks_exports import export_project_zip_job
from app.workers.tasks_meta import meta_export_job, meta_extract_batch_job, meta_extract_paper_job
from app.workers.tasks_pdf import batch_download_papers_job, process_pdf_job, summarize_paper_job

__all__ = [
    "run_coro",
    "process_pdf_job",
    "summarize_paper_job",
    "batch_download_papers_job",
    "meta_extract_paper_job",
    "meta_extract_batch_job",
    "meta_export_job",
    "export_project_zip_job",
]
