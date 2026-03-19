import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../services/api';
import { useToast } from '../ui/Toast/ToastProvider';

type DraftCitation = {
  id: string;
  marker: string;
  quoted_text?: string | null;
};

type DraftSection = {
  id: string;
  heading: string;
  content: string;
  position: number;
  generated_with_model?: string | null;
  confidence?: number;
  citations: DraftCitation[];
};

type Draft = {
  id: string;
  title: string;
  status: string;
  version: number;
  sections: DraftSection[];
};

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

  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [tables, setTables] = useState<EvidenceTable[]>([]);
  const [title, setTitle] = useState('Narrative synthesis');
  const [heading, setHeading] = useState('Introduction');
  const [selectedDraft, setSelectedDraft] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Inline editing state
  const [editingSection, setEditingSection] = useState<string | null>(null);
  const [editContent, setEditContent] = useState('');

  async function load() {
    if (!projectId) return;
    const [draftResponse, evidenceResponse] = await Promise.all([
      api.get('/drafts', { params: { project_id: projectId } }),
      api.get('/evidence/tables', { params: { project_id: projectId } }),
    ]);
    const nextDrafts = draftResponse.data as Draft[];
    setDrafts(nextDrafts);
    setTables(evidenceResponse.data as EvidenceTable[]);
    if (!selectedDraft && nextDrafts[0]) {
      setSelectedDraft(nextDrafts[0].id);
    }
  }

  useEffect(() => {
    load().catch((e: any) => setError(e?.response?.data?.detail || 'Failed to load drafts'));
  }, [projectId]);

  async function createDraft() {
    if (!projectId || !title.trim()) return;
    setBusy(true); setError(null);
    try {
      const response = await api.post('/drafts', { project_id: projectId, title });
      const draft = response.data as Draft;
      setSelectedDraft(draft.id);
      await load();
    } catch (e: any) { setError(e?.response?.data?.detail || 'Failed to create draft'); }
    finally { setBusy(false); }
  }

  async function generateSection() {
    if (!selectedDraft || !heading.trim()) return;
    setBusy(true); setError(null);
    try {
      await api.post(`/drafts/${selectedDraft}/generate-section`, { heading, paper_ids: [], extraction_record_ids: [] });
      await load();
    } catch (e: any) { setError(e?.response?.data?.detail || 'Failed to generate section'); }
    finally { setBusy(false); }
  }

  async function buildEvidence() {
    if (!projectId) return;
    setBusy(true); setError(null);
    try {
      await api.get('/evidence/tables', { params: { project_id: projectId, build: true } });
      await load();
    } catch (e: any) { setError(e?.response?.data?.detail || 'Failed to build evidence table'); }
    finally { setBusy(false); }
  }

  // Inline edit
  function startEdit(section: DraftSection) {
    setEditingSection(section.id);
    setEditContent(section.content);
  }

  async function saveEdit(draftId: string, sectionId: string) {
    setError(null);
    try {
      await api.patch(`/drafts/${draftId}/sections/${sectionId}`, { content: editContent });
      setEditingSection(null);
      toast.success('Saved', 'Section content updated.');
      await load();
    } catch (e: any) { setError(e?.response?.data?.detail || 'Failed to save section'); }
  }

  // Copy full draft
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

  // Export HTML
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

      {error && <div className="rc-error">{error}</div>}

      <div className="rc-card">
        <div className="rc-card-title">Drafts</div>
        <div className="rc-row" style={{ alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div style={{ minWidth: 240 }}>
            <div className="rc-kicker">New draft title</div>
            <input className="rc-input" value={title} onChange={e => setTitle(e.target.value)} />
          </div>
          <button className="rc-btn rc-btn--primary" onClick={createDraft} disabled={busy}>Create draft</button>
          <button className="rc-btn" onClick={buildEvidence} disabled={busy}>Build evidence table</button>
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
          <button className="rc-btn" onClick={generateSection} disabled={busy || !selectedDraft}>Generate</button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: 14 }} className="rc-grid2">
        {/* Draft contents */}
        <div className="rc-card">
          <div className="rc-card-title">Draft contents</div>

          {drafts.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 28 }}>
              <div style={{ fontSize: 28, marginBottom: 8 }}>{'\u270D\uFE0F'}</div>
              <div style={{ fontWeight: 800, marginBottom: 4 }}>No drafts yet</div>
              <div className="rc-help" style={{ maxWidth: 320, margin: '0 auto' }}>
                Drafts are generated with AI from references extracted from your papers.
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
                        <button className="rc-btn rc-btn--primary" style={{ padding: '6px 12px', fontSize: 12 }} onClick={() => saveEdit(draft.id, section.id)}>Save</button>
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
