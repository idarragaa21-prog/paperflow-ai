import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api, requestTimeouts } from '../services/api';
import { useToast } from '../ui/Toast/ToastProvider';
import { Skeleton, SkeletonLines } from '../ui/Skeleton/Skeleton';

type PaperMetadata = {
  pmid?: string | null;
  pmcid?: string | null;
  doi?: string | null;
  title: string;
  authors?: string[];
  journal?: string | null;
  pub_year?: number | null;
  abstract?: string | null;
  is_open_access?: boolean;
  oa_url?: string | null;
};

type SearchResponse = {
  count: number;
  results: PaperMetadata[];
  query_translation?: string | null;
  cached: boolean;
  sources?: string[];
  partial_success?: boolean;
  provider_status?: Record<string, string>;
  warnings?: string[];
};

type ResultUiState = {
  openStatus?: 'idle' | 'opening' | 'opened' | 'error';
  saveStatus?: 'idle' | 'saving' | 'saved' | 'duplicate' | 'error';
  error?: string | null;
};

function sourceHref(result: PaperMetadata) {
  if (result.oa_url) return result.oa_url;
  if (result.doi) return `https://doi.org/${encodeURIComponent(result.doi)}`;
  if (result.pmid) return `https://pubmed.ncbi.nlm.nih.gov/${encodeURIComponent(result.pmid)}/`;
  return null;
}

function resultKey(result: PaperMetadata, index?: number) {
  return result.doi || result.pmid || result.title || String(index || 0);
}

function canSavePdf(result: PaperMetadata) {
  return Boolean(result.is_open_access) && Boolean(result.doi || result.pmid);
}

