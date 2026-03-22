import { useState } from 'react';
import type { Draft, DraftSection } from '../types/api';
import { useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { useToast } from '../ui/Toast/ToastProvider';


type EvidenceTable = {
  id: string;
  title: string;
  table_json: { count?: number };
  confidence: number;
};

function downloadText(content: string, filename: string) {
  const blob = new Blob([content], { type: 'text/html;charset=utf-8' });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click(); a.remove();
  window.URL.revokeObjectURL(url);
}

export default function DraftsPage() {
  const { projectId } = useParams();
  const toast = useToast();
  const qc = useQueryClient();

  const [title, setTitle] = useState('Narrative synthesis');
  const [heading, setHeading] = useState('Introduction');
  const [selectedDraft, setSelectedDraft] = useState<string>('');
  const [editingSection, setEditingSection] = useState<string | null>(null);
  const [editContent, setEditContent] = useState('');

  const { data: drafts = [], isError: draftsError } = useQuery<Draft[]>({
    queryKey: ['drafts', projectId],
    queryFn: async () => {
      const r = await api.get('/drafts', { params: { project_id: projectId } });
      const data = r.data as Draft[];
      if (!selectedDraft && data[0]) setSelectedDraft(data[0].id);
      return data;
    },
    enabled: !!projectId,
  });

  const { data: tables = [] } = useQuery<EvidenceTable[]>({
    queryKey: ['evidence-tables', projectId],
    queryFn: async () => {
      const r = await api.get('/evidence/tables', { params: { project_id: projectId } });
      return r.data as EvidenceTable[];
    },
    enabled: !!projectId,
  });

  function invalidate() {
    qc.invalidateQueries({ queryKey: ['drafts', projectId] });
    qc.invalidateQueries({ queryKey: ['evidence-tables', projectId] });
  }

  const createMut = useMutation({
    mutationFn: () => api.post('/drafts', { project_id: projectId, title }),
    onSuccess: (r) => {
      setSelectedDraft((r.data as Draft).id);
      invalidate();
    },
    onError: (e: any) => toast.error('Error', e?.response?.data?.detail || 'Failed to create draft'),
  });

  const generateMut = useMutation({
    mutationFn: () => api.post(`/drafts/${selectedDraft}/generate-section`, { heading, paper_ids: [], extraction_record_ids: [] }),
    onSuccess: () => invalidate(),
    onError: (e: any) => toast.error('Error', e?.response?.data?.detail || 'Failed to generate section'),
  });

  const buildEvidenceMut = useMutation({
    mutationFn: () => api.get('/evidence/tables', { params: { project_id: projectId, build: true } }),
    onSuccess: () => invalidate(),
    onError: (e: any) => toast.error('Error', e?.response?.data?.detail || 'Failed to build evidence table'),
  });

  const saveSectionMut = useMutation({
    mutationFn: ({ draftId, sectionId }: { draftId: string; sectionId: string }) =>
      api.patch(`/drafts/${draftId}/sections/${sectionId}`, { content: editContent }),
    onSuccess: () => {
      setEditingSection(null);
      toast.success('Saved', 'Section content updated.');
      invalidate();
    },
    onError: (e: any) => toast.error('Error', e?.response?.data?.detail || 'Failed to save section'),
  });

  const busy = createMut.isPending || generateMut.isPending || buildEvidenceMut.isPending;

  function startEdit(section: DraftSection) {
    setEditingSection(section.id);
    setEditContent(section.content);
  }

  function copyFullDraft(draft: Draft) {
    const text = draft.sections
      .sort((a, b) => a.position - b.position)
      .map(s => {
        const citations = s.citations.length > 0 ? `\n\n[${s.citations.map(c => c.marker).join(', ')}]` : '';
        return `# ${s.heading}\n\n${s.content}${citations}`;
      })
      .join('\n\n');
    navigator.clipboard.writeText(text);
    toast.success('\u2713 Copied', 'Full draft copied to clipboard.');
  }

  function exportHTML(draft: Draft) {
    const sections = draft.sections
      .sort((a, b) => a.position - b.position)
      .map(s => {
        const cites = s.citations.length > 0
          ? `<p style="font-size:12px;color:#666;">[${s.citations.map(c => c.marker).join(', ')}]</p>`
          : '';
        return `<h2>${s.heading}</h2>\n<div>${s.content.replace(/\n/g, '<br/>')}</div>\n${cites}`;
      })
      .join('\n<hr/>\n');

    const html = `<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>${draft.title}</title>
<style>body{font-family:system-ui;max-width:800px;margin:40px auto;padding:0 20px;line-height:1.6;color:#1e293b}
h1{border-bottom:2px solid #e2e8f0;padding-bottom:8px}h2{color:#4f46e5;margin-top:24px}hr{border:none;border-top:1px solid #e2e8f0;margin:24px 0}</style>
</head><body>
<h1>${draft.title}</h1>
<p style="color:#64748b">Version ${draft.version} &middot; Status: ${draft.status}</p>
${sections}
</body></html>`;

    const slug = draft.title.toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 40);
    downloadText(html, `${slug}.html`);
    toast.success('Exported', `${draft.title} downloaded as HTML.`);
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div>
        <h1 className="rc-page-title">Writing Studio</h1>
        <div className="rc-subtitle">Create drafts, generate grounded sections and keep citations attached to the prose.</div>
      </div>

      {draftsError && <div className="rc-error-card">Failed to load drafts</div>}

      <div className="rc-card">
        <div className="rc-card-title">Drafts</div>
        <div className="rc-row" style={{ alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div style={{ minWidth: 240 }}>
            <div className="rc-kicker">New draft title</div>
            <input className="rc-input" value={title} onChange={e => setTitle(e.target.value)} />
          </div>
          <button className="rc-btn rc-btn--primary" onClick={() => createMut.mutate()} disabled={busy}>Create draft</button>
          <button className="rc-btn" onClick={() => buildEvidenceMut.mutate()} disabled={busy}>
            {buildEvidenceMut.isPending ? 'Building...' : 'Build evidence table'}
          </button>
        </div>
      </div>

      <div className="rc-card">
        <div className="rc-card-title">Generate section</div>
        <div className="rc-row" style={{ alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div style={{ minWidth: 240 }}>
            <div className="rc-kicker">Draft</div>
            <select className="rc-input" value={selectedDraft} onChange={e => setSelectedDraft(e.target.value)}>
              <option value="">Select draft</option>
              {drafts.map(d => <option key={d.id} value={d.id}>{d.title} &middot; v{d.version}</option>)}
            </select>
          </div>
          <div style={{ minWidth: 240 }}>
            <div className="rc-kicker">Heading</div>
            <input className="rc-input" value={heading} onChange={e => setHeading(e.target.value)} />
          </div>
          <button className="rc-btn" onClick={() => generateMut.mutate()} disabled={busy || !selectedDraft}>
            {generateMut.isPending ? 'Generating...' : 'Generate'}
          </button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: 14 }} className="rc-grid2">
        {/* Draft contents */}
        <div className="rc-card">
          <div className="rc-card-title">Draft contents</div>

          {drafts.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '36px 16px' }}>
              <svg width="48" height="48" viewBox="0 0 48 48" fill="none" style={{ margin: '0 auto 12px', display: 'block' }}>
                <rect x="6" y="8" width="28" height="34" rx="4" fill="rgba(139,92,246,0.07)" stroke="rgba(139,92,246,0.2)" strokeWidth="1.5"/>
                <line x1="14" y1="17" x2="26" y2="17" stroke="rgba(139,92,246,0.35)" strokeWidth="1.5" strokeLinecap="round"/>
                <line x1="14" y1="23" x2="26" y2="23" stroke="rgba(139,92,246,0.35)" strokeWidth="1.5" strokeLinecap="round"/>
                <line x1="14" y1="29" x2="22" y2="29" stroke="rgba(139,92,246,0.2)" strokeWidth="1.5" strokeLinecap="round"/>
                <circle cx="36" cy="36" r="10" fill="var(--rc-surface)" stroke="rgba(139,92,246,0.3)" strokeWidth="1.5"/>
                <line x1="36" y1="31" x2="36" y2="41" stroke="rgba(139,92,246,0.6)" strokeWidth="2" strokeLinecap="round"/>
                <line x1="31" y1="36" x2="41" y2="36" stroke="rgba(139,92,246,0.6)" strokeWidth="2" strokeLinecap="round"/>
              </svg>
              <div style={{ fontWeight: 700, fontSize: 14, fontFamily: 'var(--font-display)', letterSpacing: '-0.02em', marginBottom: 4 }}>No drafts yet</div>
              <div className="rc-help" style={{ maxWidth: 280, margin: '0 auto' }}>
                Create a draft above and generate sections to get started.
              </div>
            </div>
          ) : null}

          {drafts.map(draft => (
            <div key={draft.id} style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 14 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 6 }}>
                <div style={{ fontWeight: 800 }}>{draft.title} &middot; {draft.status} &middot; v{draft.version}</div>
                <div className="rc-row" style={{ gap: 4 }}>
                  <button className="rc-btn" style={{ padding: '4px 10px', fontSize: 11 }} onClick={() => copyFullDraft(draft)}>Copy full draft</button>
                  <button className="rc-btn" style={{ padding: '4px 10px', fontSize: 11 }} onClick={() => exportHTML(draft)}>Export .html</button>
                </div>
              </div>

              {draft.sections.length === 0 && (
                <div className="rc-help">No sections yet. Use "Generate section" above to add content.</div>
              )}

              {draft.sections
                .sort((a, b) => a.position - b.position)
                .map(section => (
                <div key={section.id} className="rc-card" style={{ padding: 12 }}>
                  <div className="rc-kicker">{section.heading}</div>

                  {editingSection === section.id ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                      <textarea
                        className="rc-input"
                        style={{ minHeight: 120, width: '100%', fontSize: 13 }}
                        value={editContent}
                        onChange={e => setEditContent(e.target.value)}
                      />
                      <div className="rc-row" style={{ gap: 6 }}>
                        <button className="rc-btn rc-btn--primary" style={{ padding: '6px 12px', fontSize: 12 }} onClick={() => saveSectionMut.mutate({ draftId: draft.id, sectionId: section.id })} disabled={saveSectionMut.isPending}>Save</button>
                        <button className="rc-btn" style={{ padding: '6px 12px', fontSize: 12 }} onClick={() => setEditingSection(null)}>Cancel</button>
                      </div>
                    </div>
                  ) : (
                    <div
                      style={{ whiteSpace: 'pre-wrap', cursor: 'pointer', padding: '4px 0', borderRadius: 6 }}
                      onClick={() => startEdit(section)}
                      title="Click to edit"
                    >
                      {section.content || <span className="rc-muted">Empty section. Click to edit.</span>}
                    </div>
                  )}

                  <div className="rc-help" style={{ marginTop: 6 }}>
                    Citations: {section.citations.map(c => c.marker).join(', ') || 'none'}
                  </div>
                </div>
              ))}
            </div>
          ))}
        </div>

        {/* Evidence tables */}
        <div className="rc-card">
          <div className="rc-card-title">Evidence tables</div>
          {tables.length === 0 ? <div className="rc-muted">No evidence tables yet.</div> : null}
          {tables.map(table => (
            <div key={table.id} className="rc-card" style={{ padding: 12, marginBottom: 10 }}>
              <div style={{ fontWeight: 800 }}>{table.title}</div>
              <div className="rc-help">Rows: {table.table_json?.count ?? 0} &middot; confidence {table.confidence.toFixed(2)}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
