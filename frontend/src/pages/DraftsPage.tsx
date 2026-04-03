import { useCallback, useEffect, useState } from 'react';
import type { Draft, DraftSection } from '../types/api';
import { useParams } from 'react-router-dom';
import { api } from '../services/api';
import { useToast } from '../ui/Toast/ToastProvider';
import { EmptyState } from '../components/EmptyState';
import { InsightCard, PageHero } from '../components/WorkflowPrimitives';

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
  const [initialLoading, setInitialLoading] = useState(true);
  const [syncWarning, setSyncWarning] = useState(false);

  // Inline editing state
  const [editingSection, setEditingSection] = useState<string | null>(null);
  const [editContent, setEditContent] = useState('');

  const load = useCallback(async () => {
    if (!projectId) return;
    try {
      const [draftResponse, evidenceResponse, dashResponse, refResponse] = await Promise.all([
        api.get('/drafts', { params: { project_id: projectId } }),
        api.get('/evidence/tables', { params: { project_id: projectId } }),
        api.get(`/projects/${projectId}/dashboard`),
        api.get('/references', { params: { project_id: projectId } }),
      ]);
      const nextDrafts = draftResponse.data as Draft[];
      setDrafts(nextDrafts);
      setTables(evidenceResponse.data as EvidenceTable[]);

      const papersCount = dashResponse.data?.counts?.papers || 0;
      const referencesCount = refResponse.data?.length || 0;
      setSyncWarning(papersCount > referencesCount);

      if (!selectedDraft && nextDrafts[0]) {
        setSelectedDraft(nextDrafts[0].id);
      }
    } finally {
      setInitialLoading(false);
    }
  }, [projectId, selectedDraft]);

  useEffect(() => {
    load().catch((e: any) => setError(e?.response?.data?.detail || 'Failed to load drafts'));
  }, [load]);

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

  async function enhanceWithClinical() {
    if (!selectedDraft) return;
    setBusy(true); setError(null);
    try {
      await api.post(`/drafts/${selectedDraft}/enhance-with-clinical`);
      toast.success('Clinical evidence added', 'The draft was enriched with evidence-backed clinical synthesis.');
      await load();
    } catch (e: any) { setError(e?.response?.data?.detail || 'Failed to enrich draft with clinical evidence'); }
    finally { setBusy(false); }
  }

  async function syncReferences() {
    if (!projectId) return;
    setBusy(true); setError(null);
    try {
      const r = await api.post('/references/sync-from-library', null, { params: { project_id: projectId } });
      const created = (r.data as any)?.created || 0;
      toast.success('Referencias Sincronizadas', `Se sincronizaron ${created} referencias desde la Library.`);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Error sincronizando referencias.');
    } finally {
      setBusy(false);
    }
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

  const focusedDraft = drafts.find((draft) => draft.id === selectedDraft) || drafts[0] || null;
  const focusedSections = focusedDraft
    ? [...focusedDraft.sections].sort((a, b) => a.position - b.position)
    : [];

  return (
    <div className="rc-page-enter" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <PageHero
        eyebrow="Stage 5 · Writing"
        title="Turn extracted evidence into a manuscript canvas"
        subtitle="Writing should feel like one continuous workspace with structure, editable prose and evidence close at hand, not like a list of disconnected draft actions."
        metrics={[
          { label: 'drafts', value: drafts.length, tone: 'primary' },
          { label: 'sections', value: drafts.reduce((sum, draft) => sum + draft.sections.length, 0), tone: 'success' },
          { label: 'evidence tables', value: tables.length, tone: 'warning' },
        ]}
      />

      {error && <div className="rc-error">{error}</div>}

      {initialLoading && (
        <div className="rc-page-skeleton">
          <div className="rc-skeleton-card" style={{ height: 100 }}>
            {[70, 50, 40].map((w, i) => (
              <div key={i} className="rc-skeleton-line" style={{ width: `${w}%`, marginBottom: 8 }} />
            ))}
          </div>
          <div className="rc-skeleton-card" style={{ height: 200 }}>
            {[90, 80, 60, 70, 50].map((w, i) => (
              <div key={i} className="rc-skeleton-line" style={{ width: `${w}%`, marginBottom: 8 }} />
            ))}
          </div>
        </div>
      )}

      <div className="rc-card">
        <div className="rc-card-title">Drafts</div>
        <div className="rc-row" style={{ alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div style={{ minWidth: 240 }}>
            <div className="rc-kicker">New draft title</div>
            <input className="rc-input" data-testid="draft-title-input" value={title} onChange={e => setTitle(e.target.value)} />
          </div>
          <button className="rc-btn rc-btn--primary" data-testid="draft-create-button" onClick={createDraft} disabled={busy}>Create draft</button>
          <button className="rc-btn" data-testid="draft-build-evidence-button" onClick={buildEvidence} disabled={busy}>Build evidence table</button>
          <button className={`rc-btn ${syncWarning ? 'rc-btn--warning' : ''}`} style={syncWarning ? { background: 'rgba(245,158,11,0.1)', color: '#d97706', borderColor: 'rgba(245,158,11,0.4)' } : undefined} onClick={syncReferences} disabled={busy}>🔗 {syncWarning ? '⚠ Sincronizar Referencias Pendientes' : 'Sincronizar Referencias'}</button>
        </div>
      </div>

      <div className="rc-card">
        <div className="rc-card-title">Generate section</div>
        <div className="rc-help" style={{ marginBottom: 12 }}>
          La IA redactará la sección basándose en las tablas de evidencia disponibles y las referencias sincronizadas en el proyecto.
        </div>
        <div className="rc-row" style={{ alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div style={{ minWidth: 240 }}>
            <div className="rc-kicker">Draft</div>
            <select className="rc-input" data-testid="draft-select" value={selectedDraft} onChange={e => setSelectedDraft(e.target.value)}>
              <option value="">Select draft</option>
              {drafts.map(d => <option key={d.id} value={d.id}>{d.title} &middot; v{d.version}</option>)}
            </select>
          </div>
          <div style={{ minWidth: 240 }}>
            <div className="rc-kicker">Heading</div>
            <input className="rc-input" data-testid="draft-heading-input" value={heading} onChange={e => setHeading(e.target.value)} />
          </div>
          <button className="rc-btn" data-testid="draft-generate-button" onClick={generateSection} disabled={busy || !selectedDraft}>Generate</button>
          <button className="rc-btn rc-btn--primary" data-testid="draft-enhance-clinical-button" onClick={enhanceWithClinical} disabled={busy || !selectedDraft}>Enriquecer con evidencia</button>
        </div>
      </div>
      {!initialLoading && (
      <div className="rc-manuscript-grid">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <InsightCard
            eyebrow="Outline"
            title={focusedDraft ? focusedDraft.title : 'No draft selected'}
            body={focusedDraft
              ? 'Use the outline to navigate the manuscript structure and keep section generation intentional.'
              : 'Create a draft first so the writing canvas has structure.'}
            tone="primary"
          />
          <div className="rc-card">
            <div className="rc-card-title">Manuscript outline</div>
            {focusedSections.length === 0 ? <div className="rc-muted">No sections yet.</div> : null}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {focusedSections.map((section) => (
                <button
                  key={section.id}
                  className="rc-btn"
                  style={{ justifyContent: 'flex-start', textAlign: 'left', padding: '10px 12px' }}
                  onClick={() => startEdit(section)}
                >
                  <span style={{ fontWeight: 700 }}>{section.heading}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
        <div className="rc-card">
          <div className="rc-card-title">Draft contents</div>

          {drafts.length === 0 ? (
            <EmptyState variant="notes" title="No drafts yet" description="Create a draft above and generate AI-powered sections from your paper references." />
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

        <div className="rc-card">
          <div className="rc-card-title">Evidence tables</div>
          <div className="rc-help" style={{ marginBottom: 10 }}>
            Keep the evidence surface visible while you write so the draft stays grounded and citations remain actionable.
          </div>
          {tables.length === 0 ? <div className="rc-muted">No evidence tables yet.</div> : null}
          {tables.map(table => (
            <div key={table.id} className="rc-card" style={{ padding: 12, marginBottom: 10 }}>
              <div style={{ fontWeight: 800 }}>{table.title}</div>
              <div className="rc-help">Rows: {table.table_json?.count ?? 0} &middot; confidence {table.confidence.toFixed(2)}</div>
            </div>
          ))}
        </div>
      </div>
      )}
    </div>
  );
}
