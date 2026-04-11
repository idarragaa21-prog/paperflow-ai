from .papers import lookup_crossref_doi, search_crossref
from .pdf import extract_pdf_text, infer_study_fields, validate_pdf_target
from .code import apply_edit_operations, collect_repo_snapshot, find_repo_root, run_validation_command, search_relevant_files
from .excel import fill_extraction_workbook
from .system import execute_app_action, infer_app_request, normalize_command, run_applescript, run_safe_command
from .audio import inspect_audio, synthesize_speech, transcribe_audio
from .web import browser_navigate, extract_html_summary, find_pdf_links_in_html, looks_like_url
