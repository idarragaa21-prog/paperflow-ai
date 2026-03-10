import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api, requestTimeouts } from '../services/api';
import { useToast } from '../ui/Toast/ToastProvider';
import { Skeleton, SkeletonLines } from '../ui/Skeleton/Skeleton';

type SearchOpenTarget = {
  kind: 'oa_pdf' | 'doi' | 'pubmed' | string;
  url: string;
  label: string;
};

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
  source?: string | null;
  has_abstract?: boolean;
  can_save_pdf?: boolean;
  can_open_external?: boolean;
  content_state?: 'pdf_available' | 'abstract_available' | 'metadata_only';
  open_targets?: SearchOpenTarget[];
  _uiIndex?: number;
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
  expanded?: boolean;
  error?: string | null;
};

type RecencyOption = {
  value: 'all' | '1y' | '2y' | '5y' | '10y';
  label: string;
  years: number | null;
};

const RECENCY_OPTIONS: RecencyOption[] = [
  { value: 'all', label: 'Todo', years: null },
  { value: '1y', label: 'Ultimo 1 ano', years: 1 },
  { value: '2y', label: 'Ultimos 2 anos', years: 2 },
  { value: '5y', label: 'Ultimos 5 anos', years: 5 },
  { value: '10y', label: 'Ultimos 10 anos', years: 10 },
];

const SOURCE_LABELS: Record<string, string> = {
  pubmed: 'PubMed',
  europepmc: 'Europe PMC',
  doaj: 'DOAJ',
};

function resultKey(result: PaperMetadata) {
  return result.doi || result.pmid || result.pmcid || `${result.title}-${result.pub_year || 'na'}`;
}

function fallbackOpenTargets(result: PaperMetadata): SearchOpenTarget[] {
  const targets: SearchOpenTarget[] = [];
  if (result.oa_url) {
    const label = result.oa_url.toLowerCase().endsWith('.pdf') ? 'Abrir PDF OA' : 'Abrir fuente OA';
    targets.push({ kind: 'oa_pdf', url: result.oa_url, label });
  }
  if (result.doi) {
    targets.push({ kind: 'doi', url: `https://doi.org/${encodeURIComponent(result.doi)}`, label: 'Abrir DOI' });
  }
  if (result.pmid) {
    targets.push({ kind: 'pubmed', url: `https://pubmed.ncbi.nlm.nih.gov/${encodeURIComponent(result.pmid)}/`, label: 'Abrir PubMed' });
  }
  return targets;
}

function normalizeResult(result: PaperMetadata, index: number): PaperMetadata {
  const openTargets = (result.open_targets?.length ? result.open_targets : fallbackOpenTargets(result)).filter((target, targetIndex, all) => {
    return all.findIndex((candidate) => candidate.url === target.url) === targetIndex;
  });
  const hasAbstract = typeof result.has_abstract === 'boolean' ? result.has_abstract : Boolean(String(result.abstract || '').trim());
  const canOpenExternal =
    typeof result.can_open_external === 'boolean'
      ? result.can_open_external
      : openTargets.length > 0;
  const canSavePdf =
    typeof result.can_save_pdf === 'boolean'
      ? result.can_save_pdf
      : Boolean(result.is_open_access) && Boolean(result.oa_url) && Boolean(result.doi || result.pmid);
  const contentState =
    result.content_state ||
    (canSavePdf ? 'pdf_available' : hasAbstract || canOpenExternal ? 'abstract_available' : 'metadata_only');

  return {
    ...result,
    open_targets: openTargets,
    has_abstract: hasAbstract,
    can_open_external: canOpenExternal,
    can_save_pdf: canSavePdf,
    content_state: contentState,
    _uiIndex: index,
  };
}

function providerLabel(source?: string | null) {
  return SOURCE_LABELS[String(source || '').toLowerCase()] || 'Fuente externa';
}

