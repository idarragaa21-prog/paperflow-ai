import { useEffect, useMemo, useState } from 'react';
import type { StudyRow } from '../types/api';
import { useParams } from 'react-router-dom';
import StudyViewer from '../components/meta/StudyViewer';
import { downloadBlob } from '../components/meta/exportUtils';
import { api } from '../services/api';
import { useJobPolling } from '../hooks/useJobPolling';
import { useToast } from '../ui/Toast/ToastProvider';

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

export default function MetaPage() {
  const { projectId } = useParams();
  const toast = useToast();

  const [batches, setBatches] = useState<BatchRow[]>([]);
  const [selectedBatchId, setSelectedBatchId] = useState<string | null>(null);
  const [items, setItems] = useState<ItemRow[]>([]);

  const [studies, setStudies] = useState<StudyRow[]>([]);
  const [selectedStudyId, setSelectedStudyId] = useState<string | null>(null);

  const [exportsList, setExportsList] = useState<ExportRow[]>([]);
  const [exportJobId, setExportJobId] = useState<string | null>(null);

  const [files, setFiles] = useState<FileList | null>(null);
  const [title, setTitle] = useState('');

  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const runningItems = useMemo(() => items.filter((it) => ['queued', 'started'].includes(it.status)), [items]);

  const exportJob = useJobPolling(exportJobId, {
    onCompleted: async () => {
      await loadExports();
      setExportJobId(null);
      toast.success('Export ready', 'Excel export is ready to download.');
    },
    onFailed: (s) => {
      setExportJobId(null);
      toast.error('Export failed', s.error || 'Excel export failed.');
    },
  });

  async function loadBatches() {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    // keep notice
    try {
      const r = await api.get(`/meta/batches?project_id=${projectId}`);
      setBatches(r.data as BatchRow[]);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to load batches');
    } finally {
      setLoading(false);
    }
  }

  async function loadItems(batchId: string) {
    setError(null);
    try {
      const r = await api.get(`/meta/batches/${batchId}/items`);
      setItems(r.data as ItemRow[]);
      setSelectedBatchId(batchId);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to load batch items');
    }
  }

  async function loadStudies() {
    if (!projectId) return;
    setError(null);
    try {
      const q = selectedBatchId ? `&batch_id=${selectedBatchId}` : '';
      const r = await api.get(`/meta/studies?project_id=${projectId}${q}`);
      setStudies(r.data as StudyRow[]);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to load studies');
    }
  }

  async function loadExports() {
    if (!projectId) return;
    setError(null);
    try {
      const q = selectedBatchId ? `&batch_id=${selectedBatchId}` : '';
      const r = await api.get(`/meta/exports?project_id=${projectId}${q}`);
      setExportsList(r.data as ExportRow[]);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to load exports');
    }
  }

  async function createBatch() {
    if (!projectId) return;
    if (!files || files.length === 0) {
      setError('Select at least 1 PDF');
      return;
    }

    setCreating(true);
    setError(null);
    setNotice(null);
    try {
      const form = new FormData();
      form.append('project_id', projectId);
      if (title.trim()) form.append('title', title.trim());
      Array.from(files).forEach((f) => form.append('files', f));

      const r = await api.post('/meta/batches', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      const batchId = r.data?.batch_id as string;
      setNotice(`Batch created: ${batchId} (job: ${r.data?.job_id})`);
      setFiles(null);
      setTitle('');
      await loadBatches();
      if (batchId) await loadItems(batchId);
      await loadStudies();
      await loadExports();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to create batch');
    } finally {
      setCreating(false);
    }
  }

  async function retryItem(itemId: string) {
    setError(null);
    setNotice(null);
    try {
      const r = await api.post(`/meta/items/${itemId}/retry`);
      setNotice(`Retry enqueued: job ${r.data?.job_id}`);
      if (selectedBatchId) await loadItems(selectedBatchId);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Retry failed');
    }
  }

  async function exportExcel() {
    if (!projectId) return;
    setError(null);
    setNotice(null);
    try {
      const r = await api.post('/meta/export', {
        project_id: projectId,
        batch_id: selectedBatchId,
      });
      const jid = r.data?.job_id as string | undefined;
      if (jid) {
        setExportJobId(jid);
      }
      setNotice(`Export job enqueued: ${jid || '(unknown job id)'}`);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Export failed');
    }
  }

  async function downloadExport(row: ExportRow) {
    setError(null);
    try {
      const r = await api.get(`/meta/exports/${row.id}/download`, { responseType: 'blob' });
      downloadBlob(r.data as Blob, row.filename || 'meta_export.xlsx');
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Download failed');
    }
  }

  useEffect(() => {
    loadBatches();
    loadStudies();
    loadExports();
  }, [projectId]);

  useEffect(() => {
    loadStudies();
    loadExports();
  }, [selectedBatchId]);

  useEffect(() => {
    if (!selectedBatchId) return;
    if (runningItems.length === 0) return;
    const t = window.setInterval(() => {
      loadItems(selectedBatchId);
      loadStudies();
    }, 4000);
    return () => window.clearInterval(t);
  }, [selectedBatchId, runningItems.map((i) => i.id).join('|')]);

  // Export job polling handled by useJobPolling hook above

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div>
        <h1 className="rc-page-title">Extraction Workspace</h1>
        <div className="rc-subtitle">Batch upload PDFs, extract structured study data, review effect sizes and export reusable datasets.</div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '380px 1fr', gap: 12 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div className="rc-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8, marginBottom: 10 }}>
              <div className="rc-card-title" style={{ marginBottom: 0 }}>Batches</div>
              <button className="rc-btn rc-btn--sm rc-btn--ghost" onClick={loadBatches} disabled={loading}>↻ Refresh</button>
            </div>
          {notice ? (
            <div className="rc-banner rc-banner--success" style={{ marginBottom: 10 }}>
              {String(notice)}
            </div>
          ) : null}
          {error ? <div className="rc-error" style={{ marginBottom: 8 }}>{String(error)}</div> : null}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {batches.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '20px 0', color: 'var(--rc-muted)', fontSize: 13 }}>
                No batches yet. Create one below.
              </div>
            ) : null}
            {batches.map((b) => (
              <button
                key={b.id}
                onClick={() => loadItems(b.id)}
                className="rc-btn"
                style={{ textAlign: 'left', padding: 10, borderColor: b.id === selectedBatchId ? 'rgba(79,70,229,0.35)' : undefined, background: b.id === selectedBatchId ? 'var(--rc-primary-weak)' : undefined }}
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
            <button className="rc-btn rc-btn--primary" disabled={creating} onClick={createBatch}>
              {creating ? 'Creating…' : 'Create + extract'}
            </button>
          </div>
        </div>

        <div className="rc-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'center' }}>
            <div className="rc-card-title" style={{ marginBottom: 0 }}>Exports</div>
            <button className="rc-btn" onClick={loadExports}>Refresh</button>
          </div>
          <div style={{ height: 10 }} />
          <button className="rc-btn rc-btn--primary" onClick={exportExcel} disabled={Boolean(exportJobId)}>
            {exportJobId ? 'Exporting…' : 'Export Excel'}
          </button>
          {exportJob.status ? (
            <div className="rc-help" style={{ marginTop: 8 }}>
              Export: {exportJob.status.status} · {exportJob.status.progress}%
              {exportJob.status.error ? <span className="rc-error"> · {String(exportJob.status.error)}</span> : null}
            </div>
          ) : null}
          <div style={{ height: 10 }} />
          {exportsList.length === 0 ? <div className="rc-muted">No exports yet.</div> : null}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {exportsList.map((ex) => (
              <div key={ex.id} className="rc-card" style={{ padding: 10, display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'center' }}>
                <div className="rc-help" style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{ex.filename}</div>
                <button className="rc-btn" onClick={() => downloadExport(ex)}>Download</button>
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
                <div key={it.id} className="rc-card" style={{ padding: 12, display: 'flex', flexDirection: 'column', gap: 6 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'flex-start' }}>
                    <div style={{ fontWeight: 700, fontSize: 13, flex: 1, lineHeight: 1.35 }}>
                      {it.paper_title || it.paper_filename || `Paper ${it.paper_id.slice(0, 8)}`}
                    </div>
                    <span className={
                      it.status === 'completed' ? 'rc-badge rc-badge--success' :
                      it.status === 'failed' ? 'rc-badge rc-badge--danger' :
                      it.status === 'started' ? 'rc-badge rc-badge--info' :
                      'rc-badge'
                    } style={{ flexShrink: 0 }}>{it.status}</span>
                  </div>
                  {it.paper_filename && it.paper_title && (
                    <div className="rc-help">{it.paper_filename}</div>
                  )}
                  {it.error_message ? (
                    <div className="rc-error" style={{ fontSize: 12, marginTop: 2 }}>{it.error_message}</div>
                  ) : null}
                  {(it.status === 'failed' || it.status === 'queued') && (
                    <div>
                      <button
                        className="rc-btn rc-btn--sm"
                        onClick={() => retryItem(it.id)}
                        disabled={it.status === 'queued' || it.status === 'started'}
                        style={{ marginTop: 4 }}
                      >
                        Retry
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: '32px 16px', color: 'var(--rc-muted)', fontSize: 13 }}>
              Select a batch from the left panel to view its extraction items.
            </div>
          )}
        </div>

        <div className="rc-card">
          <div style={{ display: 'grid', gridTemplateColumns: '380px 1fr', gap: 12 }}>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div className="rc-card-title" style={{ marginBottom: 0 }}>Studies</div>
                <button className="rc-btn" onClick={loadStudies}>Refresh</button>
              </div>
              <div style={{ height: 10 }} />
              {studies.length === 0 ? <div className="rc-muted">No studies (yet).</div> : null}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 460, overflow: 'auto' }}>
                {studies.map((s) => (
                  <button
                    key={s.id}
                    onClick={() => setSelectedStudyId(s.id)}
                    className="rc-btn"
                    style={{ textAlign: 'left', padding: 12, borderColor: s.id === selectedStudyId ? 'rgba(79,70,229,0.35)' : 'rgba(15,23,42,0.16)', background: s.id === selectedStudyId ? 'rgba(79,70,229,0.08)' : 'white' }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'flex-start' }}>
                      <div style={{ fontWeight: 700, fontSize: 12, flex: 1, lineHeight: 1.35 }}>{s.paper_title || s.paper_filename || `Study ${s.id.slice(0, 8)}`}</div>
                      {s.rob_auto_generated ? <span className="rc-badge" style={{ flexShrink: 0, fontSize: 9 }}>RoB auto</span> : null}
                    </div>
                    {s.paper_filename && s.paper_title ? <div className="rc-help">{s.paper_filename}</div> : null}
                    <div className="rc-help">
                      v{s.version} · conf {typeof s.extraction_confidence === 'number' ? s.extraction_confidence.toFixed(2) : s.extraction_confidence}
                    </div>
                  </button>
                ))}
              </div>
            </div>

            <div>
              {selectedStudyId ? (
                <StudyViewer studyId={selectedStudyId} onSelectStudyId={setSelectedStudyId} />
              ) : (
                <div style={{ textAlign: 'center', padding: '32px 16px', color: 'var(--rc-muted)', fontSize: 13 }}>
                Select a study from the left to view extracted data, effect sizes and risk of bias.
              </div>
              )}
            </div>
          </div>
        </div>
      </div>
      </div>
    </div>
  );
}
