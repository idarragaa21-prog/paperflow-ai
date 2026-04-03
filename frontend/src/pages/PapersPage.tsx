import { Fragment, useMemo, useState, useRef } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { useToast } from '../ui/Toast/ToastProvider';
import { useConfirm } from '../ui/Dialog/useConfirm';
import { Skeleton, SkeletonLines } from '../ui/Skeleton/Skeleton';
import type { PaperDetailResponse, PaperDownloadTrace, PaperRow } from '../types/api';
import { InsightCard, PageHero } from '../components/WorkflowPrimitives';

type StatusFilter = 'all' | 'ready' | 'processing' | 'pending' | 'failed';

const LIB_PAGE_SIZE = 25;
const SOURCE_LABELS: Record<string, string> = {
  pubmed: 'PubMed',
  europepmc: 'Europe PMC',
  doaj: 'DOAJ',
  unpaywall: 'Unpaywall',
  doi_content_negotiation: 'DOI direct',
  manual_upload: 'Carga manual',
  user_provided_oa: 'OA provista',
};

type PaperTraceState = {
  expanded: boolean;
  loading?: boolean;
  error?: string | null;
  trace?: PaperDownloadTrace | null;
};

function downloadBlob(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click(); a.remove();
  window.URL.revokeObjectURL(url);
}

function truncate(s: string, max: number) { return s.length > max ? s.slice(0, max) + '…' : s; }

function providerLabel(source?: string | null) {
  return SOURCE_LABELS[String(source || '').toLowerCase()] || 'Fuente externa';
}

function traceStatusLabel(status: PaperDownloadTrace['final_status']) {
  if (status === 'downloaded') return 'Descargado';
  if (status === 'existing') return 'Ya existía';
  if (status === 'unavailable') return 'No disponible';
  return 'Fallido';
}

function errorDetail(error: unknown, fallback: string) {
  if (typeof error === 'object' && error && 'response' in error) {
    const detail = (error as { response?: { data?: { detail?: string } } }).response?.data?.detail;
    if (detail) return detail;
  }
  return error instanceof Error ? error.message : fallback;
}