function contentStateLabel(result: PaperMetadata) {
  if (result.content_state === 'pdf_available') return 'PDF guardable';
  if (result.content_state === 'abstract_available') return 'Fuente o abstract util';
  return 'Solo metadata';
}

function describeResult(result: PaperMetadata) {
  if (result.content_state === 'pdf_available') {
    return 'Este resultado tiene PDF de acceso abierto y puede guardarse directamente en la biblioteca.';
  }
  if (result.has_abstract) {
    return 'Este resultado trae abstract recuperado por PaperFlow. Revísalo antes de decidir si abrir la fuente externa.';
  }
  if (result.can_open_external) {
    return 'Este resultado no trae abstract util aqui, pero si ofrece una fuente externa para revisarlo fuera de PaperFlow.';
  }
  return 'Este resultado solo aporta referencia bibliografica. No hay abstract recuperado ni una fuente externa util para abrir desde aqui.';
}

function buildFilters(recency: RecencyOption['value'], openAccessOnly: boolean) {
  const selected = RECENCY_OPTIONS.find((option) => option.value === recency) || RECENCY_OPTIONS[3];
  const currentYear = new Date().getFullYear();
  const filters: Record<string, unknown> = { open_access_only: openAccessOnly };
  if (selected.years) {
    filters.year_from = currentYear - selected.years;
    filters.year_to = currentYear;
  }
  return filters;
}

function currentRangeLabel(recency: RecencyOption['value']) {
  const selected = RECENCY_OPTIONS.find((option) => option.value === recency) || RECENCY_OPTIONS[3];
  if (!selected.years) return 'Sin limite temporal';
  const currentYear = new Date().getFullYear();
  return `${currentYear - selected.years} a ${currentYear}`;
}

function isRecent(result: PaperMetadata, recency: RecencyOption['value']) {
  const selected = RECENCY_OPTIONS.find((option) => option.value === recency) || RECENCY_OPTIONS[3];
  if (!selected.years || typeof result.pub_year !== 'number') return false;
  const currentYear = new Date().getFullYear();
  return result.pub_year >= currentYear - selected.years;
}

function sortResults(left: PaperMetadata, right: PaperMetadata) {
  const leftYear = typeof left.pub_year === 'number' ? left.pub_year : -1;
  const rightYear = typeof right.pub_year === 'number' ? right.pub_year : -1;
  if (leftYear !== rightYear) return rightYear - leftYear;
  if (Boolean(left.has_abstract) !== Boolean(right.has_abstract)) return Number(Boolean(right.has_abstract)) - Number(Boolean(left.has_abstract));
  return String(left.title || '').localeCompare(String(right.title || ''));
}

function providerMessages(providerStatus?: Record<string, string>) {
  if (!providerStatus) return [];
  return Object.entries(providerStatus).flatMap(([provider, status]) => {
    if (status === 'ok') return [];
    if (status === 'filtered_server_side') {
      return [`${providerLabel(provider)} se ajusto al rango temporal en el servidor`];
    }
    if (status === 'error') {
      return [`${providerLabel(provider)} no respondio en esta busqueda`];
    }
    return [`${providerLabel(provider)}: ${status}`];
  });
}

