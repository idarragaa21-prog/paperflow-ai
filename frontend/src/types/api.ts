/**
 * Canonical API types shared across all pages.
 *
 * These mirror the Pydantic schemas on the backend.  Pages should import
 * from here instead of defining their own local copies.
 */

// ─── Auth ────────────────────────────────────────────────────────────────────

export type UserMe = {
  id: string;
  email: string;
  full_name?: string | null;
};

// ─── Projects ────────────────────────────────────────────────────────────────

export type Project = {
  id: string;
  title: string;
  description?: string | null;
  clinical_area?: string | null;
  archived: boolean;
  created_at?: string | null;
  updated_at?: string | null;
};

export type ProjectCounts = {
  papers: number;
  notes: number;
  presentations: number;
  references: number;
  meta_studies_current: number;
};

// ─── Papers ───────────────────────────────────────────────────────────────────

export type PaperRow = {
  id: string;
  project_id: string;
  title: string;
  authors?: string | null;
  journal?: string | null;
  publication_year?: number | null;
  doi?: string | null;
  pmid?: string | null;
  pmcid?: string | null;
  filename: string;
  file_size_kb?: number | null;
  is_processed: boolean;
  processing_status?: string;
  processing_warnings?: string[];
  source_provider?: string | null;
  source_type?: string | null;
  is_open_access?: boolean;
  oa_url?: string | null;
  favorite?: boolean;
  created_at?: string | null;
  downloaded_at?: string | null;
};

/** Result item from search endpoints (PubMed / federated) — not yet saved */
export type PaperSearchResult = {
  pmid?: string | null;
  pmcid?: string | null;
  doi?: string | null;
  title: string;
  authors?: string[];
  journal?: string | null;
  pub_year?: number | null;
  abstract?: string | null;
  source?: string | null;
  is_open_access?: boolean;
  oa_url?: string | null;
  relevance_score?: number | null;
};

// ─── Search ───────────────────────────────────────────────────────────────────

export type SearchResponse = {
  count: number;
  results: PaperSearchResult[];
  query_translation?: string | null;
  cached: boolean;
  sources?: string[];
};

export type SearchRecord = {
  id: string;
  project_id: string;
  query: string;
  source: string;
  results_count: number | null;
  executed_at: string | null;
};

// ─── Jobs ─────────────────────────────────────────────────────────────────────

export type JobStatus = 'queued' | 'started' | 'progress' | 'completed' | 'failed';

export type JobRow = {
  id: string;
  job_type: string;
  status: JobStatus;
  progress_percent: number;
  /** Backend field name — maps to error_message on the Job model */
  error_message?: string | null;
  /** Alias used in some older API responses */
  error?: string | null;
  result?: Record<string, unknown> | null;
  created_at?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
};

// ─── Notes ────────────────────────────────────────────────────────────────────

export type NoteRow = {
  id: string;
  title: string;
  note_type: string;
  paper_id?: string | null;
  created_at?: string | null;
};

export type NoteDetail = {
  id: string;
  project_id: string;
  paper_id?: string | null;
  title: string;
  content: string;
  note_type: string;
  llm_model?: string | null;
};

// ─── Drafts ───────────────────────────────────────────────────────────────────

export type DraftSection = {
  key: string;
  title: string;
  content: string;
};

export type DraftCitation = {
  id: string;
  text: string;
};

export type Draft = {
  id: string;
  title: string;
  status: string;
  version: number;
  sections: DraftSection[];
};

// ─── Presentations ────────────────────────────────────────────────────────────

export type PresentationRow = {
  id: string;
  title: string;
  topic: string;
  duration_minutes: number;
  audience: string;
  filename: string;
  created_at?: string | null;
};

// ─── References ───────────────────────────────────────────────────────────────

export type ReferenceRow = {
  id: string;
  paper_id?: string | null;
  title: string;
  authors: string[];
  journal?: string | null;
  publication_year?: number | null;
  doi?: string | null;
  pmid?: string | null;
  pmcid?: string | null;
  source_format: string;
};

// ─── Clinical ─────────────────────────────────────────────────────────────────

export type ClinicalSheetRow = {
  id: string;
  project_id?: string | null;
  topic: string;
  version: number;
  is_current?: boolean;
  created_at?: string | null;
  updated_at?: string | null;
};

// Full detail type lives in domain/clinical/types.ts — import from there.

// ─── Meta-analysis ────────────────────────────────────────────────────────────

export type StudyRow = {
  id: string;
  title: string;
  year?: number | null;
  design?: string | null;
  n?: number | null;
  rob_score?: number | null;
};

// ─── Books ────────────────────────────────────────────────────────────────────

export type BookRow = {
  id: string;
  title: string;
  filename: string;
  total_pages?: number | null;
  chapters?: Array<{ title: string; page_start?: number; page_end?: number }> | null;
  indexed_at?: string | null;
  created_at?: string | null;
};
