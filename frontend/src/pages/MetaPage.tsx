import { useMemo, useState } from 'react';
import type { StudyRow } from '../types/api';
import { useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import StudyViewer from '../components/meta/StudyViewer';
import { downloadBlob } from '../components/meta/exportUtils';
import { api } from '../services/api';

type BatchRow = {
  id: string;
  title?: string | null;
  status: string;
  created_at: string;
};

type ItemRow = {
  id: string;
  paper_id: string;
  paper_title?: string;
  paper_filename?: string;
  status: string;
  error_message?: string | null;
  result_summary?: any;
  created_at?: string | null;
  updated_at?: string | null;
};

type ExportRow = {
  id: string;
  project_id: string;
  batch_id?: string | null;
  filename: string;
  created_at: string;
};

type JobStatus = { status: string; progress: number; error?: string | null };

export default function MetaPage() {
  const { projectId } = useParams();
  const qc = useQueryClient();

  const [selectedBatchId, setSelectedBatchId] = useState<string | null>(null);
  const [selectedStudyId, setSelectedStudyId] = useState<string | null>(null);
  const [exportJobId, setExportJobId] = useState<string | null>(null);
  const [files, setFiles] = useState<FileList | null>(null);
  const [title, setTitle] = useState('');

  // ── Batches ───────────────────────────────────────────────────────────────
  const { data: batches = [], isLoading: batchesLoading, error: batchesError } = useQuery<BatchRow[]>({
    queryKey: ['meta-batches', projectId],
    queryFn: async () => {
      const r = await api.get(`/meta/batches?project_id=${projectId}`);
      return r.data as BatchRow[];
    },
    enabled: !!projectId,
  });

  // ── Items for selected batch (with auto-refresh while running) ────────────
  const { data: items = [] } = useQuery<ItemRow[]>({
    queryKey: ['meta-items', selectedBatchId],
    queryFn: async () => {
      const r = await api.get(`/meta/batches/${selectedBatchId}/items`);
      return r.data as ItemRow[];
    },
    enabled: !!selectedBatchId,
    refetchInterval: (query) => {
      const data = query.state.data ?? [];
      const hasRunning = data.some((it) => ['queued', 'started'].includes(it.status));
      return hasRunning ? 4000 : false;
    },
  });

  // ── Studies ───────────────────────────────────────────────────────────────
  const { data: studies = [] } = useQuery<StudyRow[]>({
    queryKey: ['meta-studies', projectId, selectedBatchId],
    queryFn: async () => {
      const q = selectedBatchId ? `&batch_id=${selectedBatchId}` : '';
      const r = await api.get(`/meta/studies?project_id=${projectId}${q}`);
      return r.data as StudyRow[];
    },
    enabled: !!projectId,
  });

  // ── Exports ───────────────────────────────────────────────────────────────
  const { data: exportsList = [] } = useQuery<ExportRow[]>({
    queryKey: ['meta-exports', projectId, selectedBatchId],
    queryFn: async () => {
      const q = selectedBatchId ? `&batch_id=${selectedBatchId}` : '';
      const r = await api.get(`/meta/exports?project_id=${projectId}${q}`);
      return r.data as ExportRow[];
    },
    enabled: !!projectId,
  });

  // ── Export job polling ────────────────────────────────────────────────────
  const { data: exportJobData } = useQuery<JobStatus>({
    queryKey: ['job', exportJobId],
    queryFn: async () => {
      const r = await api.get(`/jobs/${exportJobId}`);
      const d = r.data as any;
      return { status: String(d?.status || 'unknown'), progress: Number(d?.progress_percent || 0), error: d?.error ?? null };
    },
    enabled: !!exportJobId,
    refetchInterval: (query) => {
      const s = query.state.data?.status;
      if (s === 'completed') {
        qc.invalidateQueries({ queryKey: ['meta-exports', projectId, selectedBatchId] });
        setExportJobId(null);
        return false;
      }
      return s === 'failed' ? false : 4000;
    },
  });

  function invalidate() {
    qc.invalidateQueries({ queryKey: ['meta-batches', projectId] });
    qc.invalidateQueries({ queryKey: ['meta-studies', projectId, selectedBatchId] });
    qc.invalidateQueries({ queryKey: ['meta-exports', projectId, selectedBatchId] });
  }

  // ── Create batch ──────────────────────────────────────────────────────────
  const createMut = useMutation({
    mutationFn: async () => {
      if (!files || files.length === 0) throw new Error('Select at least 1 PDF');
      const form = new FormData();
      form.append('project_id', projectId!);
      if (title.trim()) form.append('title', title.trim());
      Array.from(files).forEach((f) => form.append('files', f));
      return api.post('/meta/batches', form, { headers: { 'Content-Type': 'multipart/form-data' } });
    },
    onSuccess: (r) => {
      const batchId = r.data?.batch_id as string;
      setFiles(null);
      setTitle('');
      invalidate();
      if (batchId) setSelectedBatchId(batchId);
    },
    onError: () => {},
  });

  // ── Retry item ────────────────────────────────────────────────────────────
  const retryMut = useMutation({
    mutationFn: (itemId: string) => api.post(`/meta/items/${itemId}/retry`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['meta-items', selectedBatchId] }),
    onError: () => {},
  });

  // ── Export Excel ──────────────────────────────────────────────────────────
  const exportMut = useMutation({
    mutationFn: () => api.post('/meta/export', { project_id: projectId, batch_id: selectedBatchId }),
    onSuccess: (r) => {
      const jid = r.data?.job_id as string | undefined;
      if (jid) setExportJobId(jid);
    },
    onError: () => {},
  });

  const runningItems = useMemo(() => items.filter((it) => ['queued', 'started'].includes(it.status)), [items]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div>
        <h1 className="rc-page-title">Extraction Workspace</h1>
        <div className="rc-subtitle">Batch upload PDFs, extract structured study data, review effect sizes and export reusable datasets.</div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '380px 1fr', gap: 12 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div className="rc-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
              <div style={{ fontWeight: 900 }}>Batches</div>
              <button className="rc-btn" onClick={invalidate} disabled={batchesLoading}>Refresh</button>
            </div>
            {batchesError ? <div className="rc-error-card" style={{ marginTop: 8 }}>Failed to load batches</div> : null}
            {createMut.isSuccess ? (
              <div className="rc-badge rc-badge--success" style={{ justifyContent: 'flex-start', borderRadius: 12, padding: 10, marginTop: 8 }}>
                Batch created successfully.
              </div>
            ) : null}
            {createMut.isError ? <div className="rc-error" style={{ marginTop: 8 }}>{(createMut.error as any)?.message}</div> : null}
            <div style={{ height: 10 }} />
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {batches.length === 0 ? <div className="rc-muted">No batches yet.</div> : null}
              {batches.map((b) => (
                <button
                  key={b.id}
                  onClick={() => setSelectedBatchId(b.id)}
                  className="rc-btn"
                  style={{ textAlign: 'left', padding: 12, borderColor: b.id === selectedBatchId ? 'rgba(79,70,229,0.35)' : undefined, background: b.id === selectedBatchId ? 'rgba(79,70,229,0.08)' : undefined }}
                >
                  <div style={{ fontWeight: 850 }}>{b.title || '(untitled batch)'}</div>
                  <div className="rc-help">{b.status}</div>
                </button>
              ))}
            </div>
            <div style={{ height: 10 }} />
            <button className="rc-btn rc-btn--ghost" onClick={() => setSelectedBatchId(null)} disabled={!selectedBatchId}>
              Clear batch filter
            </button>
          </div>

          <div className="rc-card">
            <div className="rc-card-title">New batch</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <div>
                <div className="rc-kicker">Title (optional)</div>
                <input className="rc-input" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. ACL graft meta-analysis" />
              </div>
              <div>
                <div className="rc-kicker">PDF files</div>
                <input type="file" multiple accept="application/pdf" onChange={(e) => setFiles(e.target.files)} />
                <div className="rc-help" style={{ marginTop: 6 }}>Extraction runs async (Redis required). Check Jobs for progress.</div>
              </div>
              <button className="rc-btn rc-btn--primary" disabled={createMut.isPending} onClick={() => createMut.mutate()}>
                {createMut.isPending ? 'Creating…' : 'Create + extract'}
              </button>
            </div>
          </div>

          <div className="rc-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'center' }}>
              <div className="rc-card-title" style={{ marginBottom: 0 }}>Exports</div>
              <button className="rc-btn" onClick={() => qc.invalidateQueries({ queryKey: ['meta-exports', projectId, selectedBatchId] })}>Refresh</button>
            </div>
            <div style={{ height: 10 }} />
            <button className="rc-btn rc-btn--primary" onClick={() => exportMut.mutate()} disabled={exportMut.isPending || !!exportJobId}>
              {exportJobId ? 'Exporting…' : 'Export Excel'}
            </button>
            {exportJobData ? (
              <div className="rc-help" style={{ marginTop: 8 }}>
                export: {exportJobData.status} · {exportJobData.progress}%
                {exportJobData.error ? <span className="rc-error"> · {String(exportJobData.error)}</span> : null}
              </div>
            ) : null}
            <div style={{ height: 10 }} />
            {exportsList.length === 0 ? <div className="rc-muted">No exports yet.</div> : null}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {exportsList.map((ex) => (
                <div key={ex.id} className="rc-card" style={{ padding: 10, display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'center' }}>
                  <div className="rc-help" style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{ex.filename}</div>
                  <button className="rc-btn" onClick={async () => {
                    const r = await api.get(`/meta/exports/${ex.id}/download`, { responseType: 'blob' });
                    downloadBlob(r.data as Blob, ex.filename || 'meta_export.xlsx');
                  }}>Download</button>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div className="rc-card">
            {selectedBatchId ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'center' }}>
                  <div className="rc-card-title" style={{ marginBottom: 0 }}>Batch items</div>
                  {runningItems.length ? <div className="rc-help">Auto-refreshing…</div> : null}
                </div>
                {items.length === 0 ? <div className="rc-muted">No items.</div> : null}
                {items.map((it) => (
                  <div key={it.id} className="rc-card" style={{ padding: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'center' }}>
                      <div style={{ fontWeight: 850 }}>Item</div>
                      <span className={it.status === 'completed' ? 'rc-badge rc-badge--success' : it.status === 'failed' ? 'rc-badge rc-badge--danger' : 'rc-badge rc-badge--info'}>{it.status}</span>
                    </div>
                    <div className="rc-help">
                      {it.paper_title ? <span style={{ fontWeight: 800 }}>{it.paper_title}</span> : null}
                      {it.paper_filename ? <span style={{ marginLeft: 8 }}>{it.paper_filename}</span> : null}
                    </div>
                    <div className="rc-help" style={{ opacity: 0.6 }}>paper_id: {it.paper_id}</div>
                    {it.error_message ? <div className="rc-error" style={{ fontSize: 12 }}>{it.error_message}</div> : null}
                    <div className="rc-row">
                      <button className="rc-btn" onClick={() => retryMut.mutate(it.id)} disabled={['queued', 'started'].includes(it.status) || retryMut.isPending}>
                        Retry
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="rc-muted">Select a batch to view items (optional).</div>
            )}
          </div>

          <div className="rc-card">
            <div style={{ display: 'grid', gridTemplateColumns: '380px 1fr', gap: 12 }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div className="rc-card-title" style={{ marginBottom: 0 }}>Studies</div>
                  <button className="rc-btn" onClick={() => qc.invalidateQueries({ queryKey: ['meta-studies', projectId, selectedBatchId] })}>Refresh</button>
                </div>
                <div style={{ height: 10 }} />
                {studies.length === 0 ? <div className="rc-muted">No studies (yet).</div> : null}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 460, overflow: 'auto' }}>
                  {studies.map((s) => (
                    <button
                      key={s.id}
                      onClick={() => setSelectedStudyId(s.id)}
                      className="rc-btn"
                      style={{ textAlign: 'left', padding: 12, borderColor: s.id === selectedStudyId ? 'rgba(79,70,229,0.35)' : undefined, background: s.id === selectedStudyId ? 'rgba(79,70,229,0.08)' : undefined }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'center' }}>
                        <div style={{ fontWeight: 850, fontSize: 12, flex: 1 }}>{s.paper_title || `Study ${s.id}`}</div>
                        {s.rob_auto_generated ? <span className="rc-badge">ROB auto</span> : null}
                      </div>
                      {s.paper_filename ? <div className="rc-help">{s.paper_filename}</div> : null}
                      <div className="rc-help">
                        v{s.version} · conf {s.extraction_confidence} {s.batch_id ? '· batch' : ''}
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              <div>
                {selectedStudyId ? (
                  <StudyViewer studyId={selectedStudyId} onSelectStudyId={setSelectedStudyId} />
                ) : (
                  <div className="rc-muted">Select a study to edit effect sizes (inline grid).</div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
