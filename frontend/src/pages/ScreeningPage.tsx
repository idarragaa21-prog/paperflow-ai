import { useEffect, useState } from 'react';
import EmptyState from '../ui/EmptyState/EmptyState';
import { useParams } from 'react-router-dom';
import { api } from '../services/api';

type Batch = { id: string; title: string; stage: string; status: string };
type Reason = { id: string; code: string; label: string };
type Paper = { id: string; title: string };

export default function ScreeningPage() {
  const { projectId } = useParams();
  const [batches, setBatches] = useState<Batch[]>([]);
  const [reasons, setReasons] = useState<Reason[]>([]);
  const [papers, setPapers] = useState<Paper[]>([]);
  const [prisma, setPrisma] = useState<Record<string, number>>({});
  const [title, setTitle] = useState('Main screening batch');
  const [selectedBatch, setSelectedBatch] = useState('');
  const [selectedPaper, setSelectedPaper] = useState('');
  const [decision, setDecision] = useState('include');
  const [reasonLabel, setReasonLabel] = useState('Wrong population');
  const [error, setError] = useState<string | null>(null);

  async function load() {
    if (!projectId) return;
    const [batchResponse, reasonResponse, paperResponse, prismaResponse] = await Promise.all([
      api.get('/screening/batches', { params: { project_id: projectId } }),
      api.get('/screening/reasons', { params: { project_id: projectId } }),
      api.get(`/projects/${projectId}/library`),
      api.get('/screening/prisma', { params: { project_id: projectId } }).catch(() => ({ data: { counts: {} } })),
    ]);
    const nextBatches = batchResponse.data as Batch[];
    setBatches(nextBatches);
    setReasons(reasonResponse.data as Reason[]);
    setPapers(paperResponse.data as Paper[]);
    setPrisma((prismaResponse.data?.counts || {}) as Record<string, number>);
    if (!selectedBatch && nextBatches[0]) setSelectedBatch(nextBatches[0].id);
    if (!selectedPaper && (paperResponse.data as Paper[])[0]) setSelectedPaper((paperResponse.data as Paper[])[0].id);
  }

  useEffect(() => {
    load().catch((e: any) => setError(e?.response?.data?.detail || 'Failed to load screening workspace'));
  }, [projectId]);

  async function createBatch() {
    if (!projectId) return;
    try {
      await api.post('/screening/batches', { project_id: projectId, title, stage: 'title_abstract' });
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to create screening batch');
    }
  }

  async function createReason() {
    if (!projectId) return;
    try {
      await api.post('/screening/reasons', { project_id: projectId, code: reasonLabel.toLowerCase().replace(/\s+/g, '_'), label: reasonLabel });
      setReasonLabel('');
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to create reason');
    }
  }

  async function saveDecision() {
    if (!selectedBatch || !selectedPaper) return;
    try {
      await api.post('/screening/decisions', {
        batch_id: selectedBatch,
        paper_id: selectedPaper,
        decision,
        stage: 'title_abstract',
        reason_id: decision === 'exclude' ? reasons[0]?.id || null : null,
      });
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to save screening decision');
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div>
        <h1 className="rc-page-title">Screening</h1>
        <div className="rc-subtitle">Title/abstract and full-text screening with auditable reasons and lightweight PRISMA counts.</div>
      </div>

      {error ? <div className="rc-error">{error}</div> : null}

      <div className="rc-card">
        <div className="rc-card-title">Setup</div>
        <div className="rc-row" style={{ alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div style={{ minWidth: 220 }}>
            <div className="rc-kicker">Batch title</div>
            <input className="rc-input" value={title} onChange={(e) => setTitle(e.target.value)} />
          </div>
          <button className="rc-btn" onClick={createBatch}>Create batch</button>
          <div style={{ minWidth: 220 }}>
            <div className="rc-kicker">Exclusion reason</div>
            <input className="rc-input" value={reasonLabel} onChange={(e) => setReasonLabel(e.target.value)} />
          </div>
          <button className="rc-btn" onClick={createReason}>Add reason</button>
        </div>
      </div>

      <div className="rc-card">
        <div className="rc-card-title">Decision</div>
        <div className="rc-row" style={{ alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div style={{ minWidth: 220 }}>
            <div className="rc-kicker">Batch</div>
            <select className="rc-input" value={selectedBatch} onChange={(e) => setSelectedBatch(e.target.value)}>
              <option value="">Select batch</option>
              {batches.map((batch) => (
                <option key={batch.id} value={batch.id}>
                  {batch.title} · {batch.stage}
                </option>
              ))}
            </select>
          </div>
          <div style={{ minWidth: 240 }}>
            <div className="rc-kicker">Paper</div>
            <select className="rc-input" value={selectedPaper} onChange={(e) => setSelectedPaper(e.target.value)}>
              <option value="">Select paper</option>
              {papers.map((paper) => (
                <option key={paper.id} value={paper.id}>{paper.title}</option>
              ))}
            </select>
          </div>
          <div style={{ minWidth: 160 }}>
            <div className="rc-kicker">Decision</div>
            <select className="rc-input" value={decision} onChange={(e) => setDecision(e.target.value)}>
              <option value="include">Include</option>
              <option value="exclude">Exclude</option>
              <option value="maybe">Maybe</option>
            </select>
          </div>
          <button className="rc-btn rc-btn--primary" onClick={saveDecision}>Save decision</button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
        <div className="rc-card">
          <div className="rc-card-title">Batches</div>
          {batches.length === 0 ? <EmptyState title="No hay batches de screening" description="Crea tu primer batch para empezar el cribado PRISMA de títulos y abstracts." /> : null}
          {batches.map((batch) => (
            <div key={batch.id} className="rc-help">{batch.title} · {batch.stage} · {batch.status}</div>
          ))}
        </div>

        <div className="rc-card">
          <div className="rc-card-title">PRISMA counts</div>
          {Object.keys(prisma).length === 0 ? <div className="rc-muted">No counts yet.</div> : null}
          {Object.entries(prisma).map(([key, value]) => (
            <div key={key} className="rc-help">{key}: {value}</div>
          ))}
        </div>
      </div>
    </div>
  );
}
