import { Download, FlaskConical, Plus, RefreshCw } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import StudyViewer from '../components/meta/StudyViewer';
import { downloadBlob } from '../components/meta/exportUtils';
import { api } from '../services/api';
import EmptyState from '../ui/EmptyState/EmptyState';

type BatchRow = { id: string; title?: string | null; status: string; created_at: string; };
type ItemRow  = { id: string; paper_id: string; paper_title?: string; paper_filename?: string; status: string; error_message?: string | null; result_summary?: any; created_at?: string | null; updated_at?: string | null; };
type StudyRow = { id: string; paper_id: string; paper_title?: string; paper_filename?: string; batch_id?: string | null; version: number; extraction_confidence: number; rob_auto_generated?: boolean; created_at: string; };
type ExportRow = { id: string; project_id: string; batch_id?: string | null; filename: string; created_at: string; };

function confidenceColor(conf: number): string {
  if (conf >= 0.8) return 'var(--rc-success)';
  if (conf >= 0.5) return 'var(--rc-warning)';
  return 'var(--rc-danger)';
}

export default function MetaPage() {
  const { projectId } = useParams();

  const [batches, setBatches]               = useState<BatchRow[]>([]);
  const [selectedBatchId, setSelectedBatchId] = useState<string | null>(null);
  const [items, setItems]                   = useState<ItemRow[]>([]);
  const [studies, setStudies]               = useState<StudyRow[]>([]);
  const [selectedStudyId, setSelectedStudyId] = useState<string | null>(null);
  const [exportsList, setExportsList]       = useState<ExportRow[]>([]);
  const [exportJobId, setExportJobId]       = useState<string | null>(null);
  const [exportJobStatus, setExportJobStatus] = useState<{ status: string; progress: number; error?: string | null } | null>(null);
  const [files, setFiles]                   = useState<FileList | null>(null);
  const [title, setTitle]                   = useState('');
  const [loading, setLoading]               = useState(false);
  const [creating, setCreating]             = useState(false);
  const [error, setError]                   = useState<string | null>(null);
  const [notice, setNotice]                 = useState<string | null>(null);
  const [showNewBatch, setShowNewBatch]     = useState(false);

  const runningItems = useMemo(() => items.filter(it => ['queued','started'].includes(it.status)), [items]);

  async function loadBatches()  { if (!projectId) return; setLoading(true); try { const r = await api.get(`/meta/batches?project_id=${projectId}`); setBatches(r.data as BatchRow[]); } catch (e: any) { setError(e?.response?.data?.detail || 'Failed'); } finally { setLoading(false); } }
  async function loadItems(bId: string) { try { const r = await api.get(`/meta/batches/${bId}/items`); setItems(r.data as ItemRow[]); setSelectedBatchId(bId); } catch (e: any) { setError(e?.response?.data?.detail || 'Failed'); } }
  async function loadStudies()  { if (!projectId) return; try { const q = selectedBatchId ? `&batch_id=${selectedBatchId}` : ''; const r = await api.get(`/meta/studies?project_id=${projectId}${q}`); setStudies(r.data as StudyRow[]); } catch (e: any) { setError(e?.response?.data?.detail || 'Failed'); } }
  async function loadExports()  { if (!projectId) return; try { const q = selectedBatchId ? `&batch_id=${selectedBatchId}` : ''; const r = await api.get(`/meta/exports?project_id=${projectId}${q}`); setExportsList(r.data as ExportRow[]); } catch (e: any) { setError(e?.response?.data?.detail || 'Failed'); } }

  async function createBatch() {
    if (!projectId || !files || files.length === 0) { setError('Select at least 1 PDF'); return; }
    setCreating(true); setError(null); setNotice(null);
    try {
      const form = new FormData();
      form.append('project_id', projectId);
      if (title.trim()) form.append('title', title.trim());
      Array.from(files).forEach(f => form.append('files', f));
      const r = await api.post('/meta/batches', form, { headers: { 'Content-Type': 'multipart/form-data' } });
      const batchId = r.data?.batch_id as string;
      setNotice(`Batch created (${batchId})`);
      setFiles(null); setTitle(''); setShowNewBatch(false);
      await loadBatches();
      if (batchId) await loadItems(batchId);
      await loadStudies(); await loadExports();
    } catch (e: any) { setError(e?.response?.data?.detail || 'Failed'); }
    finally { setCreating(false); }
  }

  async function retryItem(itemId: string) { try { const r = await api.post(`/meta/items/${itemId}/retry`); setNotice(`Retry: ${r.data?.job_id}`); if (selectedBatchId) await loadItems(selectedBatchId); } catch (e: any) { setError(e?.response?.data?.detail || 'Retry failed'); } }

  async function exportExcel() {
    if (!projectId) return;
    try { const r = await api.post('/meta/export', { project_id: projectId, batch_id: selectedBatchId }); const jid = r.data?.job_id as string; if (jid) { setExportJobId(jid); setExportJobStatus({ status: 'queued', progress: 0 }); } } catch (e: any) { setError(e?.response?.data?.detail || 'Export failed'); }
  }

  async function downloadExport(row: ExportRow) { try { const r = await api.get(`/meta/exports/${row.id}/download`, { responseType: 'blob' }); downloadBlob(r.data as Blob, row.filename || 'meta_export.xlsx'); } catch (e: any) { setError(e?.response?.data?.detail || 'Download failed'); } }

  useEffect(() => { loadBatches(); loadStudies(); loadExports(); }, [projectId]);
  useEffect(() => { loadStudies(); loadExports(); }, [selectedBatchId]);
  useEffect(() => {
    if (!selectedBatchId || runningItems.length === 0) return;
    const t = window.setInterval(() => { loadItems(selectedBatchId); loadStudies(); }, 4000);
    return () => window.clearInterval(t);
  }, [selectedBatchId, runningItems.map(i => i.id).join('|')]);
  useEffect(() => {
    if (!exportJobId) return;
    let stopped = false;
    async function poll() {
      if (stopped) return;
      try { const r = await api.get(`/jobs/${exportJobId}`); const s = String((r.data as any)?.status || 'unknown'); const p = Number((r.data as any)?.progress_percent || 0); setExportJobStatus({ status: s, progress: p, error: (r.data as any)?.error || null }); if (s === 'completed') { await loadExports(); setExportJobId(null); } if (s === 'failed') setExportJobId(null); } catch {}
    }
    poll(); const t = window.setInterval(poll, 4000); return () => { stopped = true; window.clearInterval(t); };
  }, [exportJobId]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* ── Header ── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16 }}>
        <div>
          <h1 className="rc-page-title">Data Extraction</h1>
          <div className="rc-subtitle">Extract and compare structured data from your papers — effect sizes, ROB, statistics.</div>
        </div>
        <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start', flexWrap: 'wrap' }}>
          {/* Stat cards */}
          <div style={{ display: 'flex', gap: 8 }}>
            {[
              { label: 'Studies',  value: studies.length },
              { label: 'Batches', value: batches.length },
              { label: 'Exports', value: exportsList.length },
            ].map(({ label, value }) => (
              <div key={label} className="rc-stat">
                <span className="rc-stat-value">{value}</span>
                <span className="rc-stat-label">{label}</span>
              </div>
            ))}
          </div>
          <button className="rc-btn rc-btn--primary" onClick={() => setShowNewBatch(true)}>
            <Plus size={14} /> New batch
          </button>
        </div>
      </div>

      {error  && <div className="rc-error">{error}</div>}
      {notice && <div style={{ color: 'var(--rc-success)', fontSize: 13, fontWeight: 600 }}>✓ {notice}</div>}

      {/* ── Main layout ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '260px 1fr', gap: 14, alignItems: 'start' }}>

        {/* Left: batches list */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div className="rc-card" style={{ padding: 0, overflow: 'hidden' }}>
            <div style={{ padding: '12px 14px', borderBottom: '1px solid var(--rc-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--rc-text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Batches</span>
              <button className="rc-btn rc-btn--ghost" style={{ padding: '4px 6px' }} onClick={loadBatches} disabled={loading}>
                <RefreshCw size={13} style={{ color: 'var(--rc-muted)' }} />
              </button>
            </div>
            <div style={{ padding: '6px 6px' }}>
              {batches.length === 0
                ? <div className="rc-help" style={{ padding: '10px 8px' }}>No batches yet.</div>
                : batches.map(b => (
                  <button
                    key={b.id}
                    onClick={() => loadItems(b.id)}
                    style={{
                      width: '100%', textAlign: 'left', padding: '9px 10px', borderRadius: 8,
                      border: b.id === selectedBatchId ? '1px solid var(--rc-primary-border)' : '1px solid transparent',
                      background: b.id === selectedBatchId ? 'var(--rc-primary-weak)' : 'transparent',
                      cursor: 'pointer', display: 'flex', flexDirection: 'column', gap: 3,
                      transition: 'background 100ms ease',
                    }}
                  >
                    <span style={{ fontSize: 13, fontWeight: 650, color: b.id === selectedBatchId ? 'var(--rc-primary)' : 'var(--rc-text)' }}>
                      {b.title || '(untitled)'}
                    </span>
                    <span className={`rc-tag ${b.status === 'completed' ? 'rc-tag--green' : b.status === 'failed' ? 'rc-tag--red' : 'rc-tag--blue'}`} style={{ width: 'fit-content', fontSize: 10 }}>
                      {b.status}
                    </span>
                  </button>
                ))
              }
            </div>
            {selectedBatchId && (
              <div style={{ padding: '6px 6px', borderTop: '1px solid var(--rc-border)' }}>
                <button className="rc-btn rc-btn--ghost" style={{ width: '100%', justifyContent: 'center', fontSize: 12 }} onClick={() => { setSelectedBatchId(null); setItems([]); }}>
                  Clear filter
                </button>
              </div>
            )}
          </div>

          {/* Export */}
          <div className="rc-card">
            <div className="rc-card-title">Export</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <button className="rc-btn rc-btn--primary" style={{ justifyContent: 'center' }} onClick={exportExcel} disabled={Boolean(exportJobId)}>
                <Download size={13} /> {exportJobId ? 'Exporting…' : 'Export Excel'}
              </button>
              {exportJobStatus && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                  <div className="rc-progress"><div style={{ width: `${exportJobStatus.progress}%` }} /></div>
                  <span className="rc-help">{exportJobStatus.status} · {exportJobStatus.progress}%</span>
                </div>
              )}
              {exportsList.length > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 4 }}>
                  {exportsList.map(ex => (
                    <div key={ex.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
                      <span style={{ fontSize: 12, color: 'var(--rc-text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1 }}>{ex.filename}</span>
                      <button className="rc-btn" style={{ fontSize: 11, padding: '4px 8px', flexShrink: 0 }} onClick={() => downloadExport(ex)}>
                        <Download size={11} />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right: studies table */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div className="rc-card" style={{ padding: 0, overflow: 'hidden' }}>
            <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--rc-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--rc-text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Studies {selectedBatchId ? '(batch filter)' : '(all)'}
              </span>
              <button className="rc-btn rc-btn--ghost" style={{ padding: '4px 6px' }} onClick={loadStudies}>
                <RefreshCw size={13} style={{ color: 'var(--rc-muted)' }} />
              </button>
            </div>

            {studies.length === 0 ? (
              <EmptyState
                icon={<FlaskConical size={32} />}
                title="No hay estudios extraídos"
                description="Sube PDFs y lanza una extracción para comenzar el meta-análisis."
                action={{ label: '+ New batch', onClick: () => setShowNewBatch(true) }}
              />
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table className="rc-table">
                  <thead>
                    <tr>
                      <th style={{ width: '35%' }}>Paper</th>
                      <th style={{ width: '18%' }}>Confidence</th>
                      <th style={{ width: '10%' }}>Version</th>
                      <th style={{ width: '10%' }}>ROB auto</th>
                      <th style={{ width: '14%' }}>Date</th>
                      <th style={{ width: '13%' }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {studies.map(s => (
                      <tr key={s.id} style={{ cursor: 'pointer' }} onClick={() => setSelectedStudyId(s.id === selectedStudyId ? null : s.id)}>
                        <td>
                          <div style={{ fontWeight: 600, fontSize: 13, maxWidth: 280, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {s.paper_title || `Study ${s.id.slice(0, 8)}`}
                          </div>
                          {s.paper_filename && (
                            <div style={{ fontSize: 11, color: 'var(--rc-text-tertiary)', marginTop: 2 }}>{s.paper_filename}</div>
                          )}
                        </td>
                        <td>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            <div className="rc-progress" style={{ width: 72 }}>
                              <div style={{ width: `${Math.round(s.extraction_confidence * 100)}%`, background: confidenceColor(s.extraction_confidence) }} />
                            </div>
                            <span style={{ fontSize: 12, fontWeight: 600, color: confidenceColor(s.extraction_confidence) }}>
                              {Math.round(s.extraction_confidence * 100)}%
                            </span>
                          </div>
                        </td>
                        <td><span className="rc-tag rc-tag--slate">v{s.version}</span></td>
                        <td>
                          {s.rob_auto_generated
                            ? <span style={{ color: 'var(--rc-success)', fontWeight: 700, fontSize: 14 }}>✓</span>
                            : <span style={{ color: 'var(--rc-text-tertiary)' }}>—</span>
                          }
                        </td>
                        <td>
                          <span style={{ fontSize: 12, color: 'var(--rc-text-tertiary)' }}>
                            {new Date(s.created_at).toLocaleDateString()}
                          </span>
                        </td>
                        <td>
                          <div className="rc-row" style={{ gap: 5 }}>
                            <button
                              className="rc-btn"
                              style={{ fontSize: 11, padding: '4px 9px' }}
                              onClick={e => { e.stopPropagation(); setSelectedStudyId(s.id === selectedStudyId ? null : s.id); }}
                            >
                              {s.id === selectedStudyId ? 'Close' : 'View'}
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Study viewer */}
          {selectedStudyId && (
            <div className="rc-card">
              <StudyViewer studyId={selectedStudyId} onSelectStudyId={setSelectedStudyId} />
            </div>
          )}

          {/* Batch items */}
          {selectedBatchId && items.length > 0 && (
            <div className="rc-card" style={{ padding: 0, overflow: 'hidden' }}>
              <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--rc-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--rc-text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Batch items {runningItems.length > 0 ? <span className="rc-tag rc-tag--blue" style={{ marginLeft: 8 }}>Auto-refreshing</span> : ''}
                </span>
              </div>
              <table className="rc-table">
                <thead><tr><th>Paper</th><th>Status</th><th>Actions</th></tr></thead>
                <tbody>
                  {items.map(it => (
                    <tr key={it.id}>
                      <td>
                        <div style={{ fontSize: 13, fontWeight: 600 }}>{it.paper_title || it.paper_id.slice(0, 12)}</div>
                        {it.paper_filename && <div style={{ fontSize: 11, color: 'var(--rc-text-tertiary)' }}>{it.paper_filename}</div>}
                        {it.error_message && <div className="rc-error" style={{ fontSize: 11, marginTop: 3 }}>{it.error_message}</div>}
                      </td>
                      <td>
                        <span className={`rc-tag ${it.status === 'completed' ? 'rc-tag--green' : it.status === 'failed' ? 'rc-tag--red' : 'rc-tag--blue'}`}>
                          {it.status}
                        </span>
                      </td>
                      <td>
                        <button className="rc-btn" style={{ fontSize: 11, padding: '4px 9px' }}
                          disabled={['queued','started'].includes(it.status)}
                          onClick={() => retryItem(it.id)}>
                          Retry
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* ── New Batch Modal ── */}
      {showNewBatch && (
        <div className="rc-overlay" onClick={() => setShowNewBatch(false)}>
          <div className="rc-modal" onClick={e => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
              <h2 style={{ margin: 0, fontSize: 16, fontWeight: 800 }}>New extraction batch</h2>
              <button className="rc-btn rc-btn--ghost" style={{ padding: 6 }} onClick={() => setShowNewBatch(false)}>✕</button>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div>
                <div className="rc-kicker">Title (optional)</div>
                <input className="rc-input" value={title} onChange={e => setTitle(e.target.value)} placeholder="e.g. ACL graft meta-analysis" />
              </div>
              <div>
                <div className="rc-kicker">PDF files *</div>
                <input type="file" multiple accept="application/pdf" onChange={e => setFiles(e.target.files)} style={{ fontSize: 13 }} />
                <div className="rc-help" style={{ marginTop: 6 }}>Extraction runs async via Redis worker. Check Jobs for progress.</div>
              </div>
              <div className="rc-row" style={{ justifyContent: 'flex-end', gap: 8 }}>
                <button className="rc-btn" onClick={() => setShowNewBatch(false)}>Cancel</button>
                <button className="rc-btn rc-btn--primary" disabled={creating || !files || files.length === 0} onClick={createBatch}>
                  {creating ? 'Creating…' : 'Create + extract'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