function formatDate(value?: string | null) {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function statusTag(status?: string) {
  const s = (status || 'uploaded').toLowerCase();
  if (s === 'ready' || s === 'parsed') return { cls: 'rc-badge rc-badge--success', label: 'Ready', style: { background: 'rgba(16,185,129,0.1)', color: '#059669', border: '1px solid rgba(16,185,129,0.25)', fontWeight: 800 } };
  if (s === 'processing' || s === 'queued') return { cls: 'rc-badge rc-badge--info', label: 'Processing', style: { background: 'rgba(59,130,246,0.1)', color: '#2563eb', border: '1px solid rgba(59,130,246,0.25)', fontWeight: 600 } };
  if (s === 'failed') return { cls: 'rc-badge rc-badge--danger', label: 'Failed', style: { background: 'rgba(239,68,68,0.1)', color: '#dc2626', border: '1px solid rgba(239,68,68,0.25)', fontWeight: 600 } };
  return { cls: 'rc-badge', label: 'Pending', style: { background: 'var(--rc-surface-2)', border: '1px solid var(--rc-border)', fontWeight: 600 } };
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
  const [traceState, setTraceState] = useState<Record<string, PaperTraceState>>({});
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
    onError: (e: any) => { toast.error('Error al subir', e?.response?.data?.detail || 'El sistema de procesamiento no está disponible en este momento. Por favor, intenta de nuevo más tarde.'); setMutError(e?.response?.data?.detail || 'Error al subir'); },
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
    onError: (e: any) => { toast.error('Error al descargar', e?.response?.data?.detail || 'El sistema de procesamiento no está disponible en este momento. Por favor, intenta de nuevo más tarde.'); setMutError(e?.response?.data?.detail || 'Descarga fallida'); },
  });

  const processMut = useMutation({
    mutationFn: (paperId: string) => api.post(`/papers/${paperId}/process`),
    onSuccess: (_, paperId) => {
      const p = papers.find(x => x.id === paperId);
      toast.success('Encolado', p ? `Procesando: ${truncate(p.title, 30)}` : 'Encolado');
      invalidate();
    },
    onError: (e: any) => { toast.error('Error al procesar', e?.response?.data?.detail || 'El sistema de procesamiento no está disponible en este momento. Por favor, intenta de nuevo más tarde.'); setMutError(e?.response?.data?.detail || 'Error al procesar'); },
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
  const readyCount = useMemo(
    () => papers.filter(p => ['ready', 'parsed'].includes((p.processing_status || '').toLowerCase())).length,
    [papers],
  );
  const pendingCount = useMemo(
    () => papers.filter(p => ['uploaded', ''].includes((p.processing_status || '').toLowerCase())).length,
    [papers],
  );
  const failedCount = useMemo(
    () => papers.filter(p => (p.processing_status || '').toLowerCase() === 'failed').length,
    [papers],
  );
  const processingCount = useMemo(
    () => papers.filter(p => ['processing', 'queued'].includes((p.processing_status || '').toLowerCase())).length,
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
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }

  function patchTraceState(id: string, patch: Partial<PaperTraceState>) {
    setTraceState((prev) => ({ ...prev, [id]: { ...(prev[id] || { expanded: false }), ...patch } }));
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

  async function toggleTrace(p: PaperRow) {
    const current = traceState[p.id];
    if (current?.expanded) {
      patchTraceState(p.id, { expanded: false });
      return;
    }

    patchTraceState(p.id, { expanded: true });
    if (current?.trace || current?.loading) return;

    patchTraceState(p.id, { loading: true, error: null });
    try {
      const response = await api.get(`/papers/${p.id}`);
      const detail = response.data as PaperDetailResponse;
      patchTraceState(p.id, { loading: false, trace: detail.download_trace || null });
    } catch (error: unknown) {
      patchTraceState(p.id, {
        loading: false,
        error: errorDetail(error, 'No se pudo cargar la traza de descarga'),
      });
    }
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
  const selectedRows = filtered.filter((paper) => selected.has(paper.id)).slice(0, 5);
  const selectedReadyCount = filtered.filter((paper) => selected.has(paper.id) && ['ready', 'parsed'].includes((paper.processing_status || '').toLowerCase())).length;
  const readyRatio = papers.length > 0 ? Math.round((readyCount / papers.length) * 100) : 0;

  return (
    <div className="rc-page-enter" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <PageHero
        eyebrow="Stage 2 · Library"
        title="Library"
        subtitle="The library is where discovery becomes a working corpus. Add sources, process them, inspect traces and hand off the best papers to Reader and Extraction."
        metrics={[
          { label: 'papers in library', value: papers.length, tone: 'primary' },
          { label: 'ready to use', value: readyCount, tone: 'success' },
          { label: 'pending process', value: pendingCount, tone: 'warning' },
          { label: 'failed', value: failedCount, tone: 'neutral' },
        ]}
      />

      <div className="rc-list-stagger" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(220px,1fr))', gap: 12 }}>
        <InsightCard
          eyebrow="Add"
          title="Bring papers in"
          body="Upload PDFs or resolve OA content by DOI/PMID. This is the intake lane for the project."
          tone="primary"
          action={<button className="rc-btn rc-btn--sm" onClick={() => setUploadOpen(!uploadOpen)}>{uploadOpen ? 'Hide intake' : 'Open intake'}</button>}
        />
        <InsightCard
          eyebrow="Process"
          title="Queue the full-text pipeline"
          body={hasProcessing ? 'The pipeline is currently processing papers. Auto-refresh is enabled while jobs run.' : 'Run processing on pending papers to unlock Reader and Extraction.'}
          tone="warning"
          action={<button className="rc-btn rc-btn--sm" onClick={processAllPending}>Process pending</button>}
        />
        <InsightCard
          eyebrow="Review"
          title="Check readiness and trace"
          body="Use status, source and download trace to verify what is actually usable before you rely on it downstream."
          tone="neutral"
        />
        <InsightCard
          eyebrow="Use"
          title="Send the library downstream"
          body="Once enough papers are ready, move into Reader for grounded questioning or Extraction for structured evidence."
          tone="success"
          action={(
            <div className="rc-row" style={{ gap: 6 }}>
              <Link className="rc-btn rc-btn--sm" style={{ textDecoration: 'none' }} to={`/projects/${projectId}/reader`}>Reader</Link>
              <Link className="rc-btn rc-btn--sm" style={{ textDecoration: 'none' }} to={`/projects/${projectId}/meta`}>Extract</Link>
            </div>
          )}
        />
      </div>

      {hasProcessing && !dismissBanner && (
        <div className="rc-card" style={{ background: 'var(--rc-info-bg)', border: '1px solid var(--rc-info-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: 13 }}>⚙️ Procesando {papers.filter(p => ['processing','queued'].includes((p.processing_status||'').toLowerCase())).length} papers... (auto-refreshing)</span>
          <button className="rc-btn" aria-label="Dismiss banner" title="Dismiss banner" style={{ padding: '4px 10px', fontSize: 11 }} onClick={() => setDismissBanner(true)}>✕</button>
        </div>
      )}

      {errorMsg && <div className="rc-error">{String(errorMsg)}</div>}

      <div className="rc-composer-shell">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      {/* ── Upload panel ── */}
      <div className="rc-card" style={{ padding: uploadOpen ? 14 : '10px 14px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }} onClick={() => setUploadOpen(!uploadOpen)}>
          <span style={{ fontWeight: 800, fontSize: 13 }}>Add papers to the library</span>
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
        <div className="rc-card" style={{ textAlign: 'center', padding: 32 }}>
          <div style={{ fontSize: 32, marginBottom: 8 }}>📄</div>
          <div style={{ fontWeight: 800, marginBottom: 4 }}>No papers yet</div>
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
                  <Fragment key={p.id}>
                    <tr style={{ borderBottom: '1px solid var(--rc-border)' }}>
                      <td style={{ padding: '8px 6px' }}><input type="checkbox" checked={selected.has(p.id)} onChange={() => toggleOne(p.id)} /></td>
                      <td style={{ padding: '8px 6px' }}>
                        <div title={p.title} style={{ fontWeight: 700, lineHeight: 1.3 }}>{truncate(p.title, 45)}</div>
                        {p.authors && <div style={{ fontSize: 11, color: 'var(--rc-muted)', marginTop: 2 }}>{truncate(p.authors, 60)}</div>}
                      </td>
                      <td style={{ padding: '8px 6px', fontStyle: 'italic', fontSize: 12 }}>
                        {[p.journal, p.publication_year].filter(Boolean).join(' · ') || '—'}
                      </td>
                      <td style={{ padding: '8px 6px' }}>
                        <span className={st.cls} style={{ fontSize: 11, ...st.style }}>
                          {st.label === 'Processing' && <span style={{ display: 'inline-block', width: 8, height: 8, border: '2px solid rgba(59,130,246,0.4)', borderTopColor: 'rgba(59,130,246,1)', borderRadius: '50%', animation: 'spin .8s linear infinite', marginRight: 4 }} />}
                          {st.label}
                        </span>
                      </td>
                      <td style={{ padding: '8px 6px' }}>
                        {p.source_provider ? <span className="rc-badge" style={{ fontSize: 11 }}>{providerLabel(p.source_provider)}</span> : <span className="rc-help">—</span>}
                      </td>
                      <td style={{ padding: '8px 6px' }}>
                        <div className="rc-row" style={{ gap: 4, flexWrap: 'wrap' }}>
                          {!isReady && <button className="rc-btn" style={{ padding: '4px 8px', fontSize: 11 }} onClick={() => processMut.mutate(p.id)}>Process</button>}
                          {isReady && (
                            <>
                              <Link className="rc-btn rc-btn--primary" style={{ padding: '4px 8px', fontSize: 11, textDecoration: 'none' }} to={`/projects/${projectId}/reader?paper_id=${p.id}`}>📖 Read</Link>
                              <Link className="rc-btn rc-btn--primary" style={{ padding: '4px 8px', fontSize: 11, textDecoration: 'none' }} to={`/projects/${projectId}/meta?paper_id=${p.id}`}>⚡ Extract</Link>
                              <button className="rc-btn" style={{ padding: '4px 8px', fontSize: 11 }} onClick={async () => {
                                try {
                                  const r = await api.post(`/references/sync-paper/${p.id}`);
                                  if ((r.data as any)?.created > 0) {
                                    toast.success('Sincronizado', 'Referencia creada en el proyecto.');
                                  } else {
                                    toast.info('Ya existe', 'Este paper ya está en Referencias.');
                                  }
                                } catch (e: any) {
                                  toast.error('Error', e?.response?.data?.detail || 'No se pudo sincronizar a Referencias.');
                                }
                              }}>🔗 to References</button>
                            </>
                          )}
                          <button className="rc-btn" style={{ padding: '4px 8px', fontSize: 11 }} onClick={() => downloadFile(p)}>Download</button>
                          <button className="rc-btn" style={{ padding: '4px 8px', fontSize: 11 }} onClick={() => void toggleTrace(p)}>
                            {traceState[p.id]?.expanded ? 'Hide trace' : 'Trace'}
                          </button>
                          <button className="rc-btn" style={{ padding: '4px 8px', fontSize: 11, color: p.favorite ? '#eab308' : undefined }} onClick={() => favoriteMut.mutate(p)} title={p.favorite ? 'Quitar favorito' : 'Favorito'}>
                            {p.favorite ? '★' : '☆'}
                          </button>
                          <button className="rc-btn" style={{ padding: '4px 8px', fontSize: 11, color: 'var(--rc-danger)' }} onClick={() => deleteWithConfirm(p)}>Del</button>
                        </div>
                      </td>
                    </tr>
                    {traceState[p.id]?.expanded ? (
                      <tr style={{ background: 'var(--rc-surface-2)' }}>
                        <td colSpan={6} style={{ padding: 12 }}>
                          {traceState[p.id]?.loading ? (
                            <div className="rc-help">Cargando traza…</div>
                          ) : traceState[p.id]?.error ? (
                            <div className="rc-error">{traceState[p.id]?.error}</div>
                          ) : traceState[p.id]?.trace ? (
                            <div style={{ display: 'grid', gap: 8 }}>
                              <div className="rc-row" style={{ gap: 8, flexWrap: 'wrap' }}>
                                <span className="rc-badge">{traceStatusLabel(traceState[p.id]!.trace!.final_status)}</span>
                                <span className="rc-badge">{providerLabel(traceState[p.id]!.trace!.source_provider)}</span>
                                {traceState[p.id]!.trace!.used_fallback ? <span className="rc-badge">Usó fallback</span> : null}
                              </div>
                              <div className="rc-help">Auditado: {formatDate(traceState[p.id]!.trace!.audited_at)}</div>
                              <div className="rc-help">OA URL: {traceState[p.id]!.trace!.oa_url ? <a href={traceState[p.id]!.trace!.oa_url!} target="_blank" rel="noopener noreferrer">{traceState[p.id]!.trace!.oa_url}</a> : '—'}</div>
                              <div className="rc-help">Landing URL: {traceState[p.id]!.trace!.landing_url ? <a href={traceState[p.id]!.trace!.landing_url!} target="_blank" rel="noopener noreferrer">{traceState[p.id]!.trace!.landing_url}</a> : '—'}</div>
                              <div className="rc-help">Resolved URL: {traceState[p.id]!.trace!.resolved_url ? <a href={traceState[p.id]!.trace!.resolved_url!} target="_blank" rel="noopener noreferrer">{traceState[p.id]!.trace!.resolved_url}</a> : '—'}</div>
                              <div className="rc-help">Resultado: {traceState[p.id]!.trace!.failure_reason || traceStatusLabel(traceState[p.id]!.trace!.final_status)}</div>
                            </div>
                          ) : (
                            <div className="rc-help">Este paper no tiene una auditoría de descarga OA registrada.</div>
                          )}
                        </td>
                      </tr>
                    ) : null}
                  </Fragment>
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

        </div>

        <div className="rc-workspace-rail">
          <InsightCard
            eyebrow="Processing lane"
            title={`${readyRatio}% of the library is ready to use`}
            body={hasProcessing
              ? `${processingCount} paper(s) are still moving through the full-text pipeline. Keep Library open for curation, then move to Reader or Extraction once enough evidence is ready.`
              : 'Use this lane to move papers from intake to “ready”, then keep only the papers that really deserve downstream attention.'}
            tone={hasProcessing ? 'warning' : 'success'}
            action={<button className="rc-btn rc-btn--sm" onClick={processAllPending}>Process pending</button>}
          />

          <div className="rc-card">
            <div className="rc-card-title" style={{ marginBottom: 8 }}>Library pulse</div>
            <div className="rc-shortlist-list">
              <div className="rc-shortlist-item">
                <div className="rc-shortlist-item__title">Ready for Reader</div>
                <div className="rc-shortlist-item__meta">{readyCount} paper(s)</div>
              </div>
              <div className="rc-shortlist-item">
                <div className="rc-shortlist-item__title">Pending or newly added</div>
                <div className="rc-shortlist-item__meta">{pendingCount} paper(s)</div>
              </div>
              <div className="rc-shortlist-item">
                <div className="rc-shortlist-item__title">Need intervention</div>
                <div className="rc-shortlist-item__meta">{failedCount} failed · {processingCount} in queue</div>
              </div>
            </div>
          </div>

          <InsightCard
            eyebrow="Selection"
            title={selected.size > 0 ? `${selected.size} selected in this view` : 'No papers selected'}
            body={selected.size > 0
              ? `${selectedReadyCount} selected paper(s) are already ready for downstream use. Keep the shortlist tight and only carry forward what you trust.`
              : 'Use the checkboxes to build a temporary working subset before you process, inspect or move papers downstream.'}
            tone={selected.size > 0 ? 'primary' : 'neutral'}
            action={(
              <div className="rc-row" style={{ gap: 6 }}>
                <Link className="rc-btn rc-btn--sm" style={{ textDecoration: 'none' }} to={`/projects/${projectId}/reader`}>Reader</Link>
                <Link className="rc-btn rc-btn--sm" style={{ textDecoration: 'none' }} to={`/projects/${projectId}/meta`}>Extraction</Link>
              </div>
            )}
          />

          {selectedRows.length > 0 && (
            <div className="rc-card">
              <div className="rc-card-title" style={{ marginBottom: 8 }}>Selected preview</div>
              <div className="rc-shortlist-list">
                {selectedRows.map((paper) => (
                  <div key={paper.id} className="rc-shortlist-item">
                    <div className="rc-shortlist-item__title">{truncate(paper.title, 72)}</div>
                    <div className="rc-shortlist-item__meta">{paper.journal || 'Journal unavailable'} · {paper.publication_year || 'Year unavailable'}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