export default function SearchPage() {
  const { projectId } = useParams();
  const toast = useToast();

  const [query, setQuery] = useState('');
  const [maxResults, setMaxResults] = useState<number>(20);
  const [recency, setRecency] = useState<RecencyOption['value']>('5y');
  const [openAccessOnly, setOpenAccessOnly] = useState(false);
  const [loading, setLoading] = useState(false);
  const [pageError, setPageError] = useState<string | null>(null);
  const [data, setData] = useState<SearchResponse | null>(null);
  const [resultStates, setResultStates] = useState<Record<string, ResultUiState>>({});
  const [selected, setSelected] = useState<Record<string, boolean>>({});
  const [batchJobId, setBatchJobId] = useState<string | null>(null);
  const [batchJob, setBatchJob] = useState<{ status: string; progress: number; error?: string | null; output?: any } | null>(null);
  const [batchModalOpen, setBatchModalOpen] = useState(false);

  const canSearch = useMemo(() => Boolean(projectId && query.trim().length >= 3), [projectId, query]);

  const normalizedResults = useMemo(
    () => (data?.results || []).map((result, index) => normalizeResult(result, index)),
    [data],
  );

  const saveableResults = useMemo(
    () => normalizedResults.filter((result) => result.can_save_pdf).sort(sortResults),
    [normalizedResults],
  );
  const reviewableResults = useMemo(
    () =>
      normalizedResults
        .filter((result) => !result.can_save_pdf && (result.has_abstract || result.can_open_external))
        .sort(sortResults),
    [normalizedResults],
  );
  const metadataOnlyResults = useMemo(
    () =>
      normalizedResults
        .filter((result) => !result.can_save_pdf && !result.has_abstract && !result.can_open_external)
        .sort(sortResults),
    [normalizedResults],
  );
  const providerWarnings = useMemo(
    () => [...new Set([...(data?.warnings || []), ...providerMessages(data?.provider_status)])],
    [data],
  );
  const selectedCount = useMemo(() => Object.values(selected).filter(Boolean).length, [selected]);

  async function runSearch() {
    if (!projectId) return;
    setLoading(true);
    setPageError(null);
    try {
      const response = await api.post(
        '/search/federated',
        {
          project_id: projectId,
          query: query.trim(),
          max_results: maxResults,
          filters: buildFilters(recency, openAccessOnly),
        },
        { timeout: requestTimeouts.search },
      );
      setData(response.data as SearchResponse);
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
        expanded: false,
        error: null,
        ...(prev[key] || {}),
        ...next,
      },
    }));
  }

  function toggleExpanded(key: string) {
    patchResultState(key, { expanded: !(resultStates[key]?.expanded || false) });
  }

  async function downloadOA(result: PaperMetadata) {
    if (!projectId) return;
    const key = resultKey(result);
    patchResultState(key, { saveStatus: 'saving', error: null });
    setPageError(null);
    try {
      const payload: Record<string, unknown> = {
        project_id: projectId,
        title: result.title,
      };
      if (result.doi) payload.doi = result.doi;
      if (result.pmid) payload.pmid = result.pmid;

      const response = await api.post('/papers/download', payload);
      const duplicate = Boolean(response.data?.duplicate);
      patchResultState(key, { saveStatus: duplicate ? 'duplicate' : 'saved', error: null });
      toast.info(
        duplicate ? 'Duplicado' : 'Guardado',
        duplicate ? 'El paper ya existe en este proyecto.' : 'PDF guardado en la biblioteca del proyecto.',
      );
    } catch (e: any) {
      patchResultState(key, { saveStatus: 'error', error: e?.response?.data?.detail || 'La descarga fallo' });
    } finally {
      setSelected((prev) => ({ ...prev, [key]: false }));
    }
  }

  const selectedPapers = useMemo(() => {
    return saveableResults
      .filter((result) => Boolean(selected[resultKey(result)]))
      .map((result) => ({
        pmid: result.pmid || undefined,
        pmcid: result.pmcid || undefined,
        doi: result.doi || undefined,
        title: result.title,
      }));
  }, [saveableResults, selected]);

  function selectAllSaveable() {
    const next: Record<string, boolean> = {};
    saveableResults.forEach((result) => {
      next[resultKey(result)] = true;
    });
    setSelected(next);
  }

  function clearSelection() {
    setSelected({});
  }

  async function startBatchDownload() {
    if (!projectId) return;
    if (!selectedPapers.length) {
      toast.info('No hay papers seleccionados', 'Selecciona primero al menos un paper guardable.');
      return;
    }
    setPageError(null);
    try {
      const response = await api.post('/papers/batch-download', {
        project_id: projectId,
        papers: selectedPapers,
      });
      const jobId = String(response.data?.job_id || '');
      setBatchJobId(jobId);
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
      setBatchJob((prev) =>
        prev ? { ...prev, status: 'cancelled', error: prev.error || 'Cancelado por el usuario' } : prev,
      );
    } catch {
      // ignore best effort cancellation errors
    }
  }

  useEffect(() => {
    if (!batchJobId || !batchModalOpen) return;

    let alive = true;
    let timer: number | null = null;

    async function poll() {
      try {
        const response = await api.get(`/jobs/${batchJobId}`);
        const status = String(response.data?.status || 'queued');
        const progress = Number(response.data?.progress_percent || 0);
        const error = response.data?.error || null;
        const result = response.data?.result || {};
        const output = result?.output || result?.rq_result?.output;
        if (alive) setBatchJob({ status, progress, error, output });
        if (status === 'completed' || status === 'failed' || status === 'cancelled') return;
      } catch (e: any) {
        if (alive) {
          setBatchJob((prev) => prev || { status: 'queued', progress: 0, error: e?.message || 'La consulta del job fallo' });
        }
      }
      timer = window.setTimeout(poll, 1000);
    }

    void poll();
    return () => {
      alive = false;
      if (timer) window.clearTimeout(timer);
    };
  }, [batchJobId, batchModalOpen]);

  function renderResultCard(result: PaperMetadata) {
    const key = resultKey(result);
    const uiState = resultStates[key] || {};
    const detailsLabel = result.has_abstract ? 'Ver abstract' : 'Ver detalle';
    const statusBadge =
      uiState.saveStatus === 'saved'
        ? 'Guardado'
        : uiState.saveStatus === 'duplicate'
          ? 'Ya esta en la biblioteca'
          : contentStateLabel(result);

    return (
      <article
        key={key}
        data-testid={`search-result-card-${result._uiIndex}`}
        data-pub-year={typeof result.pub_year === 'number' ? result.pub_year : ''}
        className="rc-search-result"
      >
        <div className="rc-search-result__header">
          <div style={{ flex: 1, minWidth: 280 }}>
            <div className="rc-search-result__title">{result.title}</div>
            <div className="rc-help" style={{ marginTop: 8 }}>
              {result.authors?.length ? result.authors.slice(0, 6).join(', ') : 'Autor no disponible'}
            </div>
            <div className="rc-help">
              {result.journal || 'Revista no disponible'}
              {result.pub_year ? ` · ${result.pub_year}` : ' · Ano no disponible'}
            </div>
          </div>
          <div className="rc-chip-list">
            <span className="rc-chip">{providerLabel(result.source)}</span>
            {uiState.saveStatus === 'saved' ? <span className="rc-chip rc-chip--success">Guardado</span> : null}
            {uiState.saveStatus === 'duplicate' ? <span className="rc-chip">Ya esta en biblioteca</span> : null}
            {isRecent(result, recency) ? <span className="rc-chip rc-chip--success">Reciente</span> : null}
            {result.has_abstract ? <span className="rc-chip">Tiene abstract</span> : <span className="rc-chip">Sin abstract</span>}
            {result.is_open_access ? <span className="rc-chip rc-chip--success">Open access</span> : null}
            {result.can_save_pdf ? <span className="rc-chip rc-chip--success">PDF disponible</span> : null}
            {!result.can_save_pdf && !result.has_abstract && !result.can_open_external ? <span className="rc-chip">Solo metadata</span> : null}
          </div>
        </div>

        <div className="rc-search-result__meta">
          <span>Estado: {statusBadge}</span>
          {result.doi ? <span>DOI: {result.doi}</span> : null}
          {result.pmid ? <span>PMID: {result.pmid}</span> : null}
          {result.pmcid ? <span>PMCID: {result.pmcid}</span> : null}
        </div>

        <div className="rc-search-result__summary">{describeResult(result)}</div>

        {uiState.error ? <div className="rc-error">{uiState.error}</div> : null}

        <div className="rc-row">
          <button
            data-testid={`search-details-${result._uiIndex}`}
            className="rc-btn"
            type="button"
            onClick={() => toggleExpanded(key)}
          >
            {uiState.expanded ? 'Ocultar detalle' : detailsLabel}
          </button>

          {result.open_targets?.map((target) => (
            <a
              key={`${key}-${target.kind}`}
              data-testid={`search-open-${result._uiIndex}-${target.kind}`}
              className="rc-btn"
              href={target.url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={() => patchResultState(key, { openStatus: 'opened', error: null })}
            >
              {target.label}
            </a>
          ))}

          {result.can_save_pdf ? (
            <button
              data-testid={`search-save-${result._uiIndex}`}
              className="rc-btn rc-btn--primary"
              disabled={uiState.saveStatus === 'saving' || uiState.saveStatus === 'saved' || uiState.saveStatus === 'duplicate'}
              onClick={() => void downloadOA(result)}
            >
              {uiState.saveStatus === 'saved'
                ? 'Guardado en biblioteca'
                : uiState.saveStatus === 'duplicate'
                  ? 'Ya esta en la biblioteca'
                  : uiState.saveStatus === 'error'
                    ? 'Reintentar guardado'
                    : uiState.saveStatus === 'saving'
                      ? 'Guardando…'
                      : 'Guardar PDF'}
            </button>
          ) : (
            <span className="rc-help">No disponible para guardar</span>
          )}
        </div>

        {uiState.expanded ? (
          <div className="rc-search-result__detail">
            <div className="rc-search-result__detail-grid">
              <div>
                <div className="rc-kicker">Resumen</div>
                {result.has_abstract ? (
                  <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.55 }}>{result.abstract}</div>
                ) : (
                  <div className="rc-help">
                    PaperFlow no recupero abstract para este resultado. Si existe una fuente externa, revisala antes de decidir si vale la pena conservar esta referencia.
                  </div>
                )}
              </div>

              <div>
                <div className="rc-kicker">Disponibilidad</div>
                <div className="rc-help">Proveedor: {providerLabel(result.source)}</div>
                <div className="rc-help">Contenido: {contentStateLabel(result)}</div>
                <div className="rc-help">Fuente externa: {result.can_open_external ? 'Si' : 'No'}</div>
                <div className="rc-help">PDF guardable: {result.can_save_pdf ? 'Si' : 'No'}</div>
                <div className="rc-help">Open access: {result.is_open_access ? 'Si' : 'No'}</div>
              </div>
            </div>
          </div>
        ) : null}
      </article>
    );
  }

  return (
    <div className="rc-search-shell">
      <div className="rc-search-composer rc-card">
        <div className="rc-stage-label rc-stage-label--teal">Paso 1 · Descubrir</div>
        <h1 className="rc-page-title" style={{ marginTop: 12 }}>Busca literatura reciente y util</h1>
        <div className="rc-subtitle">
          Empieza por una pregunta de investigacion, limita la recencia y revisa rapidamente que resultados tienen abstract, fuente util o PDF guardable.
        </div>

        <textarea
          data-testid="search-query-input"
          className="rc-search-input"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Escribe una pregunta o tema de investigacion. Ej. comparacion de injerto BPTB vs isquiotibiales en reconstruccion ACL"
        />

        <div className="rc-search-filter-row">
          <label className="rc-search-field">
            <span className="rc-kicker">Recencia</span>
            <select
              data-testid="search-recency-select"
              className="rc-input"
              value={recency}
              onChange={(event) => setRecency(event.target.value as RecencyOption['value'])}
            >
              {RECENCY_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          <label className="rc-search-field">
            <span className="rc-kicker">Maximo de resultados</span>
            <input
              data-testid="search-max-results-input"
              className="rc-input"
              type="number"
              value={maxResults}
              min={1}
              max={100}
              onChange={(event) => setMaxResults(Number(event.target.value))}
            />
          </label>

          <label className="rc-search-toggle">
            <input
              data-testid="search-open-access-toggle"
              type="checkbox"
              checked={openAccessOnly}
              onChange={(event) => setOpenAccessOnly(event.target.checked)}
            />
            <span>Solo acceso abierto</span>
          </label>

          <button
            data-testid="search-submit-button"
            className="rc-btn rc-btn--primary"
            disabled={!canSearch || loading}
            onClick={() => void runSearch()}
          >
            {loading ? 'Buscando…' : 'Buscar'}
          </button>
        </div>

        <div className="rc-help">
          Valor por defecto: <strong>ultimos 5 anos</strong>. PaperFlow filtra por ano de publicacion y te muestra de forma explicita si un resultado trae abstract, PDF o solo metadata.
        </div>
      </div>

      {pageError ? <div className="rc-error">{String(pageError)}</div> : null}

      {data ? (
        <div className="rc-card rc-search-summary-card">
          <div className="rc-toolbar">
            <div>
              <div className="rc-card-title" style={{ marginBottom: 4 }}>Resumen de la busqueda</div>
              <div className="rc-help">
                {data.count} resultados · rango {currentRangeLabel(recency)} · {openAccessOnly ? 'solo acceso abierto' : 'todas las fuentes disponibles'}
              </div>
            </div>
            <div className="rc-chip-list">
              <span className="rc-chip">{saveableResults.length} guardables</span>
              <span className="rc-chip">{reviewableResults.length} para revisar</span>
              <span className="rc-chip">{metadataOnlyResults.length} solo referencia</span>
              {data.cached ? <span className="rc-chip">Cache</span> : null}
              {data.partial_success ? <span className="rc-chip">Busqueda parcial</span> : null}
            </div>
          </div>

          {providerWarnings.length ? (
            <div className="rc-search-provider-warnings">
              {providerWarnings.map((warning) => (
                <div key={warning} className="rc-help">
                  {warning}
                </div>
              ))}
            </div>
          ) : null}
        </div>
      ) : (
        <div className="rc-card rc-search-empty-card">
          <div className="rc-card-title" style={{ marginBottom: 6 }}>Empieza con una pregunta clara</div>
          <div className="rc-help">
            Busca primero literatura reciente, luego abre las fuentes que valen la pena y guarda solo los papers con PDF util para la biblioteca del proyecto.
          </div>
        </div>
      )}

      {loading ? (
        <div className="rc-card">
          <Skeleton height={14} width="36%" />
          <div style={{ height: 12 }} />
          <SkeletonLines lines={7} lineHeight={12} lastLineWidth="62%" />
        </div>
      ) : null}

      {saveableResults.length ? (
        <section className="rc-search-group">
          <div className="rc-toolbar">
            <div>
              <div className="rc-search-group__title">Listos para guardar</div>
              <div className="rc-help">Estos resultados tienen PDF OA guardable y son la mejor lista para empezar.</div>
            </div>
            <div className="rc-row">
              <button className="rc-btn" onClick={selectAllSaveable}>Seleccionar todos</button>
              <button className="rc-btn" onClick={clearSelection} disabled={selectedCount === 0}>Limpiar ({selectedCount})</button>
              <button className="rc-btn rc-btn--primary" onClick={() => void startBatchDownload()} disabled={selectedCount === 0}>
                Guardar seleccionados ({selectedCount})
              </button>
            </div>
          </div>
          <div className="rc-card-list">
            {saveableResults.map((result) => {
              const key = resultKey(result);
              return (
                <div key={`saveable-${key}`} className="rc-search-selectable">
                  <label className="rc-search-checkbox">
                    <input type="checkbox" checked={Boolean(selected[key])} onChange={() => setSelected((prev) => ({ ...prev, [key]: !prev[key] }))} />
                    <span>Seleccionar para guardado por lote</span>
                  </label>
                  {renderResultCard(result)}
                </div>
              );
            })}
          </div>
        </section>
      ) : null}

      {reviewableResults.length ? (
        <section className="rc-search-group">
          <div className="rc-search-group__title">Listos para revisar</div>
          <div className="rc-help">Tienen abstract o una fuente externa util, pero no un PDF guardable desde PaperFlow.</div>
          <div className="rc-card-list">
            {reviewableResults.map(renderResultCard)}
          </div>
        </section>
      ) : null}

      {metadataOnlyResults.length ? (
        <section className="rc-search-group">
          <div className="rc-search-group__title">Solo referencia bibliografica</div>
          <div className="rc-help">Estas entradas no traen abstract recuperado ni PDF guardable. Sirven para contexto, no para lectura directa dentro del flujo.</div>
          <div className="rc-card-list">
            {metadataOnlyResults.map(renderResultCard)}
          </div>
        </section>
      ) : null}

      {data && normalizedResults.length === 0 ? (
        <div className="rc-empty-state">
          <div style={{ fontWeight: 800, marginBottom: 6 }}>No encontramos resultados en este rango</div>
          <div className="rc-help">
            Prueba una consulta mas amplia, aumenta el rango temporal o desactiva el filtro de acceso abierto.
          </div>
        </div>
      ) : null}

      {data ? (
        <div className="rc-card rc-search-next-step">
          <div>
            <div className="rc-kicker">Siguiente paso sugerido</div>
            <div className="rc-card-title" style={{ marginTop: 4 }}>Pasa de la lista al analisis de contenido</div>
            <div className="rc-help">
              Cuando ya tengas una base de papers, abre el lector para comparar hallazgos con evidencia o ve a la biblioteca para procesar PDFs.
            </div>
          </div>
          <div className="rc-row">
            <Link className="rc-btn" to={`/projects/${projectId}/library`}>Abrir biblioteca</Link>
            <Link className="rc-btn rc-btn--primary" to={`/projects/${projectId}/reader`}>Ir al lector</Link>
          </div>
        </div>
      ) : null}

      {batchModalOpen ? (
        <div className="rc-modal-backdrop" onClick={() => setBatchModalOpen(false)}>
          <div className="rc-card rc-modal-card" onClick={(event) => event.stopPropagation()}>
            <div className="rc-toolbar">
              <div className="rc-card-title">Guardado por lote</div>
              <button className="rc-btn" onClick={() => setBatchModalOpen(false)}>Cerrar</button>
            </div>
            <div className="rc-help">Job {batchJobId || '—'} · estado {batchJob?.status || 'queued'} · progreso {batchJob?.progress ?? 0}%</div>
            {batchJob?.error ? <div className="rc-error">{String(batchJob.error)}</div> : null}
            <div className="rc-row" style={{ marginTop: 10 }}>
              <button className="rc-btn rc-btn--ghost" disabled={!batchJobId} onClick={() => void cancelBatch()}>
                Cancelar job
              </button>
            </div>
            <div style={{ height: 12 }} />
            {batchJob?.output ? (
              <div className="rc-chip-list">
                <span className="rc-chip rc-chip--success">Descargados: {batchJob.output?.downloaded?.length ?? 0}</span>
                <span className="rc-chip">Ya existen: {batchJob.output?.already_exists?.length ?? 0}</span>
                <span className="rc-chip">No disponibles: {batchJob.output?.not_available?.length ?? 0}</span>
                <span className="rc-chip">Fallidos: {batchJob.output?.failed?.length ?? 0}</span>
              </div>
            ) : (
              <div className="rc-help">El resumen aparecera cuando el job termine o avance lo suficiente.</div>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
