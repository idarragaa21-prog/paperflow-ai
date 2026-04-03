import { useCallback, useEffect, useState } from 'react';
import type { Draft, DraftSection } from '../types/api';
import { useParams, useSearchParams } from 'react-router-dom';
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
  const [searchParams] = useSearchParams();
  const paramStudies = searchParams.get('studies');
  const [extractionIds, setExtractionIds] = useState<string[]>(paramStudies ? paramStudies.split(',') : []);

  const [title, setTitle] = useState('Narrative synthesis');
  const [heading, setHeading] = useState('Introduction');
  const [selectedDraft, setSelectedDraft] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);

  // Inline editing state
  const [editingSection, setEditingSection] = useState<string | null>(null);
  const [editContent, setEditContent] = useState('');

  const load = useCallback(async () => {
    if (!projectId) return;
    try {
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
      await api.post(`/drafts/${selectedDraft}/generate-section`, { heading, paper_ids: [], extraction_record_ids: extractionIds });
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
          <button className="rc-btn" onClick={syncReferences} disabled={busy}>🔗 Sincronizar Referencias</button>
        </div>
      </div>

      <div className="rc-card">
        <div className="rc-card-title">Generate section</div>
        <div className="rc-help" style={{ marginBottom: 12 }}>
          La IA redactará la sección basándose en las tablas de evidencia disponibles y las referencias sincronizadas en el proyecto.
          {extractionIds.length > 0 && (
            <div style={{ marginTop: 6, padding: '6px 12px', background: 'rgba(79, 70, 229, 0.1)', color: '#4f46e5', borderRadius: 6, fontWeight: 600, display: 'inline-block' }}>
              Incluyendo contexto de {extractionIds.length} estudio(s) pre-seleccionado(s).
            </div>
          )}
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
        <div className="rc-editor-canvas" style={{ padding: '40px 60px' }}>
          {drafts.length === 0 ? (
            <EmptyState variant="notes" title="No drafts yet" description="Create a draft above and generate AI-powered sections from your paper references." />
          ) : null}

          {drafts.map(draft => (
            <div key={draft.id} style={{ display: 'flex', flexDirection: 'column', gap: 20, marginBottom: 14 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 12, borderBottom: '1px solid var(--rc-border)', paddingBottom: 20 }}>
                <div>
                  <h1 style={{ fontSize: 32, fontWeight: 900, margin: 0, fontFamily: 'var(--font-display)', letterSpacing: '-0.03em', lineHeight: 1.1 }}>{draft.title}</h1>
                  <div style={{ color: 'var(--rc-muted)', fontSize: 13, marginTop: 8 }}>
                    <span className="rc-status-dot rc-status-dot--ready" style={{ marginRight: 12 }}><span className="rc-status-dot__dot"></span>{draft.status}</span>
                    Version {draft.version}
                  </div>
                </div>
                <div className="rc-row" style={{ gap: 8 }}>
                  <button className="rc-btn rc-btn--ghost rc-btn--sm" onClick={() => copyFullDraft(draft)}>Copy Markdown</button>
                  <button className="rc-btn rc-btn--sm" onClick={() => exportHTML(draft)}>Export HTML</button>
                </div>
              </div>

              {draft.sections.length === 0 && (
                <div className="rc-help" style={{ textAlign: 'center', margin: '40px 0', fontSize: 14 }}>
                  This draft is currently empty. Use the "Generate section" tools above to add content.
                </div>
              )}

              {draft.sections
                .sort((a, b) => a.position - b.position)
                .map(section => (
                <div key={section.id} style={{ position: 'relative', padding: '16px 0' }} className="rc-editor-section">
                  <h2 style={{ fontSize: 22, fontWeight: 800, margin: '0 0 12px 0', fontFamily: 'var(--font-display)' }}>{section.heading}</h2>

                  {editingSection === section.id ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                      <textarea
                        className="rc-editor-textarea"
                        value={editContent}
                        onChange={e => setEditContent(e.target.value)}
                        placeholder="Start writing..."
                        autoFocus
                      />
                      <div className="rc-row" style={{ gap: 8, marginTop: 12 }}>
                        <button className="rc-btn rc-btn--primary rc-btn--sm" onClick={() => saveEdit(draft.id, section.id)}>Save Changes</button>
                        <button className="rc-btn rc-btn--ghost rc-btn--sm" onClick={() => setEditingSection(null)}>Cancel</button>
                      </div>
                    </div>
                  ) : (
                    <div
                      style={{ 
                        whiteSpace: 'pre-wrap', 
                        cursor: 'text', 
                        fontSize: 17, 
                        lineHeight: 1.8, 
                        fontFamily: 'Georgia, serif',
                        color: 'var(--rc-text)'
                      }}
                      onClick={() => startEdit(section)}
                      title="Click to edit section"
                    >
                      {section.content || <span className="rc-muted" style={{ fontStyle: 'italic' }}>Empty section. Click to start typing.</span>}
                    </div>
                  )}

                  {section.citations.length > 0 && (
                    <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px dashed var(--rc-border)' }}>
                      {section.citations.map(c => (
                         <span key={c.marker} className="rc-cite-chip" title="View Source">
                           {c.marker}
                         </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ))}
        </div>

        <div className="rc-scroll-y" style={{ display: 'flex', flexDirection: 'column', gap: 12, position: 'sticky', top: 18, maxHeight: 'calc(100vh - 120px)' }}>
          <div className="rc-card rc-glass" style={{ border: '1px solid rgba(79, 70, 229, 0.15)', boxShadow: '0 8px 30px rgba(0,0,0,0.04)' }}>
            <div className="rc-card-title" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              📚 Evidence Tables
            </div>
            <div className="rc-help" style={{ marginBottom: 16, lineHeight: 1.5 }}>
              Use these available matrices to ground your AI generation. Evidence stays visible while you review the draft.
            </div>
            {tables.length === 0 ? <div className="rc-muted" style={{ fontSize: 13 }}>No active evidence tables.</div> : null}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {tables.map(table => (
                <div key={table.id} className="rc-card" style={{ padding: '12px 14px', background: 'var(--rc-surface-2)', border: 'none' }}>
                  <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 4 }}>{table.title}</div>
                  <div className="rc-row" style={{ justifyContent: 'space-between' }}>
                    <span className="rc-help">Entries: {table.table_json?.count ?? 0}</span>
                    <span className="rc-badge rc-tag--success" style={{ padding: '2px 6px', fontSize: 10 }}>
                      {(table.confidence * 100).toFixed(0)}% Match
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
      )}
    </div>
  );
}
