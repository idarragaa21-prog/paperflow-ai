import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../services/api';

type Draft = {
  id: string;
  title: string;
  status: string;
  version: number;
  sections: Array<{
    id: string;
    heading: string;
    content: string;
    citations: Array<{ id: string; marker: string }>;
  }>;
};

type EvidenceTable = {
  id: string;
  title: string;
  table_json: { count?: number };
  confidence: number;
};

export default function DraftsPage() {
  const { projectId } = useParams();
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [tables, setTables] = useState<EvidenceTable[]>([]);
  const [title, setTitle] = useState('Narrative synthesis');
  const [heading, setHeading] = useState('Introduction');
  const [selectedDraft, setSelectedDraft] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

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
    setBusy(true);
    setError(null);
    try {
      const response = await api.post('/drafts', { project_id: projectId, title });
      const draft = response.data as Draft;
      setSelectedDraft(draft.id);
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to create draft');
    } finally {
      setBusy(false);
    }
  }

  async function generateSection() {
    if (!selectedDraft || !heading.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await api.post(`/drafts/${selectedDraft}/generate-section`, { heading, paper_ids: [], extraction_record_ids: [] });
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to generate section');
    } finally {
      setBusy(false);
    }
  }

  async function buildEvidence() {
    if (!projectId) return;
    setBusy(true);
    setError(null);
    try {
      await api.get('/evidence/tables', { params: { project_id: projectId, build: true } });
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to build evidence table');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div>
        <h1 className="rc-page-title">Writing Studio</h1>
        <div className="rc-subtitle">Create drafts, generate grounded sections and keep citations attached to the prose.</div>
      </div>

      {error ? <div className="rc-error">{error}</div> : null}

      <div className="rc-card">
        <div className="rc-card-title">Drafts</div>
        <div className="rc-row" style={{ alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div style={{ minWidth: 240 }}>
            <div className="rc-kicker">New draft title</div>
            <input data-testid="draft-title-input" className="rc-input" value={title} onChange={(e) => setTitle(e.target.value)} />
          </div>
          <button data-testid="draft-create-button" className="rc-btn rc-btn--primary" onClick={createDraft} disabled={busy}>Create draft</button>
          <button data-testid="draft-build-evidence" className="rc-btn" onClick={buildEvidence} disabled={busy}>Build evidence table</button>
        </div>
      </div>

      <div className="rc-card">
        <div className="rc-card-title">Generate section</div>
        <div className="rc-row" style={{ alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div style={{ minWidth: 240 }}>
            <div className="rc-kicker">Draft</div>
            <select data-testid="draft-select" className="rc-input" value={selectedDraft} onChange={(e) => setSelectedDraft(e.target.value)}>
              <option value="">Select draft</option>
              {drafts.map((draft) => (
                <option key={draft.id} value={draft.id}>
                  {draft.title} · v{draft.version}
                </option>
              ))}
            </select>
          </div>
          <div style={{ minWidth: 240 }}>
            <div className="rc-kicker">Heading</div>
            <input data-testid="draft-heading-input" className="rc-input" value={heading} onChange={(e) => setHeading(e.target.value)} />
          </div>
          <button data-testid="draft-generate-button" className="rc-btn" onClick={generateSection} disabled={busy || !selectedDraft}>Generate</button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: 14 }}>
        <div className="rc-card">
          <div className="rc-card-title">Draft contents</div>
          {drafts.length === 0 ? <div className="rc-muted">No drafts yet.</div> : null}
          {drafts.map((draft) => (
            <div key={draft.id} style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 14 }}>
              <div style={{ fontWeight: 800 }}>{draft.title} · {draft.status} · v{draft.version}</div>
              {draft.sections.map((section) => (
                <div key={section.id} className="rc-card" style={{ padding: 12 }}>
                  <div className="rc-kicker">{section.heading}</div>
                  <div style={{ whiteSpace: 'pre-wrap' }}>{section.content}</div>
                  <div className="rc-help">Citations: {section.citations.map((citation) => citation.marker).join(', ') || 'none'}</div>
                </div>
              ))}
            </div>
          ))}
        </div>

        <div className="rc-card">
          <div className="rc-card-title">Evidence tables</div>
          {tables.length === 0 ? <div className="rc-muted">No evidence tables yet.</div> : null}
          {tables.map((table) => (
            <div key={table.id} className="rc-card" style={{ padding: 12, marginBottom: 10 }}>
              <div style={{ fontWeight: 800 }}>{table.title}</div>
              <div className="rc-help">Rows: {table.table_json?.count ?? 0} · confidence {table.confidence.toFixed(2)}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