export default function SearchPage() {
  const { projectId } = useParams();

  const toast = useToast();

  const [query, setQuery] = useState('');
  const [maxResults, setMaxResults] = useState<number>(20);
  const [loading, setLoading] = useState(false);
  const [pageError, setPageError] = useState<string | null>(null);
  const [data, setData] = useState<SearchResponse | null>(null);
  const [resultStates, setResultStates] = useState<Record<string, ResultUiState>>({});

  const [selected, setSelected] = useState<Record<string, boolean>>({});

  const [batchJobId, setBatchJobId] = useState<string | null>(null);
  const [batchJob, setBatchJob] = useState<{ status: string; progress: number; error?: string | null; output?: any } | null>(null);
  const [batchModalOpen, setBatchModalOpen] = useState(false);

  const canSearch = useMemo(() => Boolean(projectId && query.trim().length >= 3), [projectId, query]);

  async function runSearch() {
    if (!projectId) return;
    setLoading(true);
    setPageError(null);
    try {
      const r = await api.post('/search/federated', {
        project_id: projectId,
        query: query.trim(),
        max_results: maxResults,
      }, { timeout: requestTimeouts.search });
      setData(r.data as SearchResponse);
      setSelected({});
      setResultStates({});
      setBatchJobId(null);
      setBatchJob(null);
      setBatchModalOpen(false);
    } catch (e: any) {
      setPageError(e?.response?.data?.detail || 'La busqueda fallo');
    } finally {
      setLoading(false);
    }
  }

  function patchResultState(key: string, next: Partial<ResultUiState>) {
    setResultStates((prev) => ({
      ...prev,
      [key]: {
        openStatus: 'idle',
        saveStatus: 'idle',
        error: null,
        ...(prev[key] || {}),
        ...next,
      },
    }));
  }

  function openSource(r: PaperMetadata, key: string) {
    const href = sourceHref(r);
    if (!href) {
      patchResultState(key, { openStatus: 'error', error: 'Este resultado solo tiene metadatos y no ofrece una fuente abrible.' });
      return;
    }
    patchResultState(key, { openStatus: 'opening', error: null });
    const popup = window.open(href, '_blank', 'noopener,noreferrer');
    if (!popup) {
      patchResultState(key, { openStatus: 'error', error: 'El navegador bloqueo la apertura de la fuente. Permite popups o abre el enlace manualmente.' });
      return;
    }
    patchResultState(key, { openStatus: 'opened' });
  }

  async function downloadOA(r: PaperMetadata) {
    if (!projectId) return;
    const key = resultKey(r);
    patchResultState(key, { saveStatus: 'saving', error: null });
    setPageError(null);
    try {
      const payload: any = {
        project_id: projectId,
        title: r.title,
      };
      if (r.doi) payload.doi = r.doi;
      if (r.pmid) payload.pmid = r.pmid;

      const resp = await api.post('/papers/download', payload);
      const duplicate = Boolean(resp.data?.duplicate);
      patchResultState(key, { saveStatus: duplicate ? 'duplicate' : 'saved', error: null });
      toast.info(duplicate ? 'Duplicado' : 'Guardado', duplicate ? 'El paper ya existe en este proyecto.' : 'PDF descargado y guardado.');
    } catch (e: any) {
      patchResultState(key, { saveStatus: 'error', error: e?.response?.data?.detail || 'La descarga fallo' });
    } finally {
      setSelected((prev) => ({ ...prev, [key]: false }));
    }
  }

  const selectedCount = useMemo(() => Object.values(selected).filter(Boolean).length, [selected]);
  const openableCount = useMemo(() => (data?.results || []).filter((item) => Boolean(sourceHref(item))).length, [data]);
  const saveableResults = useMemo(() => (data?.results || []).filter((item) => canSavePdf(item)), [data]);
  const reviewOnlyResults = useMemo(() => (data?.results || []).filter((item) => !canSavePdf(item)), [data]);
  const saveableCount = saveableResults.length;

  const selectedPapers = useMemo(() => {
    if (!data) return [] as any[];
    return data.results
      .map((r, idx) => ({ r, idx }))
      .filter(({ r, idx }) => {
        const key = resultKey(r, idx);
        const canDownload = canSavePdf(r);
        return Boolean(selected[key]) && canDownload;
      })
      .map(({ r }) => ({
        pmid: r.pmid || undefined,
        pmcid: r.pmcid || undefined,
        doi: r.doi || undefined,
        title: r.title,
      }));
  }, [data, selected]);

  function toggleSelect(key: string, next?: boolean) {
    setSelected((prev) => ({ ...prev, [key]: next ?? !prev[key] }));
  }

  function selectAllOA() {
    if (!data) return;
    const next: Record<string, boolean> = {};
    data.results.forEach((r, idx) => {
      const key = resultKey(r, idx);
      const canDownload = canSavePdf(r);
      if (canDownload) next[key] = true;
    });
    setSelected(next);
  }

  function clearSelection() {
    setSelected({});
  }

  async function startBatchDownload() {
    if (!projectId) return;
    if (!selectedPapers.length) {
      toast.info('No hay papers seleccionados', 'Selecciona primero al menos un paper elegible con PDF abierto.');
      return;
    }
    setPageError(null);
    try {
      const resp = await api.post('/papers/batch-download', {
        project_id: projectId,
        papers: selectedPapers,
      });
      const jid = String(resp.data?.job_id || '');
      setBatchJobId(jid);
      setBatchJob({ status: 'queued', progress: 0, error: null });
      setBatchModalOpen(true);
    } catch (e: any) {
      setPageError(e?.response?.data?.detail || 'La descarga por lote fallo');
    }
  }

  async function cancelBatch() {
    if (!batchJobId) return;
    try {
      await api.post(`/jobs/${batchJobId}/cancel`);
      setBatchJob((prev) => prev ? { ...prev, status: 'cancelled', error: prev.error || 'Cancelado por el usuario' } : prev);
    } catch {
      // ignore
    }
  }

  useEffect(() => {
    if (!batchJobId || !batchModalOpen) return;

    let alive = true;
    let t: any = null;

    async function poll() {
      try {
        const r = await api.get(`/jobs/${batchJobId}`);
        const status = String(r.data?.status || 'queued');
        const progress = Number(r.data?.progress_percent || 0);
        const error = r.data?.error || null;
        const result = r.data?.result || {};
        const output = result?.output || result?.rq_result?.output;

        if (alive) setBatchJob({ status, progress, error, output });

        if (status === 'completed' || status === 'failed' || status === 'cancelled') return;
      } catch (e: any) {
        if (alive) setBatchJob((prev) => prev || { status: 'queued', progress: 0, error: e?.message || 'La consulta del job fallo' });
      }
      t = setTimeout(poll, 1000);
    }

    poll();
    return () => {
      alive = false;
      if (t) clearTimeout(t);
    };
  }, [batchJobId, batchModalOpen]);

  return (
    <div className="rc-section-shell">
      <div className="rc-hero-card">
        <div style={{ maxWidth: 760 }}>
          <div className="rc-stage-label rc-stage-label--teal">Paso 1 · Descubrir</div>
          <h1 className="rc-page-title" style={{ marginTop: 12 }}>Encuentra la evidencia correcta</h1>
          <div className="rc-subtitle">Busca en PubMed, Europe PMC y DOAJ, y mueve los articulos prometedores a la biblioteca del proyecto.</div>
          <div className="rc-help" style={{ marginTop: 12 }}>
            Usa una consulta parecida a una pregunta y guarda directamente los articulos de acceso abierto. Cuando ya tengas una lista base, pasa al lector para hacer preguntas con evidencia.
          </div>
        </div>
        <div className="rc-metric-grid" style={{ minWidth: 300 }}>
          <div className="rc-metric-tile"><strong>{data?.count ?? '—'}</strong><span>Resultados</span></div>
          <div className="rc-metric-tile"><strong>{openableCount || '—'}</strong><span>Fuentes abribles</span></div>
          <div className="rc-metric-tile"><strong>{saveableCount || '—'}</strong><span>PDFs guardables</span></div>
        </div>
      </div>

      <div className="rc-shelf">
        <div className="rc-card">
          <div className="rc-card-title">Consulta de busqueda</div>
          <div className="rc-row" style={{ alignItems: 'flex-end' }}>
            <div style={{ flex: 1, minWidth: 260 }}>
              <div className="rc-kicker">Pregunta de investigacion</div>
              <input data-testid="search-query-input" className="rc-input" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="ej. metaanalisis reconstruccion ACL isquiotibiales vs BPTB" />
            </div>
            <div style={{ width: 140 }}>
              <div className="rc-kicker">Maximo de resultados</div>
              <input data-testid="search-max-results-input" className="rc-input" type="number" value={maxResults} min={1} max={100} onChange={(e) => setMaxResults(Number(e.target.value))} />
            </div>
            <button data-testid="search-submit-button" className="rc-btn rc-btn--primary" disabled={!canSearch || loading} onClick={runSearch}>
              {loading ? 'Buscando…' : 'Buscar'}
            </button>
          </div>
          <div className="rc-help" style={{ marginTop: 8 }}>Consejo: usa frases, resultados, poblaciones y tipos de estudio. La app fusiona duplicados entre proveedores.</div>
        </div>

        <div className="rc-next-step">
          <div className="rc-kicker">Siguiente paso sugerido</div>
          <div style={{ fontWeight: 800, letterSpacing: '-0.02em', marginTop: 4 }}>Construye tu lista de lectura</div>
          <div className="rc-help" style={{ marginTop: 8 }}>
            Guarda primero los articulos abiertos y luego abre el lector para comparar hallazgos con citas. La biblioteca guarda la lista larga; el lector te ayuda a decidir que importa.
          </div>
          <div className="rc-row" style={{ marginTop: 12 }}>
            <Link className="rc-btn" to={`/projects/${projectId}/library`}>Abrir biblioteca</Link>
            <Link className="rc-btn rc-btn--primary" to={`/projects/${projectId}/reader`}>Ir al lector</Link>
          </div>
        </div>
      </div>

      {pageError ? <div className="rc-error">{String(pageError)}</div> : null}

      {data ? (
        <div className="rc-card-list">
          <div className="rc-focus-card">
            <div>
              <div className="rc-card-title" style={{ marginBottom: 6 }}>Que hacer aqui</div>
              <div className="rc-help">
                Revisa primero los articulos <b>listos para guardar</b>. Si un resultado no tiene PDF descargable, úsalo solo como referencia con <b>Abrir fuente</b>.
              </div>
              {data.partial_success ? (
                <div className="rc-help" style={{ marginTop: 8 }}>
                  La busqueda fue parcial. Algunas fuentes externas no respondieron, pero los resultados visibles son válidos.
                </div>
              ) : null}
            </div>
            <div className="rc-chip-list">
              <span className="rc-chip">Resultados: {data.count}{data.cached ? ' en cache' : ''}</span>
              {data.query_translation ? <span className="rc-chip">Traduccion: {data.query_translation}</span> : null}
              {data.sources?.length ? <span className="rc-chip">Fuentes: {data.sources.join(', ')}</span> : null}
              {data.partial_success ? <span className="rc-chip">Busqueda parcial</span> : null}
            </div>
          </div>

          {data.warnings?.length ? (
            <div className="rc-card">
              <div className="rc-card-title" style={{ marginBottom: 6 }}>Alertas de proveedores</div>
              <div className="rc-help">{data.warnings.join(' · ')}</div>
            </div>
          ) : null}

          {loading ? (
            <div className="rc-card">
              <Skeleton height={14} width="40%" />
              <div style={{ height: 10 }} />
              <SkeletonLines lines={6} lineHeight={12} lastLineWidth="60%" />
            </div>
          ) : null}

          {saveableResults.length ? (
            <div className="rc-card">
              <div className="rc-toolbar" style={{ marginBottom: 12 }}>
                <div>
                  <div className="rc-card-title" style={{ marginBottom: 4 }}>Listos para guardar en la biblioteca</div>
                  <div className="rc-help">Estos resultados tienen PDF descargable. Guarda primero este grupo y deja el resto para revisión manual.</div>
                </div>
                <div className="rc-chip-list">
                  <span className="rc-chip">{saveableResults.length} listos</span>
                  <span className="rc-chip">{selectedCount} seleccionados</span>
                </div>
              </div>
              <div className="rc-row">
                <button className="rc-btn" onClick={selectAllOA}>Seleccionar todos</button>
                <button className="rc-btn" onClick={clearSelection} disabled={selectedCount === 0}>Limpiar ({selectedCount})</button>
                <button className="rc-btn rc-btn--primary" onClick={startBatchDownload} disabled={selectedCount === 0}>Guardar seleccionados ({selectedCount})</button>
                {batchJobId ? <button className="rc-btn" onClick={() => setBatchModalOpen(true)}>Ver job por lote</button> : null}
              </div>
            </div>
          ) : null}

          {saveableResults.length ? (
            <div className="rc-result-section">
              <div className="rc-result-section__title">Articulos listos para guardar</div>
              <div className="rc-card-list">
                {saveableResults.map((r, idx) => {
                  const key = resultKey(r, idx);
                  const canDownload = canSavePdf(r);
                  const isSelected = Boolean(selected[key]);
                  const itemState = resultStates[key] || {};
                  const href = sourceHref(r);
                  const savedState = itemState.saveStatus === 'saved' || itemState.saveStatus === 'duplicate' ? itemState.saveStatus : undefined;
                  return (
                    <div key={key} className="rc-card" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                      <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                        <input type="checkbox" disabled={!canDownload} checked={isSelected} onChange={() => toggleSelect(key)} title={canDownload ? 'Seleccionar para guardado por lote' : 'No elegible para guardado por lote'} style={{ marginTop: 3 }} />
                        <div style={{ fontWeight: 850, flex: 1, lineHeight: 1.25 }}>{r.title}</div>
                        {savedState === 'saved' ? <span className="rc-badge rc-badge--success">Guardado</span> : null}
                        {savedState === 'duplicate' ? <span className="rc-badge">Ya esta en la biblioteca</span> : null}
                        {!savedState ? <span className="rc-badge rc-badge--success">PDF listo</span> : null}
                      </div>

                      <div className="rc-help">
                        {(r.journal || '—')}{r.pub_year ? ` · ${r.pub_year}` : ''}
                        {r.doi ? ` · DOI: ${r.doi}` : ''}
                        {r.pmid ? ` · PMID: ${r.pmid}` : ''}
                      </div>

                      {r.abstract ? <div style={{ fontSize: 13, whiteSpace: 'pre-wrap' }}>{r.abstract}</div> : null}

                      {itemState.error ? <div className="rc-error">{itemState.error}</div> : null}

                      <div className="rc-row">
                        <button
                          data-testid={`search-save-${idx}`}
                          className="rc-btn rc-btn--primary"
                          disabled={!canDownload || Boolean(savedState) || itemState.saveStatus === 'saving'}
                          onClick={() => downloadOA(r)}
                        >
                          {savedState === 'saved'
                            ? 'Guardado en biblioteca'
                            : savedState === 'duplicate'
                              ? 'Ya esta en la biblioteca'
                              : itemState.saveStatus === 'error'
                                ? 'Reintentar guardado'
                              : itemState.saveStatus === 'saving'
                                ? 'Guardando…'
                                : 'Guardar PDF en biblioteca'}
                        </button>
                        {href ? (
                          <button
                            data-testid={`search-open-${idx}`}
                            className="rc-btn"
                            type="button"
                            onClick={() => openSource(r, key)}
                          >
                            {itemState.openStatus === 'opening' ? 'Abriendo…' : itemState.openStatus === 'opened' ? 'Fuente abierta' : 'Abrir fuente'}
                          </button>
                        ) : null}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : null}

          {reviewOnlyResults.length ? (
            <div className="rc-result-section">
              <div className="rc-result-section__title">Resultados para revisar antes de guardar</div>
              <div className="rc-card-list">
                {reviewOnlyResults.map((r, idx) => {
                  const key = resultKey(r, idx);
                  const href = sourceHref(r);
                  const itemState = resultStates[key] || {};
                  return (
                    <div key={key} className="rc-card" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                      <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                        <div style={{ fontWeight: 850, flex: 1, lineHeight: 1.25 }}>{r.title}</div>
                        {href ? <span className="rc-badge rc-badge--info">Fuente disponible</span> : <span className="rc-badge">Solo metadatos</span>}
                      </div>

                      <div className="rc-help">
                        {(r.journal || '—')}{r.pub_year ? ` · ${r.pub_year}` : ''}
                        {r.doi ? ` · DOI: ${r.doi}` : ''}
                        {r.pmid ? ` · PMID: ${r.pmid}` : ''}
                      </div>

                      {r.abstract ? <div style={{ fontSize: 13, whiteSpace: 'pre-wrap' }}>{r.abstract}</div> : null}

                      {itemState.error ? <div className="rc-error">{itemState.error}</div> : null}

                      <div className="rc-row">
                        {href ? (
                          <button
                            data-testid={`search-open-review-${idx}`}
                            className="rc-btn rc-btn--primary"
                            type="button"
                            onClick={() => openSource(r, key)}
                          >
                            {itemState.openStatus === 'opening' ? 'Abriendo…' : itemState.openStatus === 'opened' ? 'Fuente abierta' : 'Abrir fuente'}
                          </button>
                        ) : null}
                        {!r.is_open_access ? <span className="rc-help">Los proveedores no lo marcan como acceso abierto descargable.</span> : null}
                        {r.is_open_access && !canSavePdf(r) ? <span className="rc-help">Hay acceso abierto, pero falta DOI o PMID para resolver el PDF.</span> : null}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : null}
        </div>
      ) : (
        <div className="rc-muted">Ejecuta una busqueda para ver resultados.</div>
      )}

      {batchModalOpen ? (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.35)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: 20,
            zIndex: 50,
          }}
          onClick={() => setBatchModalOpen(false)}
        >
          <div className="rc-card" style={{ width: 'min(860px, 96vw)', maxHeight: '85vh', overflow: 'auto' }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'center' }}>
              <div style={{ fontWeight: 900 }}>Guardado por lote de PDFs OA</div>
              <button className="rc-btn" onClick={() => setBatchModalOpen(false)}>Cerrar</button>
            </div>
            <div style={{ height: 10 }} />
            <div className="rc-help">
              Job: <span style={{ fontFamily: 'monospace' }}>{batchJobId || '—'}</span>
            </div>
            <div className="rc-help">
              Estado: <b>{batchJob?.status || '—'}</b> · Progreso: <b>{batchJob?.progress ?? 0}%</b>
            </div>
            {batchJob?.error ? <div className="rc-error" style={{ marginTop: 8 }}>{String(batchJob.error)}</div> : null}

            <div className="rc-row" style={{ marginTop: 10 }}>
              <button className="rc-btn rc-btn--ghost" disabled={!batchJobId} onClick={cancelBatch}>
                Cancelar job
              </button>
            </div>

            <div style={{ height: 12 }} />
            <div style={{ fontWeight: 850, marginBottom: 6 }}>Resumen</div>
            {batchJob?.output ? (
              <div className="rc-row" style={{ gap: 8 }}>
                <span className="rc-badge rc-badge--success">Descargados: <b>{batchJob.output?.downloaded?.length ?? 0}</b></span>
                <span className="rc-badge">Ya existen: <b>{batchJob.output?.already_exists?.length ?? 0}</b></span>
                <span className="rc-badge">No disponibles: <b>{batchJob.output?.not_available?.length ?? 0}</b></span>
                <span className="rc-badge rc-badge--danger">Fallidos: <b>{batchJob.output?.failed?.length ?? 0}</b></span>
              </div>
            ) : (
              <div className="rc-muted">Esperando la salida del job…</div>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
