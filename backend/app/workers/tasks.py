"""Backward-compatible re-exports for all worker task functions.

The implementation has been split into domain-specific modules:
  - tasks_pdf.py       — PDF processing, paper summarization, batch download
  - tasks_meta.py      — Meta-analysis extraction and export
  - tasks_clinical.py  — Clinical sheet generation
  - tasks_presentation.py — Presentation (PPTX) generation
  - tasks_books.py     — Book indexing
  - tasks_export.py    — Project ZIP export

All public names are re-exported here so that existing RQ job references
(stored as "app.workers.tasks.<function_name>") continue to resolve.
"""
from __future__ import annotations

from app.workers._run_coro import run_coro  # noqa: F401 — kept for any direct imports
from app.workers.tasks_pdf import (  # noqa: F401
    process_pdf_job,
    summarize_paper_job,
    batch_download_papers_job,
)
from app.workers.tasks_meta import (  # noqa: F401
    meta_extract_paper_job,
    meta_extract_batch_job,
    meta_export_excel_job,
    meta_export_job,
)
from app.workers.tasks_clinical import (  # noqa: F401
    clinical_query_job,
    clinical_generate_sheet_job,
)
from app.workers.tasks_presentation import (  # noqa: F401
    GeneratePresentationParams,
    generate_presentation_job,
)
from app.workers.tasks_books import books_index_job  # noqa: F401
from app.workers.tasks_export import export_project_zip_job  # noqa: F401

__all__ = [
    "run_coro",
    "process_pdf_job",
    "summarize_paper_job",
    "batch_download_papers_job",
    "meta_extract_paper_job",
    "meta_extract_batch_job",
    "meta_export_excel_job",
    "meta_export_job",
    "clinical_query_job",
    "clinical_generate_sheet_job",
    "GeneratePresentationParams",
    "generate_presentation_job",
    "books_index_job",
    "export_project_zip_job",
]
