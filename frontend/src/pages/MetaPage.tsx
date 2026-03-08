import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
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

type StudyRow = {
  id: string;
  paper_id: string;
  paper_title?: string;
  paper_filename?: string;
  batch_id?: string | null;
  version: number;
  extraction_confidence: number;
  rob_auto_generated?: boolean;
  created_at: string;
};

type ExportRow = {
  id: string;
  project_id: string;
  batch_id?: string | null;
  filename: string;
  created_at: string;
};

function formatDate(value?: string | null) {
  if (!value) return 'Unknown time';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

export default function MetaPage() {
  const { projectId } = useParams();

  const [batches, setBatches] = useState<BatchRow[]>([]);
  const [selectedBatchId, setSelectedBatchId] = useState<string | null>(null);
  const [items, setItems] = useState<ItemRow[]>([]);
  const [studies, setStudies] = useState<StudyRow[]>([]);
  const [selectedStudyId, setSelectedStudyId] = useState<string | null>(null);
  const [exportsList, setExportsList] = useState<ExportRow[]>([]);
  const [exportJobId, setExportJobId] = useState<string | null>(null);
  const [exportJobStatus, setExportJobStatus] = useState<{ status: string; progress: number; error?: string | null } | null>(null);
  const [files, setFiles] = useState<FileList | null>(null);
  const [title, setTitle] = useState('');
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const runningItems = useMemo(() => items.filter((it) => ['queued', 'started'].includes(it.status)), [items]);
  const completedItems = useMemo(() => items.filter((it) => it.status === 'completed').length, [items]);
  const failedItems = useMemo(() => items.filter((it) => it.status === 'failed').length, [items]);
  const selectedBatch = useMemo(() => batches.find((batch) => batch.id === selectedBatchId) || null, [batches, selectedBatchId]);
  const selectedFilesCount = files?.length || 0;

  async function loadBatches() {
    if (!projectId) return;
    setLoading(true);
    setError(null);
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
      const nextStudies = r.data as StudyRow[];
      setStudies(nextStudies);
      if (!selectedStudyId && nextStudies[0]) {
        setSelectedStudyId(nextStudies[0].id);
      }
      if (selectedStudyId && !nextStudies.some((study) => study.id === selectedStudyId)) {
        setSelectedStudyId(nextStudies[0]?.id || null);
      }
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
      Array.from(files).forEach((file) => form.append('files', file));

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
        setExportJobStatus({ status: 'queued', progress: 0, error: null });
      }
      setNotice(`Export job enqueued: ${jid || '(unknown job id)'}`);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Export failed');
    } finally {
      await loadExports();
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
    void loadBatches();
    void loadStudies();
    void loadExports();
  }, [projectId]);

  useEffect(() => {
    void loadStudies();
    void loadExports();
  }, [selectedBatchId]);

  useEffect(() => {
    if (!selectedBatchId || runningItems.length === 0) return;
    const timer = window.setInterval(() => {
      void loadItems(selectedBatchId);
      void loadStudies();
    }, 4000);
    return () => window.clearInterval(timer);
  }, [selectedBatchId, runningItems.map((item) => item.id).join('|')]);

  useEffect(() => {
    if (!exportJobId) return;

    let stopped = false;

    async function poll() {
      if (stopped) return;
      try {
        const r = await api.get(`/jobs/${exportJobId}`);
        const status = String((r.data as any)?.status || 'unknown');
        const progress = Number((r.data as any)?.progress_percent || 0);
        const err = (r.data as any)?.error || null;
        setExportJobStatus({ status, progress, error: err });

        if (status === 'completed') {
          await loadExports();
          setExportJobId(null);
        }
        if (status === 'failed') {
          setExportJobId(null);
        }
      } catch (e: any) {
        setExportJobStatus({ status: 'polling_error', progress: 0, error: e?.response?.data?.detail || 'Polling failed' });
      }
    }

    void poll();
    const timer = window.setInterval(() => {
      void poll();
    }, 4000);
    return () => {
      stopped = true;
      window.clearInterval(timer);
    };
  }, [exportJobId]);

  return (
    <div className="rc-section-shell">
      <div className="rc-hero-card">
        <div style={{ maxWidth: 760 }}>
          <div className="rc-stage-label rc-stage-label--warm">Step 3 · Extract</div>
          <h1 className="rc-page-title" style={{ marginTop: 12 }}>Extraction Workspace</h1>
          <div className="rc-subtitle">Upload PDF batches, review extraction health and turn papers into structured evidence before you write or analyze.</div>
          <div className="rc-help" style={{ marginTop: 12 }}>This is the bridge between reading and writing. Clean extractions here make every downstream draft and analysis easier.</div>
        </div>
        <div className="rc-metric-grid" style={{ minWidth: 320 }}>
          <div className="rc-metric-tile"><strong>{batches.length}</strong><span>Batches</span></div>
          <div className="rc-metric-tile"><strong>{studies.length}</strong><span>Studies</span></div>
          <div className="rc-metric-tile"><strong>{runningItems.length}</strong><span>Running items</span></div>
          <div className="rc-metric-tile"><strong>{exportsList.length}</strong><span>Exports</span></div>
        </div>
      </div>

      {error ? <div className="rc-error">{String(error)}</div> : null}
      {notice ? <div className="rc-soft-card"><div className="rc-help">{notice}</div></div> : null}

      <div className="rc-panel-grid" style={{ alignItems: 'start' }}>
        <div className="rc-stack">
          <div className="rc-card">
            <div className="rc-toolbar">
              <div>
                <div className="rc-card-title" style={{ marginBottom: 4 }}>Batch queue</div>
                <div className="rc-help">Select a batch to focus extraction items and study outputs.</div>
              </div>
              <button className="rc-btn" onClick={() => void loadBatches()} disabled={loading}>
                {loading ? 'Refreshing...' : 'Refresh'}
              </button>
            </div>
            <div style={{ height: 12 }} />
            {batches.length === 0 ? (
              <div className="rc-empty-state">
                <div style={{ fontWeight: 800, marginBottom: 6 }}>No extraction batches yet</div>
                <div className="rc-help">Create a batch from one or more PDFs to start generating structured study records.</div>
              </div>
            ) : (
              <div className="rc-card-list">
                {batches.map((batch) => (
                  <button
                    key={batch.id}
                    onClick={() => void loadItems(batch.id)}
                    className={`rc-list-button ${batch.id === selectedBatchId ? 'rc-list-button--active' : ''}`}
                  >
                    <div className="rc-detail-header">
                      <div style={{ fontWeight: 850 }}>{batch.title || '(untitled batch)'}</div>
                      <span className={batch.status === 'completed' ? 'rc-badge rc-badge--success' : batch.status === 'failed' ? 'rc-badge rc-badge--danger' : 'rc-badge rc-badge--info'}>
                        {batch.status}
                      </span>
                    </div>
                    <div className="rc-help" style={{ marginTop: 8 }}>{formatDate(batch.created_at)}</div>
                  </button>
                ))}
              </div>
            )}
            <div style={{ height: 12 }} />
            <button className="rc-btn rc-btn--ghost" onClick={() => setSelectedBatchId(null)} disabled={!selectedBatchId}>
              Clear batch focus
            </button>
          </div>

          <div className="rc-card">
            <div className="rc-card-title">New extraction batch</div>
            <div className="rc-help" style={{ marginBottom: 12 }}>Choose PDF files, optionally name the run and let the worker queue process them in the background.</div>
            <div className="rc-card-list">
              <div>
                <div className="rc-kicker">Batch title</div>
                <input className="rc-input" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. ACL graft meta-analysis" />
              </div>
              <div>
                <div className="rc-kicker">PDF files</div>
                <input type="file" multiple accept="application/pdf" onChange={(e) => setFiles(e.target.files)} />
                <div className="rc-help" style={{ marginTop: 8 }}>
                  {selectedFilesCount ? `${selectedFilesCount} file(s) selected.` : 'Choose one or more PDFs.'} Extraction runs async through Redis workers.
                </div>
              </div>
              <button className="rc-btn rc-btn--primary" disabled={creating} onClick={createBatch}>
                {creating ? 'Creating...' : 'Create and extract'}
              </button>
            </div>
          </div>

          <div className="rc-card">
            <div className="rc-toolbar">
              <div>
                <div className="rc-card-title" style={{ marginBottom: 4 }}>Exports</div>
                <div className="rc-help">Package current extraction data for downstream review or analysis.</div>
              </div>
              <button className="rc-btn" onClick={() => void loadExports()}>Refresh</button>
            </div>
            <div style={{ height: 12 }} />
            <button className="rc-btn rc-btn--primary" onClick={exportExcel} disabled={Boolean(exportJobId)}>
              {exportJobId ? 'Exporting...' : 'Export Excel'}
            </button>
            {exportJobStatus ? (
              <div className="rc-help" style={{ marginTop: 10 }}>
                Export status: {exportJobStatus.status} · {exportJobStatus.progress}%
                {exportJobStatus.error ? ` · ${String(exportJobStatus.error)}` : ''}
              </div>
            ) : null}
            <div style={{ height: 12 }} />
            {exportsList.length === 0 ? (
              <div className="rc-empty-state">
                <div style={{ fontWeight: 800, marginBottom: 6 }}>No exports yet</div>
                <div className="rc-help">Run an export once a batch has produced study outputs.</div>
              </div>
            ) : (
              <div className="rc-card-list">
                {exportsList.map((item) => (
                  <div key={item.id} className="rc-soft-card">
                    <div className="rc-detail-header">
                      <div style={{ minWidth: 0, flex: 1 }}>
                        <div style={{ fontWeight: 800, overflow: 'hidden', textOverflow: 'ellipsis' }}>{item.filename}</div>
                        <div className="rc-help" style={{ marginTop: 6 }}>{formatDate(item.created_at)}</div>
                      </div>
                      <button className="rc-btn" onClick={() => void downloadExport(item)}>Download</button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="rc-stack">
          <div className="rc-card">
            <div className="rc-toolbar">
              <div>
                <div className="rc-card-title" style={{ marginBottom: 4 }}>Batch items</div>
                <div className="rc-help">
                  {selectedBatch ? `Tracking papers in "${selectedBatch.title || 'Untitled batch'}".` : 'Select a batch to inspect item-level progress and failures.'}
                </div>
              </div>
              {runningItems.length ? <span className="rc-badge rc-badge--info">Auto-refreshing</span> : null}
            </div>
            <div style={{ height: 12 }} />
            {selectedBatchId ? (
              <>
                <div className="rc-metric-grid" style={{ marginBottom: 12 }}>
                  <div className="rc-metric-tile"><strong>{items.length}</strong><span>Items</span></div>
                  <div className="rc-metric-tile"><strong>{completedItems}</strong><span>Completed</span></div>
                  <div className="rc-metric-tile"><strong>{failedItems}</strong><span>Failed</span></div>
                </div>
                {items.length === 0 ? (
                  <div className="rc-empty-state">
                    <div style={{ fontWeight: 800, marginBottom: 6 }}>Batch has no items yet</div>
                    <div className="rc-help">Files may still be entering the queue. Check Jobs if Redis workers are busy.</div>
                  </div>
                ) : (
                  <div className="rc-card-list">
                    {items.map((item) => (
                      <div key={item.id} className="rc-soft-card">
                        <div className="rc-detail-header">
                          <div style={{ flex: 1, minWidth: 220 }}>
                            <div style={{ fontWeight: 850 }}>{item.paper_title || item.paper_filename || 'Untitled item'}</div>
                            <div className="rc-help" style={{ marginTop: 8 }}>
                              {item.paper_filename ? `${item.paper_filename} · ` : ''}
                              paper_id {item.paper_id}
                            </div>
                          </div>
                          <span className={item.status === 'completed' ? 'rc-badge rc-badge--success' : item.status === 'failed' ? 'rc-badge rc-badge--danger' : 'rc-badge rc-badge--info'}>
                            {item.status}
                          </span>
                        </div>
                        {item.error_message ? <div className="rc-error" style={{ marginTop: 10 }}>{item.error_message}</div> : null}
                        <div className="rc-row" style={{ marginTop: 10 }}>
                          <button className="rc-btn" onClick={() => void retryItem(item.id)} disabled={['queued', 'started'].includes(item.status)}>
                            Retry item
                          </button>
                          {item.updated_at ? <div className="rc-help">Updated {formatDate(item.updated_at)}</div> : null}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </>
            ) : (
              <div className="rc-empty-state">
                <div style={{ fontWeight: 800, marginBottom: 6 }}>No batch selected</div>
                <div className="rc-help">Pick a batch from the queue to review item progress, failures and retry controls.</div>
              </div>
            )}
          </div>

          <div className="rc-card">
            <div className="rc-toolbar">
              <div>
                <div className="rc-card-title" style={{ marginBottom: 4 }}>Study review</div>
                <div className="rc-help">Browse extracted studies and open the detailed viewer for confidence, risk of bias and effect size review.</div>
              </div>
              <button className="rc-btn" onClick={() => void loadStudies()}>Refresh</button>
            </div>
            <div style={{ height: 12 }} />
            {studies.length === 0 ? (
              <div className="rc-empty-state">
                <div style={{ fontWeight: 800, marginBottom: 6 }}>No studies available yet</div>
                <div className="rc-help">Studies appear here as batch items complete extraction. Once a study lands, this panel turns into a review split view.</div>
              </div>
            ) : (
              <div className="rc-split-layout">
                <div className="rc-card-list" style={{ maxHeight: 620, overflow: 'auto', paddingRight: 4 }}>
                  {studies.map((study) => (
                    <button
                      key={study.id}
                      onClick={() => setSelectedStudyId(study.id)}
                      className={`rc-list-button ${study.id === selectedStudyId ? 'rc-list-button--active' : ''}`}
                    >
                      <div className="rc-detail-header">
                        <div style={{ fontWeight: 850, fontSize: 13, lineHeight: 1.3 }}>
                          {study.paper_title || study.paper_filename || `Study ${study.id}`}
                        </div>
                        {study.rob_auto_generated ? <span className="rc-badge">ROB auto</span> : null}
                      </div>
                      <div className="rc-help" style={{ marginTop: 8 }}>
                        v{study.version} · confidence {study.extraction_confidence}
                        {study.batch_id ? ' · batched' : ''}
                      </div>
                    </button>
                  ))}
                </div>

                <div>
                  {selectedStudyId ? (
                    <StudyViewer studyId={selectedStudyId} onSelectStudyId={setSelectedStudyId} />
                  ) : (
                    <div className="rc-empty-state">
                      <div style={{ fontWeight: 800, marginBottom: 6 }}>Select a study</div>
                      <div className="rc-help">Choose a study from the left column to review extracted evidence in detail.</div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
