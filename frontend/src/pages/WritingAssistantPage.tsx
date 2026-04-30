import { useEffect, useMemo, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';

type WritingMode = 'narrative' | 'systematic_review' | 'meta_analysis' | 'letter_to_editor' | 'cover_letter';
type CitationStyle = 'apa' | 'vancouver' | 'ama';
type ExportFormat = 'docx' | 'pdf' | 'md';

type WritingSection = {
  id: string;
  section_key: string;
  heading: string;
  position: number;
  status: string;
  content_markdown: string;
};

type WritingClaimLink = {
  id: string;
  section_id: string | null;
  claim_text: string;
  source_type: string;
  source_id: string;
  citation_marker: string;
  confidence: number | null;
};

type WritingDocument = {
  id: string;
  project_id: string;
  title: string;
  mode: WritingMode;
  status: string;
  version: number;
  sections: WritingSection[];
  claim_links: WritingClaimLink[];
  created_at?: string | null;
};

const MODES: WritingMode[] = ['narrative', 'systematic_review', 'meta_analysis', 'letter_to_editor', 'cover_letter'];
const CITATION_STYLES: CitationStyle[] = ['apa', 'vancouver', 'ama'];

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  setTimeout(() => {
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, 0);
}

export default function WritingAssistantPage() {
  const { projectId } = useParams();
  const qc = useQueryClient();
  const [title, setTitle] = useState('Manuscript draft');
  const [mode, setMode] = useState<WritingMode>('meta_analysis');
  const [citationStyle, setCitationStyle] = useState<CitationStyle>('apa');
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(null);
  const [editingSectionId, setEditingSectionId] = useState<string | null>(null);
  const [editContent, setEditContent] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [autoSaveState, setAutoSaveState] = useState<'idle' | 'saving' | 'saved'>('idle');
  const editTextareaRef = useRef<HTMLTextAreaElement | null>(null);

  const documentsQuery = useQuery<WritingDocument[]>({
    queryKey: ['writing-documents', projectId],
    enabled: Boolean(projectId),
    queryFn: async () => {
      const response = await api.get('/writing/documents', { params: { project_id: projectId } });
      return response.data as WritingDocument[];
    },
  });

  const selectedDocument = useMemo(() => {
    if (!documentsQuery.data || documentsQuery.data.length === 0) return null;
    if (selectedDocumentId) return documentsQuery.data.find((item) => item.id === selectedDocumentId) || null;
    return documentsQuery.data[0];
  }, [documentsQuery.data, selectedDocumentId]);

  const editingSection = useMemo(
    () => selectedDocument?.sections.find((s) => s.id === editingSectionId) || null,
    [selectedDocument, editingSectionId],
  );

  const createMutation = useMutation({
    mutationFn: async () => {
      const response = await api.post('/writing/documents', {
        project_id: projectId,
        title: title.trim(),
        mode,
      });
      return response.data as WritingDocument;
    },
    onSuccess: async (document) => {
      setSelectedDocumentId(document.id);
      setError(null);
      await qc.invalidateQueries({ queryKey: ['writing-documents', projectId] });
    },
    onError: (e: unknown) => {
      setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Could not create document');
    },
  });

  const generateSectionMutation = useMutation({
    mutationFn: async (sectionKey: string) => {
      if (!selectedDocument) throw new Error('No document selected');
      const response = await api.post(`/writing/documents/${selectedDocument.id}/sections/${sectionKey}`);
      return response.data as WritingDocument;
    },
    onSuccess: async () => {
      setError(null);
      await qc.invalidateQueries({ queryKey: ['writing-documents', projectId] });
    },
    onError: (e: unknown) => {
      setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Could not generate section');
    },
  });

  const saveSectionMutation = useMutation({
    mutationFn: async ({ sectionKey, content }: { sectionKey: string; content: string }) => {
      if (!selectedDocument) throw new Error('No document selected');
      const response = await api.patch(`/writing/documents/${selectedDocument.id}/sections/${sectionKey}`, {
        content_markdown: content,
      });
      return response.data as WritingDocument;
    },
    onSuccess: async () => {
      setAutoSaveState('saved');
      setError(null);
      await qc.invalidateQueries({ queryKey: ['writing-documents', projectId] });
    },
    onError: (e: unknown) => {
      setAutoSaveState('idle');
      setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Could not save section');
    },
  });

  const resolveMutation = useMutation({
    mutationFn: async () => {
      if (!selectedDocument) throw new Error('No document selected');
      const response = await api.post(`/writing/documents/${selectedDocument.id}/citations/resolve`);
      return response.data as { count: number; citations: Array<{ marker: string; claim_text: string }> };
    },
    onError: (e: unknown) => {
      setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Could not resolve citations');
    },
  });

  const exportMutation = useMutation({
    mutationFn: async (format: ExportFormat) => {
      if (!selectedDocument) throw new Error('No document selected');
      const response = await api.get(`/writing/documents/${selectedDocument.id}/export`, {
        params: { format, citation_style: citationStyle },
        responseType: 'blob',
      });
      const ext = format === 'md' ? 'md' : format;
      const filename = `${selectedDocument.title.replace(/[^a-z0-9_-]/gi, '_').slice(0, 80) || 'document'}.${ext}`;
      downloadBlob(response.data as Blob, filename);
      return { filename };
    },
    onError: (e: unknown) => {
      setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Could not export document');
    },
  });

  // ── Auto-save (debounced 2s) ─────────────────────────────
  useEffect(() => {
    if (!editingSection) return;
    if (editContent === editingSection.content_markdown) {
      setAutoSaveState('idle');
      return;
    }
    setAutoSaveState('saving');
    const timer = window.setTimeout(() => {
      saveSectionMutation.mutate({ sectionKey: editingSection.section_key, content: editContent });
    }, 2000);
    return () => window.clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [editContent, editingSection?.id]);

  // ── Insert citation marker at cursor position ────────────
  const insertCitation = (marker: string) => {
    const ta = editTextareaRef.current;
    if (!ta) {
      setEditContent((prev) => `${prev} ${marker}`);
      return;
    }
    const start = ta.selectionStart ?? editContent.length;
    const end = ta.selectionEnd ?? editContent.length;
    const next = `${editContent.slice(0, start)}${marker}${editContent.slice(end)}`;
    setEditContent(next);
    requestAnimationFrame(() => {
      ta.focus();
      ta.setSelectionRange(start + marker.length, start + marker.length);
    });
  };

  if (!projectId) {
    return <div className="rc-error">Missing project id</div>;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div>
        <h1 className="rc-page-title">Writing Assistant</h1>
        <div className="rc-subtitle">
          Grounded manuscript drafting based on matrix rows, meta-run outputs and traceable citations.
        </div>
      </div>

      {error ? <div className="rc-error">{error}</div> : null}

      <div className="rc-card">
        <div className="rc-card-title">Create document</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(220px, 1fr) minmax(180px, 220px) auto', gap: 10, alignItems: 'end' }}>
          <label className="rc-discover-filter-field">
            <span>Title</span>
            <input className="rc-input" value={title} onChange={(e) => setTitle(e.target.value)} />
          </label>
          <label className="rc-discover-filter-field">
            <span>Mode</span>
            <select className="rc-input" value={mode} onChange={(e) => setMode(e.target.value as WritingMode)}>
              {MODES.map((item) => (
                <option key={item} value={item}>{item}</option>
              ))}
            </select>
          </label>
          <button
            className="rc-btn rc-btn--primary"
            onClick={() => createMutation.mutate()}
            disabled={createMutation.isPending || title.trim().length < 2}
          >
            {createMutation.isPending ? 'Creating…' : 'Create document'}
          </button>
        </div>
      </div>

      <div className="rc-workspace-grid" style={{ gridTemplateColumns: 'minmax(260px, 320px) minmax(0, 1fr)' }}>
        <section className="rc-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div className="rc-card-title" style={{ margin: 0 }}>Documents</div>
            <button className="rc-btn rc-btn--sm rc-btn--ghost" onClick={() => documentsQuery.refetch()} disabled={documentsQuery.isFetching} aria-label="Refresh documents" title="Refresh documents">
              {documentsQuery.isFetching ? '…' : '↻'}
            </button>
          </div>

          {(documentsQuery.data || []).length === 0 ? <div className="rc-muted">No documents yet.</div> : null}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {(documentsQuery.data || []).map((document) => (
              <button
                key={document.id}
                className="rc-btn"
                style={{
                  textAlign: 'left',
                  alignItems: 'flex-start',
                  flexDirection: 'column',
                  gap: 4,
                  borderColor: selectedDocument?.id === document.id ? 'rgba(79,70,229,0.35)' : undefined,
                  background: selectedDocument?.id === document.id ? 'var(--rc-primary-weak)' : undefined,
                }}
                onClick={() => setSelectedDocumentId(document.id)}
              >
                <div style={{ fontWeight: 700 }}>{document.title}</div>
                <div className="rc-help">{document.mode} · v{document.version} · {document.status}</div>
              </button>
            ))}
          </div>
        </section>

        <section className="rc-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
            <div className="rc-card-title" style={{ margin: 0 }}>Document workspace</div>
            <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}>
              <label className="rc-help" style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                Citation
                <select
                  className="rc-input rc-input--sm"
                  value={citationStyle}
                  onChange={(e) => setCitationStyle(e.target.value as CitationStyle)}
                  style={{ width: 110 }}
                >
                  {CITATION_STYLES.map((item) => (
                    <option key={item} value={item}>{item.toUpperCase()}</option>
                  ))}
                </select>
              </label>
              <button
                className="rc-btn rc-btn--sm"
                onClick={() => resolveMutation.mutate()}
                disabled={!selectedDocument || resolveMutation.isPending}
              >
                {resolveMutation.isPending ? 'Resolving…' : 'Resolve citations'}
              </button>
              <button
                className="rc-btn rc-btn--sm rc-btn--primary"
                onClick={() => exportMutation.mutate('docx')}
                disabled={!selectedDocument || exportMutation.isPending}
                title="Export as Microsoft Word"
              >
                Export DOCX
              </button>
              <button
                className="rc-btn rc-btn--sm"
                onClick={() => exportMutation.mutate('pdf')}
                disabled={!selectedDocument || exportMutation.isPending}
              >
                PDF
              </button>
              <button
                className="rc-btn rc-btn--sm"
                onClick={() => exportMutation.mutate('md')}
                disabled={!selectedDocument || exportMutation.isPending}
              >
                MD
              </button>
            </div>
          </div>

          {!selectedDocument ? <div className="rc-muted">Select a document.</div> : null}

          {selectedDocument ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {(selectedDocument.sections || []).map((section) => {
                const isEmpty = !(section.content_markdown && section.content_markdown.replace(/^##\s+.*$/m, '').trim().length > 0);
                const isEditing = editingSectionId === section.id;
                return (
                  <div key={section.id} className="rc-card" style={{ padding: 12 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8, gap: 8, flexWrap: 'wrap' }}>
                      <div style={{ fontWeight: 700 }}>{section.heading}</div>
                      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                        {isEditing ? (
                          <span className="rc-help" style={{ minWidth: 70, textAlign: 'right' }}>
                            {autoSaveState === 'saving' ? 'Saving…' : autoSaveState === 'saved' ? 'Saved ✓' : ''}
                          </span>
                        ) : null}
                        <button
                          className="rc-btn rc-btn--sm"
                          onClick={() => generateSectionMutation.mutate(section.section_key)}
                          disabled={generateSectionMutation.isPending}
                          title="Regenerate this section from project evidence"
                        >
                          {generateSectionMutation.isPending ? 'Generating…' : 'Generate'}
                        </button>
                        {!isEditing ? (
                          <button
                            className="rc-btn rc-btn--sm rc-btn--ghost"
                            onClick={() => {
                              setEditingSectionId(section.id);
                              setEditContent(section.content_markdown || '');
                              setAutoSaveState('idle');
                            }}
                          >
                            Edit
                          </button>
                        ) : (
                          <button
                            className="rc-btn rc-btn--sm rc-btn--ghost"
                            onClick={() => {
                              setEditingSectionId(null);
                              setEditContent('');
                            }}
                          >
                            Done
                          </button>
                        )}
                      </div>
                    </div>

                    {isEditing ? (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                        <textarea
                          ref={editTextareaRef}
                          className="rc-textarea"
                          value={editContent}
                          onChange={(e) => setEditContent(e.target.value)}
                          style={{ minHeight: 220, fontFamily: 'inherit', fontSize: 13, lineHeight: 1.6 }}
                          placeholder="Write in Markdown. Use [M1], [R2], [C3] markers from the claim links panel below."
                        />
                        <div className="rc-help">
                          Auto-saves 2s after you stop typing. Markers like [M1] insert as superscripts in DOCX/PDF.
                        </div>
                      </div>
                    ) : isEmpty ? (
                      <div className="rc-muted" style={{ fontStyle: 'italic' }}>
                        Empty section — press <strong>Generate</strong> to build it from your matrix, meta runs and references,
                        or <strong>Edit</strong> to write it manually.
                      </div>
                    ) : (
                      <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontFamily: 'inherit', fontSize: 13, lineHeight: 1.6 }}>
                        {section.content_markdown}
                      </pre>
                    )}
                  </div>
                );
              })}

              {resolveMutation.data ? (
                <div className="rc-card" style={{ padding: 12 }}>
                  <div style={{ fontWeight: 700, marginBottom: 8 }}>
                    Citation map ({resolveMutation.data.count})
                  </div>
                  {(resolveMutation.data.citations || []).map((citation) => (
                    <div key={`${citation.marker}-${citation.claim_text}`} className="rc-help">
                      {citation.marker} {citation.claim_text}
                    </div>
                  ))}
                </div>
              ) : null}

              <div className="rc-card" style={{ padding: 12 }}>
                <div style={{ fontWeight: 700, marginBottom: 8, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span>Claim links</span>
                  {editingSection ? (
                    <span className="rc-help">Click a marker to insert it at the cursor</span>
                  ) : null}
                </div>
                {(selectedDocument.claim_links || []).length === 0 ? <div className="rc-muted">No claim links yet — press Generate on a section.</div> : null}
                {(selectedDocument.claim_links || []).slice(0, 30).map((claim) => (
                  <div key={claim.id} className="rc-help" style={{ display: 'flex', gap: 6, alignItems: 'flex-start', padding: '4px 0' }}>
                    {editingSection ? (
                      <button
                        className="rc-btn rc-btn--xs rc-btn--ghost"
                        onClick={() => insertCitation(claim.citation_marker)}
                        style={{ minWidth: 48 }}
                      >
                        {claim.citation_marker}
                      </button>
                    ) : (
                      <span style={{ fontWeight: 600, minWidth: 48 }}>{claim.citation_marker}</span>
                    )}
                    <span>{claim.claim_text} <span className="rc-muted">· {claim.source_type}</span></span>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </section>
      </div>
    </div>
  );
}
