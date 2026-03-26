import { useCallback, useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api, isApiError } from '../services/api';
import { useToast } from '../ui/Toast/ToastProvider';
import { useConfirm } from '../ui/Dialog/useConfirm';
import { Skeleton, SkeletonLines } from '../ui/Skeleton/Skeleton';

type PaperDownloadTrace = {
  title: string;
  paper_id: string;
  doi?: string | null;
  pmid?: string | null;
  pmcid?: string | null;
  source_provider?: string | null;
  oa_url?: string | null;
  landing_url?: string | null;
  resolved_url?: string | null;
  used_fallback?: boolean;
  final_status: 'downloaded' | 'existing' | 'unavailable' | 'failed';
  failure_reason?: string | null;
  audited_at?: string | null;
};

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

type PaperDetailResponse = PaperRow & {
  download_trace?: PaperDownloadTrace | null;
};

type PaginatedResponse<T> = {
  items: T[];
  next_cursor?: string | null;
  has_more: boolean;
  total_count?: number;
};

type PaperTraceState = {
  expanded: boolean;
  loading: boolean;
  error: string | null;
  trace?: PaperDownloadTrace | null;
};

const SOURCE_LABELS: Record<string, string> = {
  pubmed: 'PubMed',
  europepmc: 'Europe PMC',
  doaj: 'DOAJ',
  unpaywall: 'Unpaywall',
  doi_content_negotiation: 'DOI direct',
  manual_upload: 'Carga manual',
};

function providerLabel(source?: string | null) {
  return SOURCE_LABELS[String(source || '').toLowerCase()] || String(source || 'Fuente externa');
}

function traceStatusLabel(status: PaperDownloadTrace['final_status']) {
  if (status === 'downloaded') return 'Descargado';
  if (status === 'existing') return 'Ya existía';
  if (status === 'unavailable') return 'No disponible';
  return 'Falló';
}

function formatDate(value?: string | null) {
  if (!value) return 'Sin fecha';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString();
}

