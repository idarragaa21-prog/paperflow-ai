import { useMemo, useState, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { useToast } from '../ui/Toast/ToastProvider';
import { useConfirm } from '../ui/Dialog/useConfirm';
import { Skeleton, SkeletonLines } from '../ui/Skeleton/Skeleton';
import type { PaperRow } from '../types/api';

type StatusFilter = 'all' | 'ready' | 'processing' | 'pending' | 'failed';

const LIB_PAGE_SIZE = 25;

function downloadBlob(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click(); a.remove();
  window.URL.revokeObjectURL(url);
}

function truncate(s: string, max: number) { return s.length > max ? s.slice(0, max) + '…' : s; }

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
  const qc = useQueryClient();

  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [uploadOpen, setUploadOpen] = useState(false);
  const [uploadTab, setUploadTab] = useState<'upload' | 'doi'>('upload');
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [doi, setDoi] = useState('');
  const [pmid, setPmid] = useState('');
  const [dismissBanner, setDismissBanner] = useState(false);
  const [libPage, setLibPage] = useState(0);
  const [mutError, setMutError] = useState<string | null>(null);
  const processingAllRef = useRef(false);

  // ── Main query — auto-polls while papers are processing ──────────────────
  const papersKey = ['papers', projectId];
  const { data: papers = [], isLoading, error: queryError } = useQuery<PaperRow[]>({
    queryKey: papersKey,
    queryFn: async () => {
      const r = await api.get(`/projects/${projectId}/library`);
      return r.data as PaperRow[];
    },
    enabled: Boolean(projectId),
    refetchInterval: (query) => {
      const rows = query.state.data ?? [];
      const hasProcessing = rows.some(p => ['processing', 'queued'].includes((p.processing_status || '').toLowerCase()));
      return hasProcessing && !dismissBanner ? 5000 : false;
    },
  });

  const invalidate = () => qc.invalidateQueries({ queryKey: papersKey });

  // ── Mutations ─────────────────────────────────────────────────────────────
  const uploadMut = useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData();
      form.append('project_id', projectId!);
      form.append('file', file);
      return api.post('/papers/upload', form, { headers: { 'Content-Type': 'multipart/form-data' } });
    },
    onSuccess: (r) => {
      toast.info((r.data as any)?.duplicate ? 'Duplicado' : 'Subido', (r.data as any)?.duplicate ? 'El paper ya existe.' : 'PDF subido.');
      setUploadFile(null);
      invalidate();
    },
    onError: (e: any) => setMutError(e?.response?.data?.detail || 'Error al subir'),
  });

  const downloadOAMut = useMutation({
    mutationFn: async () => {
      const payload: any = { project_id: projectId };
      if (doi.trim()) payload.doi = doi.trim();
      if (pmid.trim()) payload.pmid = pmid.trim();
      return api.post('/papers/download', payload);
    },
    onSuccess: () => {
      toast.success('Descarga solicitada', 'OA resolver job iniciado.');
      setDoi(''); setPmid('');
      invalidate();
    },
    onError: (e: any) => setMutError(e?.response?.data?.detail || 'Descarga fallida'),
  });

  const processMut = useMutation({
    mutationFn: (paperId: string) => api.post(`/papers/${paperId}/process`),
    onSuccess: (_, paperId) => {
      const p = papers.find(x => x.id === paperId);
      toast.success('Encolado', p ? `Procesando: ${truncate(p.title, 30)}` : 'Encolado');
      invalidate();
    },
    onError: (e: any) => setMutError(e?.response?.data?.detail || 'Error al procesar'),
  });

  const favoriteMut = useMutation({
    mutationFn: async (p: PaperRow) => {
      const r = await api.patch(`/papers/${p.id}/favorite`);
      return { id: p.id, favorite: (r.data as any).favorite };
    },
    onSuccess: ({ id, favorite }) => {
      qc.setQueryData<PaperRow[]>(papersKey, (prev) =>
        (prev ?? []).map(p => p.id === id ? { ...p, favorite } : p)
      );
    },
    onError: (e: any) => setMutError(e?.response?.data?.detail || 'Error al cambiar favorito'),
  });

  const deleteMut = useMutation({
    mutationFn: (paperId: string) => api.delete(`/papers/${paperId}`),
    onSuccess: () => invalidate(),
    onError: (e: any) => setMutError(e?.response?.data?.detail || 'Error al eliminar'),
  });

  // ── Derived state ─────────────────────────────────────────────────────────
  const hasProcessing = useMemo(
    () => papers.some(p => ['processing', 'queued'].includes((p.processing_status || '').toLowerCase())),
    [papers],
  );

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    return papers.filter(p => {
      if (!matchesFilter(p, statusFilter)) return false;
      if (q && !p.title.toLowerCase().includes(q) && !(p.authors || '').toLowerCase().includes(q)) return false;
      return true;
    });
  }, [papers, search, statusFilter]);

  const allSelected = filtered.length > 0 && filtered.every(p => selected.has(p.id));
  function toggleAll() { setSelected(allSelected ? new Set() : new Set(filtered.map(p => p.id))); }
  function toggleOne(id: string) {
    setSelected(prev => { const n = new Set(prev); n.has(id) ? n.delete(id) : n.add(id); return n; });
  }

  async function downloadFile(p: PaperRow) {
    try {
      const r = await api.get(`/papers/${p.id}/download`, { responseType: 'blob' });
      downloadBlob(r.data as Blob, p.filename || 'paper.pdf');
    } catch (e: any) { setMutError(e?.response?.data?.detail || 'Error descargando archivo'); }
  }

  async function deleteWithConfirm(p: PaperRow) {
    const ok = await confirm({ title: '¿Eliminar paper?', body: p.title, confirmText: 'Eliminar', danger: true });
    if (!ok) return;
    deleteMut.mutate(p.id);
  }

  async function processAllPending() {
    if (processingAllRef.current) return;
    const pending = papers.filter(p => {
      const s = (p.processing_status || 'uploaded').toLowerCase();
      return s !== 'ready' && s !== 'parsed' && s !== 'processing' && s !== 'queued';
    });
    if (!pending.length) { toast.info('Nada pendiente', 'Todos ya procesados o en cola.'); return; }
    processingAllRef.current = true;
    setDismissBanner(false);
    for (const p of pending) {
      try { await api.post(`/papers/${p.id}/process`); } catch { /* continuar */ }
      await new Promise(r => setTimeout(r, 500));
    }
    toast.success('Encolados', `${pending.length} papers enviados a procesar.`);
    processingAllRef.current = false;
    invalidate();
  }

  const errorMsg = mutError || (queryError as any)?.message;
  const totalPages = Math.ceil(filtered.length / LIB_PAGE_SIZE);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div>
        <h1 className="rc-page-title">Library</h1>
        <div className="rc-subtitle">Curate PDFs, deduplicate sources, process full text and build a reusable project library.</div>
      </div>

      {hasProcessing && !dismissBanner && (
        <div className="rc-card" style={{ background: 'rgba(59,130,246,0.08)', border: '1px solid rgba(59,130,246,0.2)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: 13 }}>⚙️ Procesando {papers.filter(p => ['processing','queued'].includes((p.processing_status||'').toLowerCase())).length} papers... (auto-refreshing)</span>
          <button className="rc-btn" style={{ padding: '4px 10px', fontSize: 11 }} onClick={() => setDismissBanner(true)}>✕</button>
        </div>
      )}

      {errorMsg && <div className="rc-error">{String(errorMsg)}</div>}

      {/* ── Upload panel ── */}
      <div className="rc-card" style={{ padding: uploadOpen ? 14 : '10px 14px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }} onClick={() => setUploadOpen(!uploadOpen)}>
          <span style={{ fontWeight: 800, fontSize: 13 }}>+ Add papers</span>
          <span style={{ fontSize: 11, opacity: 0.6 }}>{uploadOpen ? '▲ Collapse' : '▼ Expand'}</span>
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
                <button className="rc-btn rc-btn--primary" disabled={!uploadFile || uploadMut.isPending} onClick={() => uploadFile && uploadMut.mutate(uploadFile)} style={{ padding: '8px 14px', fontSize: 13 }}>
                  {uploadMut.isPending ? 'Subiendo...' : 'Upload'}
                </button>
              </div>
            ) : (
              <div className="rc-row" style={{ alignItems: 'flex-end' }}>
                <div style={{ minWidth: 200 }}><div className="rc-kicker">DOI</div><input className="rc-input" value={doi} onChange={e => setDoi(e.target.value)} placeholder="10.xxxx/xxxxx" /></div>
                <div style={{ width: 160 }}><div className="rc-kicker">PMID</div><input className="rc-input" value={pmid} onChange={e => setPmid(e.target.value)} placeholder="12345678" /></div>
                <button className="rc-btn rc-btn--primary" disabled={!(doi.trim() || pmid.trim()) || downloadOAMut.isPending} onClick={() => downloadOAMut.mutate()} style={{ padding: '8px 14px', fontSize: 13 }}>
                  {downloadOAMut.isPending ? 'Descargando...' : 'Download'}
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── Toolbar ── */}
      <div className="rc-row" style={{ justifyContent: 'space-between' }}>
        <div className="rc-row" style={{ gap: 8 }}>
          <input className="rc-input" style={{ width: 220, padding: '8px 12px', fontSize: 13 }} placeholder="Buscar título o autores..." value={search} onChange={e => { setSearch(e.target.value); setLibPage(0); }} />
          <select className="rc-input" style={{ width: 140, padding: '8px 10px', fontSize: 13 }} value={statusFilter} onChange={e => { setStatusFilter(e.target.value as StatusFilter); setLibPage(0); }}>
            <option value="all">All</option>
            <option value="ready">Ready</option>
            <option value="processing">Processing</option>
            <option value="pending">Pending</option>
            <option value="failed">Failed</option>
          </select>
          <button className="rc-btn" style={{ padding: '8px 12px', fontSize: 12 }} onClick={processAllPending}>Process all pending</button>
          <button className="rc-btn" onClick={() => invalidate()} disabled={isLoading} style={{ padding: '8px 12px', fontSize: 12 }}>{isLoading ? '...' : '↻'}</button>
        </div>
        <span className="rc-help" style={{ whiteSpace: 'nowrap' }}>{filtered.length} paper{filtered.length !== 1 ? 's' : ''}</span>
      </div>

      {isLoading && papers.length === 0 && (
        <div className="rc-card"><Skeleton height={14} width="55%" /><div style={{ height: 10 }} /><SkeletonLines lines={6} lineHeight={12} lastLineWidth="50%" /></div>
      )}

      {!isLoading && papers.length === 0 && (
        <div className="rc-card" style={{ textAlign: 'center', padding: '48px 24px' }}>
          <svg width="56" height="56" viewBox="0 0 56 56" fill="none" style={{ margin: '0 auto 16px', display: 'block' }}>
            <rect x="8" y="10" width="32" height="40" rx="4" fill="rgba(16,185,129,0.07)" stroke="rgba(16,185,129,0.2)" strokeWidth="1.5"/>
            <rect x="16" y="4" width="32" height="40" rx="4" fill="var(--rc-surface)" stroke="rgba(16,185,129,0.22)" strokeWidth="1.5"/>
            <line x1="24" y1="16" x2="38" y2="16" stroke="rgba(16,185,129,0.35)" strokeWidth="1.5" strokeLinecap="round"/>
            <line x1="24" y1="22" x2="38" y2="22" stroke="rgba(16,185,129,0.35)" strokeWidth="1.5" strokeLinecap="round"/>
            <line x1="24" y1="28" x2="33" y2="28" stroke="rgba(16,185,129,0.2)" strokeWidth="1.5" strokeLinecap="round"/>
          </svg>
          <div style={{ fontWeight: 750, fontSize: 15, fontFamily: 'var(--font-display)', letterSpacing: '-0.02em', marginBottom: 6 }}>No papers yet</div>
          <div className="rc-help">Upload a PDF or download by DOI/PMID to get started.</div>
        </div>
      )}

      {filtered.length > 0 && (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '2px solid var(--rc-border)', textAlign: 'left' }}>
                <th style={{ padding: '8px 6px', width: 32 }}><input type="checkbox" checked={allSelected} onChange={toggleAll} /></th>
                <th style={{ padding: '8px 6px' }}>Title</th>
                <th style={{ padding: '8px 6px', width: 160 }}>Journal · Year</th>
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
                      {[p.journal, p.publication_year].filter(Boolean).join(' · ') || '—'}
                    </td>
                    <td style={{ padding: '8px 6px' }}>
                      <span className={st.cls} style={{ fontSize: 11 }}>
                        {st.label === 'Processing' && <span style={{ display: 'inline-block', width: 8, height: 8, border: '2px solid rgba(59,130,246,0.4)', borderTopColor: 'rgba(59,130,246,1)', borderRadius: '50%', animation: 'spin .8s linear infinite', marginRight: 4 }} />}
                        {st.label}
                      </span>
                    </td>
                    <td style={{ padding: '8px 6px' }}>
                      {p.source_provider ? <span className="rc-badge" style={{ fontSize: 11 }}>{p.source_provider}</span> : <span className="rc-help">—</span>}
                    </td>
                    <td style={{ padding: '8px 6px' }}>
                      <div className="rc-row" style={{ gap: 4 }}>
                        {!isReady && <button className="rc-btn" style={{ padding: '4px 8px', fontSize: 11 }} onClick={() => processMut.mutate(p.id)}>Process</button>}
                        <button className="rc-btn" style={{ padding: '4px 8px', fontSize: 11 }} onClick={() => downloadFile(p)}>Download</button>
                        <button className="rc-btn" style={{ padding: '4px 8px', fontSize: 11, color: p.favorite ? '#eab308' : undefined }} onClick={() => favoriteMut.mutate(p)} title={p.favorite ? 'Quitar favorito' : 'Favorito'}>
                          {p.favorite ? '★' : '☆'}
                        </button>
                        <button className="rc-btn" style={{ padding: '4px 8px', fontSize: 11, color: 'var(--rc-danger)' }} onClick={() => deleteWithConfirm(p)}>Del</button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {totalPages > 1 && (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 12, padding: '12px 0' }}>
              <button className="rc-btn" disabled={libPage === 0} onClick={() => setLibPage(p => Math.max(0, p - 1))} style={{ padding: '4px 12px', fontSize: 12 }}>← Prev</button>
              <span style={{ fontSize: 13, color: 'var(--rc-muted)' }}>Page {libPage + 1} of {totalPages} ({filtered.length} papers)</span>
              <button className="rc-btn" disabled={libPage >= totalPages - 1} onClick={() => setLibPage(p => Math.min(totalPages - 1, p + 1))} style={{ padding: '4px 12px', fontSize: 12 }}>Next →</button>
            </div>
          )}
        </div>
      )}

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
