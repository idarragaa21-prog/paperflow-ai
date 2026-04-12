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
  references: number;
  meta_studies_current: number;
};

export type MembershipRole = 'owner' | 'editor' | 'viewer';

export type ProjectMember = {
  id?: string | null;
  project_id: string;
  user_id: string;
  email: string;
  full_name?: string | null;
  role: MembershipRole;
  created_at?: string | null;
};

export type ProjectInvitationStatus = 'pending' | 'accepted' | 'revoked';

export type ProjectInvitation = {
  id: string;
  project_id: string;
  email: string;
  role: MembershipRole;
  token: string;
  accept_path: string;
  status: ProjectInvitationStatus;
  created_at?: string | null;
  accepted_at?: string | null;
  revoked_at?: string | null;
};

export type ProjectInviteResult = {
  kind: 'membership' | 'invitation';
  member?: ProjectMember | null;
  invitation?: ProjectInvitation | null;
  invitation_url?: string | null;
  delivery_status?: 'sent' | 'manual_required' | null;
  delivery_method?: 'smtp' | 'manual_link' | null;
  delivery_detail?: string | null;
};

export type ProjectInvitationLookup = {
  id: string;
  project_id: string;
  project_title: string;
  email: string;
  role: MembershipRole;
  status: ProjectInvitationStatus;
  accept_path: string;
  accepted_at?: string | null;
  revoked_at?: string | null;
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
  download_trace?: PaperDownloadTrace | null;
  favorite?: boolean;
  created_at?: string | null;
  downloaded_at?: string | null;
};

export type PaperDownloadTrace = {
  title: string;
  paper_id: string;
  doi?: string | null;
  pmid?: string | null;
  pmcid?: string | null;
  source_provider?: string | null;
  oa_url?: string | null;
  landing_url?: string | null;
  resolved_url?: string | null;
  used_fallback: boolean;
  final_status: 'downloaded' | 'existing' | 'unavailable' | 'failed';
  failure_reason?: string | null;
  audited_at?: string | null;
};

export type PaperDetailResponse = PaperRow & {
  authors?: string | null;
  abstract_text?: string | null;
  full_text_extracted?: string | null;
  processing_error?: string | null;
  processing_warnings?: string[];
  download_trace?: PaperDownloadTrace | null;
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
  warnings?: string[];
};

export type SearchSynthesizeResponse = {
  answer: string;
};

export type BatchDownloadTraceItem = {
  title: string;
  pmid?: string | null;
  pmcid?: string | null;
  doi?: string | null;
  paper_id?: string | null;
  source_provider?: string | null;
  oa_url?: string | null;
  landing_url?: string | null;
  resolved_url?: string | null;
  used_fallback: boolean;
  final_status: 'downloaded' | 'existing' | 'unavailable' | 'failed';
  failure_reason?: string | null;
};

export type BatchDownloadOutput = {
  items: BatchDownloadTraceItem[];
  downloaded: BatchDownloadTraceItem[];
  already_exists: BatchDownloadTraceItem[];
  not_available: BatchDownloadTraceItem[];
  failed: BatchDownloadTraceItem[];
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
  id: string;
  key: string;
  heading: string;
  title: string;
  content: string;
  position: number;
  citations: DraftCitation[];
};

export type DraftCitation = {
  id: string;
  text: string;
  marker: string;
};

export type Draft = {
  id: string;
  title: string;
  status: string;
  version: number;
  sections: DraftSection[];
};

// ─── References ───────────────────────────────────────────────────────────────

export type ReferenceRow = {
  id: string;
  paper_id?: string | null;
  citation_key?: string | null;
  title: string;
  authors: string[];
  journal?: string | null;
  publication_year?: number | null;
  doi?: string | null;
  pmid?: string | null;
  pmcid?: string | null;
  source_format: string;
};

// ─── Meta-analysis ────────────────────────────────────────────────────────────

export type StudyRow = {
  id: string;
  title: string;
  paper_title?: string | null;
  paper_filename?: string | null;
  year?: number | null;
  design?: string | null;
  n?: number | null;
  rob_score?: number | null;
  rob_auto_generated?: boolean;
  version?: number | null;
  extraction_confidence?: number | string | null;
};