function errorDetail(error: unknown, fallback: string) {
  if (!isApiError(error)) {
    return error instanceof Error ? error.message : fallback;
  }
  const detail = error.response?.data;
  if (detail && typeof detail === 'object' && 'detail' in detail && typeof detail.detail === 'string') {
    return detail.detail;
  }
  return error.message || fallback;
}

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
  const [traceState, setTraceState] = useState<Record<string, PaperTraceState>>({});

  const canDownload = useMemo(() => Boolean(projectId && (doi.trim() || pmid.trim())), [projectId, doi, pmid]);

  function patchTraceState(paperId: string, next: Partial<PaperTraceState>) {
    setTraceState((prev) => ({
      ...prev,
      [paperId]: {
        ...(prev[paperId] || {
          expanded: false,
          loading: false,
          error: null,
        }),
        ...next,
      },
    }));
  }

  const load = useCallback(async (cursor?: string | null, append = false) => {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    try {
      const rp = await api.get(`/projects/${projectId}/library`, { params: { limit: 50, cursor: cursor || undefined } });
      const page = rp.data as PaginatedResponse<PaperRow>;
      setPapers((prev) => (append ? [...prev, ...page.items] : page.items));
      setNextCursor(page.next_cursor || null);
      setHasMore(Boolean(page.has_more));
    } catch (error: unknown) {
      setError(errorDetail(error, 'No se pudieron cargar los papers'));
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    void load();
  }, [load]);

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
      const duplicate = Boolean((r.data as { duplicate?: boolean })?.duplicate);
      toast.info(duplicate ? 'Duplicado' : 'Subido', duplicate ? 'El paper ya existe en este proyecto.' : 'PDF subido correctamente.');
      setUploadFile(null);
      await load();
    } catch (error: unknown) {
      setError(errorDetail(error, 'La subida fallo'));
    } finally {
      setUploading(false);
    }
  }

  async function downloadOA() {
    if (!projectId) return;
    setDownloading(true);
    setError(null);
    try {
      const payload: Record<string, string> = {
        project_id: projectId,
      };
      if (doi.trim()) payload.doi = doi.trim();
      if (pmid.trim()) payload.pmid = pmid.trim();
      await api.post('/papers/download', payload);
      toast.success('Descarga solicitada', 'El job del resolvedor OA ha comenzado (los duplicados se deduplican).');
      setDoi('');
      setPmid('');
      await load();
    } catch (error: unknown) {
      setError(errorDetail(error, 'La descarga fallo'));
    } finally {
      setDownloading(false);
    }
  }

  async function downloadFile(p: PaperRow) {
    setError(null);
    try {
      const r = await api.get(`/papers/${p.id}/download`, { responseType: 'blob' });
      downloadBlob(r.data as Blob, p.filename || 'paper.pdf');
    } catch (error: unknown) {
      setError(errorDetail(error, 'La descarga del archivo fallo'));
    }
  }

  async function processPaper(p: PaperRow) {
    setError(null);
    try {
      const r = await api.post(`/papers/${p.id}/process`);
      toast.success('Job encolado', `Proceso: ${String(r.data?.job_id || '')}`);
    } catch (error: unknown) {
      setError(errorDetail(error, 'No se pudo encolar el job de procesamiento'));
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
    } catch (error: unknown) {
      setError(errorDetail(error, 'No se pudo encolar el job de resumen'));
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
    } catch (error: unknown) {
      setError(errorDetail(error, 'La eliminacion fallo'));
    }
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

  return (
    <div className="rc-product-page">
      <div className="rc-product-page__header">
        <div>
          <div className="rc-kicker">Biblioteca</div>
          <h2>PDFs, metadatos y procesamiento en un solo lugar</h2>
          <p>
            Sube artículos, resuelve open access por DOI o PMID y mantén la biblioteca lista para lectura, extracción y análisis.
          </p>
        </div>
        <div className="rc-discover-badges">
          <span className="rc-discover-badge">{papers.length} artículos visibles</span>
          <span className="rc-discover-badge">{hasMore ? '50+' : papers.length} cargados</span>
        </div>
      </div>

      {error ? <div className="rc-error">{String(error)}</div> : null}

      <div className="rc-product-two-column">
        <section className="rc-product-card">
          <div className="rc-product-card__header">
            <div>
              <div className="rc-card-title">Descargar OA</div>
              <div className="rc-help">Usa DOI o PMID para lanzar el resolvedor de PDF open access.</div>
            </div>
          </div>
          <div className="rc-product-form-grid">
            <label className="rc-discover-filter-field">
              <span>DOI</span>
              <input className="rc-input" value={doi} onChange={(e) => setDoi(e.target.value)} placeholder="10.xxxx/xxxxx" />
            </label>
            <label className="rc-discover-filter-field">
              <span>PMID</span>
              <input className="rc-input" value={pmid} onChange={(e) => setPmid(e.target.value)} placeholder="12345678" />
            </label>
          </div>
          <div className="rc-product-actions">
            <button className="rc-btn rc-btn--primary" disabled={!canDownload || downloading} onClick={downloadOA}>
              {downloading ? 'Descargando…' : 'Descargar'}
            </button>
            <button className="rc-btn rc-btn--subtle" onClick={() => { void load(); }} disabled={loading}>
              {loading ? 'Cargando…' : 'Actualizar'}
            </button>
          </div>
        </section>

        <section className="rc-product-card">
          <div className="rc-product-card__header">
            <div>
              <div className="rc-card-title">Subir PDF</div>
              <div className="rc-help">Las subidas se deduplican en servidor por hash y metadatos.</div>
            </div>
          </div>
          <div className="rc-product-actions">
            <input type="file" accept="application/pdf" onChange={(e) => setUploadFile(e.target.files?.[0] || null)} />
            <button className="rc-btn rc-btn--primary" disabled={!uploadFile || uploading} onClick={upload}>
              {uploading ? 'Subiendo…' : 'Subir'}
            </button>
          </div>
        </section>
      </div>

      <section className="rc-product-card">
        <div className="rc-product-card__header">
          <div>
            <div className="rc-card-title">Biblioteca del proyecto</div>
            <div className="rc-help">Cada paper deja claro su origen, estado de procesamiento y acciones disponibles.</div>
          </div>
        </div>

      <div className="rc-product-record-list">
        {loading && papers.length === 0 ? (
          <div className="rc-product-record">
            <Skeleton height={14} width="55%" />
            <div style={{ height: 10 }} />
            <SkeletonLines lines={4} lineHeight={12} lastLineWidth="50%" />
          </div>
        ) : null}
        {!loading && papers.length === 0 ? <div className="rc-empty-state">Todavia no hay articulos en este proyecto.</div> : null}
        {papers.map((p) => (
          <div key={p.id} className="rc-product-record">
            <div className="rc-product-record__header">
              <div style={{ flex: 1, minWidth: 220 }}>
                <h3 className="rc-product-record__title">{p.title}</h3>
                <div className="rc-help" style={{ marginTop: 10 }}>
                  {p.authors ? `${p.authors} · ` : ''}
                  {p.journal ? `${p.journal} · ` : ''}
                  {p.publication_year ? `${p.publication_year} · ` : ''}
                  {p.filename}
                  {p.file_size_kb ? ` · ${p.file_size_kb} KB` : ''}
                </div>
              </div>
              {p.processing_status === 'parsed' ? <span className="rc-badge rc-badge--success">procesado</span> : <span className="rc-badge">{p.processing_status || (p.is_processed ? 'procesado' : 'subido')}</span>}
            </div>

            <div className="rc-product-record__meta">
              {p.doi ? <span className="rc-discover-badge">DOI {p.doi}</span> : null}
              {p.pmid ? <span className="rc-discover-badge">PMID {p.pmid}</span> : null}
              {p.source_provider ? <span className="rc-discover-badge">{p.source_provider}</span> : null}
              {p.is_open_access ? <span className="rc-discover-badge rc-discover-badge--strong">Open access</span> : null}
            </div>
            {p.processing_warnings?.length ? <div className="rc-help">Alertas: {p.processing_warnings.join(', ')}</div> : null}

            <div className="rc-product-actions" style={{ marginTop: 12 }}>
              <button className="rc-btn" onClick={() => downloadFile(p)}>Descargar PDF</button>
              <button className="rc-btn" onClick={() => processPaper(p)} disabled={p.is_processed}>Procesar</button>
              <button className="rc-btn rc-btn--primary" onClick={() => summarizePaper(p)}>Resumir</button>
              <button className="rc-btn rc-btn--subtle" onClick={() => void toggleTrace(p)}>
                {traceState[p.id]?.expanded ? 'Ocultar traza' : 'Ver traza'}
              </button>
              <button className="rc-btn rc-btn--ghost" onClick={() => deletePaper(p)} style={{ borderColor: 'rgba(185,28,28,0.25)', color: 'var(--rc-danger)' }}>
                Eliminar
              </button>
            </div>

            {traceState[p.id]?.expanded ? (
              <div style={{ marginTop: 16 }}>
                <div className="rc-kicker">Trazabilidad de descarga</div>
                {traceState[p.id]?.loading ? (
                  <div className="rc-help">Cargando traza…</div>
                ) : traceState[p.id]?.error ? (
                  <div className="rc-error">{traceState[p.id]?.error}</div>
                ) : traceState[p.id]?.trace ? (
                  <>
                    <div className="rc-product-record__meta" style={{ marginTop: 8 }}>
                      <span className="rc-discover-badge">{traceStatusLabel(traceState[p.id]!.trace!.final_status)}</span>
                      <span className="rc-discover-badge">
                        {traceState[p.id]!.trace!.source_provider
                          ? providerLabel(traceState[p.id]!.trace!.source_provider)
                          : 'Proveedor no resuelto'}
                      </span>
                      {traceState[p.id]!.trace!.used_fallback ? (
                        <span className="rc-discover-badge">Usó fallback</span>
                      ) : null}
                    </div>
                    <div className="rc-help" style={{ marginTop: 8 }}>
                      Auditado: {formatDate(traceState[p.id]!.trace!.audited_at)}
                    </div>
                    <div className="rc-product-job-grid" style={{ marginTop: 12 }}>
                      <div>
                        <div className="rc-kicker">OA URL</div>
                        {traceState[p.id]!.trace!.oa_url ? (
                          <a href={traceState[p.id]!.trace!.oa_url!} target="_blank" rel="noopener noreferrer">
                            {traceState[p.id]!.trace!.oa_url}
                          </a>
                        ) : (
                          <div className="rc-help">No disponible</div>
                        )}
                      </div>
                      <div>
                        <div className="rc-kicker">Landing URL</div>
                        {traceState[p.id]!.trace!.landing_url ? (
                          <a href={traceState[p.id]!.trace!.landing_url!} target="_blank" rel="noopener noreferrer">
                            {traceState[p.id]!.trace!.landing_url}
                          </a>
                        ) : (
                          <div className="rc-help">No disponible</div>
                        )}
                      </div>
                      <div>
                        <div className="rc-kicker">URL final usada</div>
                        {traceState[p.id]!.trace!.resolved_url ? (
                          <a href={traceState[p.id]!.trace!.resolved_url!} target="_blank" rel="noopener noreferrer">
                            {traceState[p.id]!.trace!.resolved_url}
                          </a>
                        ) : (
                          <div className="rc-help">No se registró URL final</div>
                        )}
                      </div>
                      <div>
                        <div className="rc-kicker">Resultado</div>
                        <div className="rc-help">
                          {traceState[p.id]!.trace!.failure_reason ||
                            (traceState[p.id]!.trace!.final_status === 'downloaded'
                              ? 'PDF guardado en la biblioteca.'
                              : traceState[p.id]!.trace!.final_status === 'existing'
                                ? 'El intento resolvió a un paper que ya existía.'
                                : 'No hubo una descarga OA utilizable.')}
                        </div>
                      </div>
                    </div>
                  </>
                ) : (
                  <div className="rc-help">
                    Este paper no tiene una auditoría de descarga OA. Suele pasar con cargas manuales o registros más antiguos.
                  </div>
                )}
              </div>
            ) : null}
          </div>
        ))}
        {hasMore ? (
          <div className="rc-product-actions">
            <button className="rc-btn" onClick={() => load(nextCursor, true)} disabled={loading}>
              {loading ? 'Cargando…' : 'Cargar mas'}
            </button>
          </div>
        ) : null}
      </div>
      </section>
    </div>
  );
}
