export type TocItem = { id: string; text: string };

export type EvidenceStrength = 'high' | 'medium' | 'low' | 'na';

export type EvidenceSummary = {
  sourcesCount: number;
  projectPapers: Array<{
    paper_id: string;
    title?: string | null;
    pmid?: string | null;
    doi?: string | null;
    year?: number | null;
    oa?: boolean | null;
  }>;
  onlineSources: Array<{ label: string; url?: string }>;
  evidenceStrength?: EvidenceStrength;
  gaps: string[];
};

export type ClinicalSheetDetail = {
  id: string;
  project_id?: string | null;
  topic: string;
  version: number;
  is_current: boolean;
  content_markdown: string;
  content_json?: any;
  format_version?: string | null;
  references_json?: any;
  sources_used?: any;
  llm_model?: string | null;
  llm_usage?: any;
  created_at?: string | null;
  updated_at?: string | null;
};

export type ClinicalSheetVersionRow = {
  id: string;
  version: number;
  is_current: boolean;
  created_at?: string | null;
};
