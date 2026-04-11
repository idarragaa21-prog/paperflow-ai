import { useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';

type WritingMode = 'narrative' | 'systematic_review' | 'meta_analysis' | 'letter_to_editor' | 'cover_letter';

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

export default function WritingAssistantPage() {
  const { projectId } = useParams();
  const qc = useQueryClient();
  const [title, setTitle] = useState('Manuscript draft');
  const [mode, setMode] = useState<WritingMode>('meta_analysis');
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(null);
  const [editingSectionId, setEditingSectionId] = useState<string | null>(null);
  const [editContent, setEditContent] = useState('');
  const [error, setError] = useState<string | null>(null);

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
      setEditingSectionId(null);
      setEditContent('');
      setError(null);
      await qc.invalidateQueries({ queryKey: ['writing-documents', projectId] });
    },
    onError: (e: unknown) => {
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
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(220px, 1fr) minmax(220px, 280px) auto', gap: 10, alignItems: 'end' }}>
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

      <div className="rc-workspace-grid" style={{ gridTemplateColumns: 'minmax(260px, 360px) minmax(0, 1fr)' }}>
        <section className="rc-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div className="rc-card-title" style={{ margin: 0 }}>Documents</div>
            <button className="rc-btn rc-btn--sm rc-btn--ghost" onClick={() => documentsQuery.refetch()} disabled={documentsQuery.isFetching}>
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
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div className="rc-card-title" style={{ margin: 0 }}>Document workspace</div>
            <button
              className="rc-btn rc-btn--sm rc-btn--primary"
              onClick={() => resolveMutation.mutate()}
              disabled={!selectedDocument || resolveMutation.isPending}
            >
              {resolveMutation.isPending ? 'Resolving…' : 'Resolve citations'}
            </button>
          </div>

          {!selectedDocument ? <div className="rc-muted">Select a document.</div> : null}

          {selectedDocument ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {(selectedDocument.sections || []).map((section) => (
                <div key={section.id} className="rc-card" style={{ padding: 12 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                    <div style={{ fontWeight: 700 }}>{section.heading}</div>
                    <div style={{ display: 'flex', gap: 8 }}>
                      <button
                        className="rc-btn rc-btn--sm"
                        onClick={() => generateSectionMutation.mutate(section.section_key)}
                        disabled={generateSectionMutation.isPending}
                      >
                        Generate
                      </button>
                      {editingSectionId !== section.id ? (
                        <button
                          className="rc-btn rc-btn--sm rc-btn--ghost"
                          onClick={() => {
                            setEditingSectionId(section.id);
                            setEditContent(section.content_markdown || '');
                          }}
                        >
                          Edit
                        </button>
                      ) : null}
                    </div>
                  </div>

                  {editingSectionId === section.id ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                      <textarea
                        className="rc-textarea"
                        value={editContent}
                        onChange={(e) => setEditContent(e.target.value)}
                        style={{ minHeight: 140 }}
                      />
                      <div style={{ display: 'flex', gap: 8 }}>
                        <button
                          className="rc-btn rc-btn--primary rc-btn--sm"
                          onClick={() => saveSectionMutation.mutate({ sectionKey: section.section_key, content: editContent })}
                          disabled={saveSectionMutation.isPending}
                        >
                          Save
                        </button>
                        <button className="rc-btn rc-btn--sm" onClick={() => setEditingSectionId(null)}>
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontFamily: 'inherit', fontSize: 13, lineHeight: 1.6 }}>
                      {section.content_markdown || '_No content_'}
                    </pre>
                  )}
                </div>
              ))}

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
                <div style={{ fontWeight: 700, marginBottom: 8 }}>Claim links</div>
                {(selectedDocument.claim_links || []).length === 0 ? <div className="rc-muted">No claim links yet.</div> : null}
                {(selectedDocument.claim_links || []).slice(0, 20).map((claim) => (
                  <div key={claim.id} className="rc-help">
                    {claim.citation_marker} {claim.claim_text} · {claim.source_type}
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
