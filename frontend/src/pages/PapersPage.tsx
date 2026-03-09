import { useEffect, useMemo, useState } from 'react';
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

type PaginatedResponse<T> = {
  items: T[];
  next_cursor?: string | null;
  has_more: boolean;
  total_count?: number;
};

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

export default function PapersPage() {
  const { projectId } = useParams();

  const toast = useToast();
  const confirm = useConfirm();

  const [papers, setPapers] = useState<PaperRow[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);

  const [doi, setDoi] = useState('');
  const [pmid, setPmid] = useState('');
  const [downloading, setDownloading] = useState(false);

  const canDownload = useMemo(() => Boolean(projectId && (doi.trim() || pmid.trim())), [projectId, doi, pmid]);

  async function load(cursor?: string | null, append = false) {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    try {
      const rp = await api.get(`/projects/${projectId}/library`, { params: { limit: 50, cursor: cursor || undefined } });
      const page = rp.data as PaginatedResponse<PaperRow>;
      setPapers((prev) => (append ? [...prev, ...page.items] : page.items));
      setNextCursor(page.next_cursor || null);
      setHasMore(Boolean(page.has_more));
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'No se pudieron cargar los papers');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [projectId]);

  async function upload() {
    if (!projectId || !uploadFile) return;
    setUploading(true);
    setError(null);
    try {
      const form = new FormData();
      form.append('project_id', projectId);
      form.append('file', uploadFile);
      const r = await api.post('/papers/upload', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      const duplicate = Boolean((r.data as any)?.duplicate);
      toast.info(duplicate ? 'Duplicado' : 'Subido', duplicate ? 'El paper ya existe en este proyecto.' : 'PDF subido correctamente.');
      setUploadFile(null);
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'La subida fallo');
    } finally {
      setUploading(false);
    }
  }

  async function downloadOA() {
    if (!projectId) return;
    setDownloading(true);
    setError(null);
    try {
      const payload: any = {
        project_id: projectId,
      };
      if (doi.trim()) payload.doi = doi.trim();
      if (pmid.trim()) payload.pmid = pmid.trim();
      await api.post('/papers/download', payload);
      toast.success('Descarga solicitada', 'El job del resolvedor OA ha comenzado (los duplicados se deduplican).');
      setDoi('');
      setPmid('');
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'La descarga fallo');
    } finally {
      setDownloading(false);
    }
  }

  async function downloadFile(p: PaperRow) {
    setError(null);
    try {
      const r = await api.get(`/papers/${p.id}/download`, { responseType: 'blob' });
      downloadBlob(r.data as Blob, p.filename || 'paper.pdf');
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'La descarga del archivo fallo');
    }
  }

  async function processPaper(p: PaperRow) {
    setError(null);
    try {
      const r = await api.post(`/papers/${p.id}/process`);
      toast.success('Job encolado', `Proceso: ${String(r.data?.job_id || '')}`);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'No se pudo encolar el job de procesamiento');
    }
  }

  async function summarizePaper(p: PaperRow) {
    setError(null);
    try {
      const r = await api.post('/notes/summarize', {
        paper_id: p.id,
        custom_instructions: null,
      });
      toast.success('Job encolado', `Resumen: ${String(r.data?.job_id || '')}`);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'No se pudo encolar el job de resumen');
    }
  }

  async function deletePaper(p: PaperRow) {
    const ok = await confirm({
      title: `Eliminar paper?`,
      body: `Esto eliminara el PDF almacenado.\n\n${p.title}`,
      confirmText: 'Eliminar',
      danger: true,
    });
    if (!ok) return;

    setError(null);
    try {
      await api.delete(`/papers/${p.id}`);
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'La eliminacion fallo');
    }
  }

  return (
    <div className="rc-section-shell">
      <div className="rc-hero-card">
        <div style={{ maxWidth: 760 }}>
          <div className="rc-pill">Biblioteca</div>
          <h1 className="rc-page-title" style={{ marginTop: 12 }}>Biblioteca de investigacion</h1>
          <div className="rc-subtitle">Curate PDFs, elimina duplicados, procesa texto completo y construye una biblioteca reutilizable de evidencia.</div>
        </div>
        <div className="rc-metric-grid" style={{ minWidth: 300 }}>
          <div className="rc-metric-tile"><strong>{papers.length}</strong><span>Articulos visibles</span></div>
          <div className="rc-metric-tile"><strong>{hasMore ? '50+' : papers.length}</strong><span>Registros cargados</span></div>
        </div>
      </div>

      <div className="rc-row">
        <button className="rc-btn" onClick={() => { void load(); }} disabled={loading}>
          {loading ? 'Cargando…' : 'Actualizar'}
        </button>
      </div>

      {error ? <div className="rc-error">{String(error)}</div> : null}

      <div className="rc-panel-grid" style={{ alignItems: 'start' }}>
        <div className="rc-card">
          <div className="rc-card-title">Descargar OA (por DOI / PMID)</div>
          <div className="rc-row" style={{ alignItems: 'flex-end' }}>
            <div style={{ minWidth: 240 }}>
              <div className="rc-kicker">DOI</div>
              <input className="rc-input" value={doi} onChange={(e) => setDoi(e.target.value)} placeholder="10.xxxx/xxxxx" />
            </div>
            <div style={{ width: 180 }}>
              <div className="rc-kicker">PMID</div>
              <input className="rc-input" value={pmid} onChange={(e) => setPmid(e.target.value)} placeholder="12345678" />
            </div>
            <button className="rc-btn rc-btn--primary" disabled={!canDownload || downloading} onClick={downloadOA}>
              {downloading ? 'Descargando…' : 'Descargar'}
            </button>
          </div>
        </div>

        <div className="rc-card">
          <div className="rc-card-title">Subir PDF</div>
          <div className="rc-row" style={{ alignItems: 'center' }}>
            <input type="file" accept="application/pdf" onChange={(e) => setUploadFile(e.target.files?.[0] || null)} />
            <button className="rc-btn rc-btn--primary" disabled={!uploadFile || uploading} onClick={upload}>
              {uploading ? 'Subiendo…' : 'Subir'}
            </button>
          </div>
          <div className="rc-help" style={{ marginTop: 8 }}>Las subidas se deduplican en el servidor (hash + metadatos).</div>
        </div>
      </div>

      <div className="rc-card-list">
        {loading && papers.length === 0 ? (
          <div className="rc-card">
            <Skeleton height={14} width="55%" />
            <div style={{ height: 10 }} />
            <SkeletonLines lines={4} lineHeight={12} lastLineWidth="50%" />
          </div>
        ) : null}
        {!loading && papers.length === 0 ? <div className="rc-muted">Todavia no hay articulos en este proyecto.</div> : null}
        {papers.map((p) => (
          <div key={p.id} className="rc-card" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'flex-start' }}>
              <div style={{ fontWeight: 850, lineHeight: 1.25 }}>{p.title}</div>
              {p.processing_status === 'parsed' ? <span className="rc-badge rc-badge--success">procesado</span> : <span className="rc-badge">{p.processing_status || (p.is_processed ? 'procesado' : 'subido')}</span>}
            </div>

            <div className="rc-help">
              {p.authors ? `${p.authors} · ` : ''}
              {p.journal ? `${p.journal} · ` : ''}
              {p.publication_year ? `${p.publication_year} · ` : ''}
              {p.doi ? `DOI: ${p.doi} · ` : ''}
              {p.pmid ? `PMID: ${p.pmid} · ` : ''}
              {p.filename}
              {p.file_size_kb ? ` · ${p.file_size_kb} KB` : ''}
              {p.source_provider ? ` · ${p.source_provider}` : ''}
              {p.is_open_access ? ' · OA' : ''}
            </div>
            {p.processing_warnings?.length ? <div className="rc-help">Alertas: {p.processing_warnings.join(', ')}</div> : null}

            <div className="rc-row" style={{ marginTop: 2 }}>
              <button className="rc-btn" onClick={() => downloadFile(p)}>Descargar PDF</button>
              <button className="rc-btn" onClick={() => processPaper(p)} disabled={p.is_processed}>Procesar</button>
              <button className="rc-btn rc-btn--primary" onClick={() => summarizePaper(p)}>Resumir</button>
              <button className="rc-btn rc-btn--ghost" onClick={() => deletePaper(p)} style={{ borderColor: 'rgba(185,28,28,0.25)', color: 'var(--rc-danger)' }}>
                Eliminar
              </button>
            </div>
          </div>
        ))}
        {hasMore ? (
          <div className="rc-row">
            <button className="rc-btn" onClick={() => load(nextCursor, true)} disabled={loading}>
              {loading ? 'Cargando…' : 'Cargar mas'}
            </button>
          </div>
        ) : null}
      </div>
    </div>
  );
}
