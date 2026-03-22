import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';

type Batch = { id: string; title: string; stage: string; status: string };
type Reason = { id: string; code: string; label: string };
type Paper = { id: string; title: string };

type ScreeningData = {
  batches: Batch[];
  reasons: Reason[];
  papers: Paper[];
  prisma: Record<string, number>;
};

export default function ScreeningPage() {
  const { projectId } = useParams();
  const qc = useQueryClient();

  const [title, setTitle] = useState('Main screening batch');
  const [selectedBatch, setSelectedBatch] = useState('');
  const [selectedPaper, setSelectedPaper] = useState('');
  const [decision, setDecision] = useState('include');
  const [reasonLabel, setReasonLabel] = useState('Wrong population');

  const { data, isError } = useQuery<ScreeningData>({
    queryKey: ['screening', projectId],
    queryFn: async () => {
      const [batchRes, reasonRes, paperRes, prismaRes] = await Promise.all([
        api.get('/screening/batches', { params: { project_id: projectId } }),
        api.get('/screening/reasons', { params: { project_id: projectId } }),
        api.get(`/projects/${projectId}/library`),
        api.get('/screening/prisma', { params: { project_id: projectId } }).catch(() => ({ data: { counts: {} } })),
      ]);
      const batches = batchRes.data as Batch[];
      const papers = paperRes.data as Paper[];
      if (!selectedBatch && batches[0]) setSelectedBatch(batches[0].id);
      if (!selectedPaper && papers[0]) setSelectedPaper(papers[0].id);
      return {
        batches,
        reasons: reasonRes.data as Reason[],
        papers,
        prisma: (prismaRes.data?.counts || {}) as Record<string, number>,
      };
    },
    enabled: !!projectId,
  });

  function invalidate() { qc.invalidateQueries({ queryKey: ['screening', projectId] }); }

  const batchMut = useMutation({
    mutationFn: () => api.post('/screening/batches', { project_id: projectId, title, stage: 'title_abstract' }),
    onSuccess: () => invalidate(),
    onError: () => {},
  });

  const reasonMut = useMutation({
    mutationFn: () => api.post('/screening/reasons', { project_id: projectId, code: reasonLabel.toLowerCase().replace(/\s+/g, '_'), label: reasonLabel }),
    onSuccess: () => { setReasonLabel(''); invalidate(); },
    onError: () => {},
  });

  const decisionMut = useMutation({
    mutationFn: () => api.post('/screening/decisions', {
      batch_id: selectedBatch,
      paper_id: selectedPaper,
      decision,
      stage: 'title_abstract',
      reason_id: decision === 'exclude' ? data?.reasons[0]?.id || null : null,
    }),
    onSuccess: () => invalidate(),
    onError: () => {},
  });

  const batches = data?.batches ?? [];
  const reasons = data?.reasons ?? [];
  const papers = data?.papers ?? [];
  const prisma = data?.prisma ?? {};

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div>
        <h1 className="rc-page-title">Screening</h1>
        <div className="rc-subtitle">Title/abstract and full-text screening with auditable reasons and lightweight PRISMA counts.</div>
      </div>

      {isError && <div className="rc-error-card">Failed to load screening workspace</div>}

      <div className="rc-card">
        <div className="rc-card-title">Setup</div>
        <div className="rc-row" style={{ alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div style={{ minWidth: 220 }}>
            <div className="rc-kicker">Batch title</div>
            <input className="rc-input" value={title} onChange={(e) => setTitle(e.target.value)} />
          </div>
          <button className="rc-btn" onClick={() => batchMut.mutate()} disabled={batchMut.isPending}>Create batch</button>
          <div style={{ minWidth: 220 }}>
            <div className="rc-kicker">Exclusion reason</div>
            <input className="rc-input" value={reasonLabel} onChange={(e) => setReasonLabel(e.target.value)} />
          </div>
          <button className="rc-btn" onClick={() => reasonMut.mutate()} disabled={reasonMut.isPending}>Add reason</button>
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
          <button className="rc-btn rc-btn--primary" onClick={() => decisionMut.mutate()} disabled={decisionMut.isPending || !selectedBatch || !selectedPaper}>
            {decisionMut.isPending ? 'Saving...' : 'Save decision'}
          </button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
        <div className="rc-card">
          <div className="rc-card-title">Batches</div>
          {batches.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '32px 16px' }}>
              <svg width="56" height="56" viewBox="0 0 56 56" fill="none" style={{ margin: '0 auto 10px', display: 'block' }}>
                <rect x="6" y="8" width="44" height="32" rx="4" fill="rgba(16,185,129,0.07)" stroke="rgba(16,185,129,0.2)" strokeWidth="1.5"/>
                <line x1="14" y1="18" x2="38" y2="18" stroke="rgba(16,185,129,0.3)" strokeWidth="1.5" strokeLinecap="round"/>
                <line x1="14" y1="24" x2="38" y2="24" stroke="rgba(16,185,129,0.2)" strokeWidth="1.5" strokeLinecap="round"/>
                <circle cx="42" cy="42" r="12" fill="var(--rc-surface)" stroke="rgba(16,185,129,0.3)" strokeWidth="1.5"/>
                <path d="M38 42h8M42 38v8" stroke="rgba(16,185,129,0.65)" strokeWidth="2" strokeLinecap="round"/>
              </svg>
              <div style={{ fontSize: 13, fontWeight: 600 }}>No screening batches yet</div>
              <div className="rc-help" style={{ marginTop: 3 }}>Create a batch to start screening papers</div>
            </div>
          ) : null}
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
