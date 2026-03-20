import { useEffect, useMemo, useState, useCallback, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../services/api';
import { useToast } from '../ui/Toast/ToastProvider';
import { useConfirm } from '../ui/Dialog/useConfirm';
import { Skeleton, SkeletonLines } from '../ui/Skeleton/Skeleton';

type PaperRow = {
  id: string;
  title: string;
  authors?: string | null;
  journal?: string | null;
  publication_year?: number | null;
  doi?: string | null;
  pmid?: string | null;
  filename: string;
  file_size_kb?: number | null;
  is_processed: boolean;
  processing_status?: string;
  processing_warnings?: string[];
  source_provider?: string | null;
  source_type?: string | null;
  is_open_access?: boolean;
  favorite?: boolean;
  created_at?: string | null;
};

type StatusFilter = 'all' | 'ready' | 'processing' | 'pending' | 'failed';

function downloadBlob(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}

function truncate(s: string, max: number) {
  return s.length > max ? s.slice(0, max) + '\u2026' : s;
}

function statusTag(status?: string) {
  const s = (status || 'uploaded').toLowerCase();
  if (s === 'ready' || s === 'parsed') return { cls: 'rc-badge rc-badge--success', label: 'Ready' };
  if (s === 'processing' || s === 'queued') return { cls: 'rc-badge rc-badge--info', label: 'Processing' };
  if (s === 'failed') return { cls: 'rc-badge rc-badge--danger', label: 'Failed' };
  return { cls: 'rc-badge', label: 'Pending' };
}

function matchesFilter(p: PaperRow, f: StatusFilter): boolean {
  if (f === 'all') return true;
  const s = (p.processing_status || 'uploaded').toLowerCase();
  if (f === 'ready') return s === 'ready' || s === 'parsed';
  if (f === 'processing') return s === 'processing' || s === 'queued';
  if (f === 'failed') return s === 'failed';
  if (f === 'pending') return s === 'uploaded' || !p.processing_status;
  return true;
}

export default function PapersPage() {
  const { projectId } = useParams();
  const toast = useToast();
  const confirm = useConfirm();

  const [papers, setPapers] = useState<PaperRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const [uploadOpen, setUploadOpen] = useState(false);
  const [uploadTab, setUploadTab] = useState<'upload' | 'doi'>('upload');
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [doi, setDoi] = useState('');
  const [pmid, setPmid] = useState('');
  const [downloading, setDownloading] = useState(false);

  const [processingAll, setProcessingAll] = useState(false);
  const [dismissBanner, setDismissBanner] = useState(false);
  const pollRef = useRef<number | null>(null);

  // Pagination
  const LIB_PAGE_SIZE = 25;
  const [libPage, setLibPage] = useState(0);

  const load = useCallback(async () => {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    try {
      const rp = await api.get(`/projects/${projectId}/library`);
      setPapers(rp.data as PaperRow[]);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Error cargando papers');
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    if (!loading && papers.length === 0) setUploadOpen(true);
  }, [loading, papers.length]);

  const hasProcessing = useMemo(
    () => papers.some(p => ['processing', 'queued'].includes((p.processing_status || '').toLowerCase())),
    [papers]
  );

  useEffect(() => {
    if (!hasProcessing || dismissBanner) {
      if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
      return;
    }
    pollRef.current = window.setInterval(() => { load(); }, 5000);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [hasProcessing, dismissBanner, load]);

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    return papers.filter(p => {
      if (!matchesFilter(p, statusFilter)) return false;
      if (q && !p.title.toLowerCase().includes(q) && !(p.authors || '').toLowerCase().includes(q)) return false;
      return true;
    });
  }, [papers, search, statusFilter]);

  // Reset page when filter/search changes
  useEffect(() => { setLibPage(0); }, [search, statusFilter]);

  const allSelected = filtered.length > 0 && filtered.every(p => selected.has(p.id));
  function toggleAll() {
    if (allSelected) setSelected(new Set());
    else setSelected(new Set(filtered.map(p => p.id)));
  }
  function toggleOne(id: string) {
    setSelected(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  async function upload() {
    if (!projectId || !uploadFile) return;
    setUploading(true); setError(null);
    try {
      const form = new FormData();
      form.append('project_id', projectId);
      form.append('file', uploadFile);
      const r = await api.post('/papers/upload', form, { headers: { 'Content-Type': 'multipart/form-data' } });
      toast.info((r.data as any)?.duplicate ? 'Duplicado' : 'Subido', (r.data as any)?.duplicate ? 'El paper ya existe.' : 'PDF subido.');
      setUploadFile(null);
      await load();
    } catch (e: any) { setError(e?.response?.data?.detail || 'Error al subir'); }
    finally { setUploading(false); }
  }

  async function downloadOA() {
    if (!projectId) return;
    setDownloading(true); setError(null);
    try {
      const payload: any = { project_id: projectId };
      if (doi.trim()) payload.doi = doi.trim();
      if (pmid.trim()) payload.pmid = pmid.trim();
      await api.post('/papers/download', payload);
      toast.success('Descarga solicitada', 'OA resolver job iniciado.');
      setDoi(''); setPmid('');
      await load();
    } catch (e: any) { setError(e?.response?.data?.detail || 'Descarga fallida'); }
    finally { setDownloading(false); }
  }

  async function downloadFile(p: PaperRow) {
    try {
      const r = await api.get(`/papers/${p.id}/download`, { responseType: 'blob' });
      downloadBlob(r.data as Blob, p.filename || 'paper.pdf');
    } catch (e: any) { setError(e?.response?.data?.detail || 'Error descargando archivo'); }
  }

  async function processPaper(p: PaperRow) {
    try {
      await api.post(`/papers/${p.id}/process`);
      toast.success('Encolado', `Procesando: ${truncate(p.title, 30)}`);
      await load();
    } catch (e: any) { setError(e?.response?.data?.detail || 'Error al procesar'); }
  }

  async function toggleFavorite(p: PaperRow) {
    try {
      const r = await api.patch(`/papers/${p.id}/favorite`);
      setPapers(prev => prev.map(pp => pp.id === p.id ? { ...pp, favorite: (r.data as any).favorite } : pp));
    } catch (e: any) { setError(e?.response?.data?.detail || 'Error al cambiar favorito'); }
  }

  async function deletePaper(p: PaperRow) {
    const ok = await confirm({ title: '\u00bfEliminar paper?', body: p.title, confirmText: 'Eliminar', danger: true });
    if (!ok) return;
    try { await api.delete(`/papers/${p.id}`); await load(); }
    catch (e: any) { setError(e?.response?.data?.detail || 'Error al eliminar'); }
  }

  async function processAllPending() {
    const pending = papers.filter(p => {
      const s = (p.processing_status || 'uploaded').toLowerCase();
      return s !== 'ready' && s !== 'parsed' && s !== 'processing' && s !== 'queued';
    });
    if (pending.length === 0) { toast.info('Nada pendiente', 'Todos ya procesados o en cola.'); return; }
    setProcessingAll(true); setDismissBanner(false);
    for (const p of pending) {
      try { await api.post(`/papers/${p.id}/process`); } catch { /* continuar */ }
      await new Promise(r => setTimeout(r, 500));
    }
    toast.success('Encolados', `${pending.length} papers enviados a procesar.`);
    setProcessingAll(false);
    await load();
  }

  const canDownload = Boolean(projectId && (doi.trim() || pmid.trim()));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div>
        <h1 className="rc-page-title">Library</h1>
        <div className="rc-subtitle">Curate PDFs, deduplicate sources, process full text and build a reusable project library.</div>
      </div>

      {hasProcessing && !dismissBanner && (
        <div className="rc-card" style={{ background: 'rgba(59,130,246,0.08)', border: '1px solid rgba(59,130,246,0.2)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: 13 }}>{'\u2699\uFE0F'} Procesando {papers.filter(p => ['processing', 'queued'].includes((p.processing_status || '').toLowerCase())).length} papers... (auto-refreshing)</span>
          <button className="rc-btn" style={{ padding: '4px 10px', fontSize: 11 }} onClick={() => setDismissBanner(true)}>{'\u2715'}</button>
        </div>
      )}

      {error && <div className="rc-error">{String(error)}</div>}

      {/* Upload panel colapsable */}
      <div className="rc-card" style={{ padding: uploadOpen ? 14 : '10px 14px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }} onClick={() => setUploadOpen(!uploadOpen)}>
          <span style={{ fontWeight: 800, fontSize: 13 }}>+ Add papers</span>
          <span style={{ fontSize: 11, opacity: 0.6 }}>{uploadOpen ? '\u25B2 Collapse' : '\u25BC Expand'}</span>
        </div>
        {uploadOpen && (
          <div style={{ marginTop: 12 }}>
            <div className="rc-row" style={{ gap: 4, marginBottom: 10 }}>
              <button className={`rc-btn ${uploadTab === 'upload' ? 'rc-btn--primary' : ''}`} style={{ padding: '6px 14px', fontSize: 12 }} onClick={() => setUploadTab('upload')}>Upload PDF</button>
              <button className={`rc-btn ${uploadTab === 'doi' ? 'rc-btn--primary' : ''}`} style={{ padding: '6px 14px', fontSize: 12 }} onClick={() => setUploadTab('doi')}>Download by DOI/PMID</button>
            </div>
            {uploadTab === 'upload' ? (
              <div className="rc-row" style={{ alignItems: 'center' }}>
                <input type="file" accept="application/pdf" onChange={e => setUploadFile(e.target.files?.[0] || null)} />
                <button className="rc-btn rc-btn--primary" disabled={!uploadFile || uploading} onClick={upload} style={{ padding: '8px 14px', fontSize: 13 }}>
                  {uploading ? 'Subiendo...' : 'Upload'}
                </button>
              </div>
            ) : (
              <div className="rc-row" style={{ alignItems: 'flex-end' }}>
                <div style={{ minWidth: 200 }}>
                  <div className="rc-kicker">DOI</div>
                  <input className="rc-input" value={doi} onChange={e => setDoi(e.target.value)} placeholder="10.xxxx/xxxxx" />
                </div>
                <div style={{ width: 160 }}>
                  <div className="rc-kicker">PMID</div>
                  <input className="rc-input" value={pmid} onChange={e => setPmid(e.target.value)} placeholder="12345678" />
                </div>
                <button className="rc-btn rc-btn--primary" disabled={!canDownload || downloading} onClick={downloadOA} style={{ padding: '8px 14px', fontSize: 13 }}>
                  {downloading ? 'Descargando...' : 'Download'}
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Toolbar */}
      <div className="rc-row" style={{ justifyContent: 'space-between' }}>
        <div className="rc-row" style={{ gap: 8 }}>
          <input className="rc-input" style={{ width: 220, padding: '8px 12px', fontSize: 13 }} placeholder="Buscar titulo o autores..." value={search} onChange={e => setSearch(e.target.value)} />
          <select className="rc-input" style={{ width: 140, padding: '8px 10px', fontSize: 13 }} value={statusFilter} onChange={e => setStatusFilter(e.target.value as StatusFilter)}>
            <option value="all">All</option>
            <option value="ready">Ready</option>
            <option value="processing">Processing</option>
            <option value="pending">Pending</option>
            <option value="failed">Failed</option>
          </select>
          <button className="rc-btn" style={{ padding: '8px 12px', fontSize: 12 }} onClick={processAllPending} disabled={processingAll}>
            {processingAll ? 'Encolando...' : 'Process all pending'}
          </button>
          <button className="rc-btn" onClick={load} disabled={loading} style={{ padding: '8px 12px', fontSize: 12 }}>{loading ? '...' : '\u21BB'}</button>
        </div>
        <span className="rc-help" style={{ whiteSpace: 'nowrap' }}>{filtered.length} paper{filtered.length !== 1 ? 's' : ''}</span>
      </div>

      {loading && papers.length === 0 ? (
        <div className="rc-card"><Skeleton height={14} width="55%" /><div style={{ height: 10 }} /><SkeletonLines lines={6} lineHeight={12} lastLineWidth="50%" /></div>
      ) : null}

      {!loading && papers.length === 0 ? (
        <div className="rc-card" style={{ textAlign: 'center', padding: 32 }}>
          <div style={{ fontSize: 32, marginBottom: 8 }}>{'\uD83D\uDCC4'}</div>
          <div style={{ fontWeight: 800, marginBottom: 4 }}>No papers yet</div>
          <div className="rc-help">Upload a PDF or download by DOI/PMID to get started.</div>
        </div>
      ) : null}

      {filtered.length > 0 && (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '2px solid var(--rc-border)', textAlign: 'left' }}>
                <th style={{ padding: '8px 6px', width: 32 }}><input type="checkbox" checked={allSelected} onChange={toggleAll} /></th>
                <th style={{ padding: '8px 6px' }}>Title</th>
                <th style={{ padding: '8px 6px', width: 160 }}>Journal &middot; Year</th>
                <th style={{ padding: '8px 6px', width: 100 }}>Status</th>
                <th style={{ padding: '8px 6px', width: 100 }}>Source</th>
                <th style={{ padding: '8px 6px', width: 200 }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.slice(libPage * LIB_PAGE_SIZE, (libPage + 1) * LIB_PAGE_SIZE).map(p => {
                const st = statusTag(p.processing_status);
                const isReady = ['ready', 'parsed'].includes((p.processing_status || '').toLowerCase());
                return (
                  <tr key={p.id} style={{ borderBottom: '1px solid var(--rc-border)' }}>
                    <td style={{ padding: '8px 6px' }}><input type="checkbox" checked={selected.has(p.id)} onChange={() => toggleOne(p.id)} /></td>
                    <td style={{ padding: '8px 6px' }}>
                      <div title={p.title} style={{ fontWeight: 700, lineHeight: 1.3 }}>{truncate(p.title, 45)}</div>
                      {p.authors && <div style={{ fontSize: 11, color: 'var(--rc-muted)', marginTop: 2 }}>{truncate(p.authors, 60)}</div>}
                    </td>
                    <td style={{ padding: '8px 6px', fontStyle: 'italic', fontSize: 12 }}>
                      {[p.journal, p.publication_year].filter(Boolean).join(' \u00B7 ') || '\u2014'}
                    </td>
                    <td style={{ padding: '8px 6px' }}>
                      <span className={st.cls} style={{ fontSize: 11 }}>
                        {st.label === 'Processing' && <span style={{ display: 'inline-block', width: 8, height: 8, border: '2px solid rgba(59,130,246,0.4)', borderTopColor: 'rgba(59,130,246,1)', borderRadius: '50%', animation: 'spin .8s linear infinite', marginRight: 4 }} />}
                        {st.label}
                      </span>
                    </td>
                    <td style={{ padding: '8px 6px' }}>
                      {p.source_provider ? <span className="rc-badge" style={{ fontSize: 11 }}>{p.source_provider}</span> : <span className="rc-help">{'\u2014'}</span>}
                    </td>
                    <td style={{ padding: '8px 6px' }}>
                      <div className="rc-row" style={{ gap: 4 }}>
                        {!isReady && <button className="rc-btn" style={{ padding: '4px 8px', fontSize: 11 }} onClick={() => processPaper(p)}>Process</button>}
                        <button className="rc-btn" style={{ padding: '4px 8px', fontSize: 11 }} onClick={() => downloadFile(p)}>Download</button>
                        <button className="rc-btn" style={{ padding: '4px 8px', fontSize: 11, color: p.favorite ? '#eab308' : undefined }} onClick={() => toggleFavorite(p)} title={p.favorite ? 'Quitar favorito' : 'Marcar favorito'}>
                          {p.favorite ? '\u2605' : '\u2606'}
                        </button>
                        <button className="rc-btn" style={{ padding: '4px 8px', fontSize: 11, color: 'var(--rc-danger)' }} onClick={() => deletePaper(p)}>Del</button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {/* Library pagination */}
          {(() => {
            const totalPages = Math.ceil(filtered.length / LIB_PAGE_SIZE);
            if (totalPages <= 1) return null;
            return (
              <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 12, padding: '12px 0' }}>
                <button className="rc-btn" disabled={libPage === 0} onClick={() => setLibPage((p) => Math.max(0, p - 1))} style={{ padding: '4px 12px', fontSize: 12 }}>
                  ← Prev
                </button>
                <span style={{ fontSize: 13, color: 'var(--rc-muted)' }}>
                  Page {libPage + 1} of {totalPages} ({filtered.length} papers)
                </span>
                <button className="rc-btn" disabled={libPage >= totalPages - 1} onClick={() => setLibPage((p) => Math.min(totalPages - 1, p + 1))} style={{ padding: '4px 12px', fontSize: 12 }}>
                  Next →
                </button>
              </div>
            );
          })()}
        </div>
      )}

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
