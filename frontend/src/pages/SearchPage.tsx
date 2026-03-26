import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api, isApiError, requestTimeouts } from '../services/api';
import { useAuthStore } from '../store/authStore';
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

type BatchDownloadTraceItem = {
  title: string;
  pmid?: string | null;
  pmcid?: string | null;
  doi?: string | null;
  paper_id?: string | null;
  source_provider?: string | null;
  oa_url?: string | null;
  landing_url?: string | null;
  resolved_url?: string | null;
  used_fallback?: boolean;
  final_status: 'downloaded' | 'existing' | 'unavailable' | 'failed';
  failure_reason?: string | null;
};

type BatchJobOutput = {
  items: BatchDownloadTraceItem[];
  downloaded: BatchDownloadTraceItem[];
  already_exists: BatchDownloadTraceItem[];
  not_available: BatchDownloadTraceItem[];
  failed: BatchDownloadTraceItem[];
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

type ExampleGroup = {
  label: string;
  questions: string[];
};

const RECENCY_OPTIONS: RecencyOption[] = [
  { value: 'all', label: 'Todo', years: null },
  { value: '1y', label: 'Ultimo 1 año', years: 1 },
  { value: '2y', label: 'Ultimos 2 años', years: 2 },
  { value: '5y', label: 'Ultimos 5 años', years: 5 },
  { value: '10y', label: 'Ultimos 10 años', years: 10 },
];

const SOURCE_LABELS: Record<string, string> = {
  pubmed: 'PubMed',
  europepmc: 'Europe PMC',
  doaj: 'DOAJ',
  unpaywall: 'Unpaywall',
  doi_content_negotiation: 'DOI direct',
};

const EXAMPLE_GROUPS: ExampleGroup[] = [
  {
    label: 'Medicina clínica',
    questions: [
      '¿Son los agonistas del receptor GLP-1 efectivos y seguros para la pérdida de peso a largo plazo?',
      '¿Reduce la metformina la progresión de prediabetes a diabetes tipo 2 en estudios del mundo real?',
      '¿Es la fisioterapia temprana efectiva para reducir el dolor y la discapacidad en dolor lumbar?',
    ],
  },
  {
    label: 'Atención sanitaria',
    questions: [
      '¿Aumenta la exposición a largo plazo a PM2.5 el riesgo de demencia?',
      '¿Aumentan los alimentos ultraprocesados el riesgo de enfermedad cardiovascular?',
      '¿Qué modelos mejoran adherencia al tratamiento en pacientes con enfermedades crónicas?',
    ],
  },
];

function resultKey(result: PaperMetadata) {
  return result.doi || result.pmid || result.pmcid || `${result.title}-${result.pub_year || 'na'}`;
}

function fallbackOpenTargets(result: PaperMetadata): SearchOpenTarget[] {
  const targets: SearchOpenTarget[] = [];
  if (result.oa_url) {
    const label = result.oa_url.toLowerCase().endsWith('.pdf') ? 'Abrir PDF OA' : 'Abrir fuente';
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
  const openTargets = (result.open_targets?.length ? result.open_targets : fallbackOpenTargets(result)).filter(
    (target, targetIndex, all) => all.findIndex((candidate) => candidate.url === target.url) === targetIndex,
  );
  const hasAbstract = typeof result.has_abstract === 'boolean' ? result.has_abstract : Boolean(String(result.abstract || '').trim());
  const canOpenExternal =
    typeof result.can_open_external === 'boolean' ? result.can_open_external : openTargets.length > 0;
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
  if (result.content_state === 'abstract_available') return 'Fuente o abstract útil';
  return 'Solo metadata';
}

function describeResult(result: PaperMetadata) {
  if (result.content_state === 'pdf_available') {
    return 'Este paper tiene un PDF de acceso abierto y se puede guardar directamente en la biblioteca.';
  }
  if (result.has_abstract) {
    return 'Hay abstract suficiente para decidir rápido si vale la pena abrir la fuente externa o guardarlo después.';
  }
  if (result.can_open_external) {
    return 'No hay abstract útil dentro de PaperFlow, pero sí una fuente externa disponible para revisarlo.';
  }
  return 'Este resultado es solo referencia bibliográfica. No hay abstract recuperado ni fuente externa útil desde aquí.';
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
  if (!selected.years) return 'Sin límite temporal';
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
  if (Boolean(left.has_abstract) !== Boolean(right.has_abstract)) {
    return Number(Boolean(right.has_abstract)) - Number(Boolean(left.has_abstract));
  }
  return String(left.title || '').localeCompare(String(right.title || ''));
}

function providerMessages(providerStatus?: Record<string, string>) {
  if (!providerStatus) return [];
  return Object.entries(providerStatus).flatMap(([provider, status]) => {
    if (status === 'ok') return [];
    if (status === 'filtered_server_side') {
      return [`${providerLabel(provider)} se ajustó al rango temporal en el servidor`];
    }
    if (status === 'error') {
      return [`${providerLabel(provider)} no respondió en esta búsqueda`];
    }
    return [`${providerLabel(provider)}: ${status}`];
  });
}

function normalizeBatchItems(raw: unknown): BatchDownloadTraceItem[] {
  if (!Array.isArray(raw)) return [];
  return raw.map((item) => ({
    title: String(item?.title || 'Paper'),
    pmid: item?.pmid ? String(item.pmid) : null,
    pmcid: item?.pmcid ? String(item.pmcid) : null,
    doi: item?.doi ? String(item.doi) : null,
    paper_id: item?.paper_id ? String(item.paper_id) : null,
    source_provider: item?.source_provider ? String(item.source_provider) : null,
    oa_url: item?.oa_url ? String(item.oa_url) : null,
    landing_url: item?.landing_url ? String(item.landing_url) : null,
    resolved_url: item?.resolved_url ? String(item.resolved_url) : null,
    used_fallback: Boolean(item?.used_fallback),
    final_status:
      item?.final_status === 'downloaded' ||
      item?.final_status === 'existing' ||
      item?.final_status === 'unavailable' ||
      item?.final_status === 'failed'
        ? item.final_status
        : 'failed',
    failure_reason: item?.failure_reason ? String(item.failure_reason) : null,
  }));
}

function normalizeBatchOutput(raw: unknown): BatchJobOutput | null {
  if (!raw || typeof raw !== 'object') return null;
  const downloaded = normalizeBatchItems((raw as Record<string, unknown>).downloaded);
  const alreadyExists = normalizeBatchItems((raw as Record<string, unknown>).already_exists);
  const notAvailable = normalizeBatchItems((raw as Record<string, unknown>).not_available);
  const failed = normalizeBatchItems((raw as Record<string, unknown>).failed);
  const items = normalizeBatchItems((raw as Record<string, unknown>).items);

  return {
    items: items.length ? items : [...downloaded, ...alreadyExists, ...notAvailable, ...failed],
    downloaded,
    already_exists: alreadyExists,
    not_available: notAvailable,
    failed,
  };
}

function batchStatusLabel(status: BatchDownloadTraceItem['final_status']) {
  if (status === 'downloaded') return 'Descargado';
  if (status === 'existing') return 'Ya existía';
  if (status === 'unavailable') return 'No disponible';
  return 'Falló';
}

function batchStatusClass(status: BatchDownloadTraceItem['final_status']) {
  if (status === 'downloaded') return 'rc-discover-badge rc-discover-badge--strong';
  if (status === 'existing') return 'rc-discover-badge';
  if (status === 'unavailable') return 'rc-discover-badge rc-discover-badge--warning';
  return 'rc-discover-badge rc-discover-badge--danger';
}

function apiErrorDetail(error: unknown, fallback: string) {
  if (!isApiError(error)) return fallback;
  const detail = error.response?.data;
  if (detail && typeof detail === 'object' && 'detail' in detail && typeof detail.detail === 'string') {
    return detail.detail;
  }
  return error.message || fallback;
}

export default function SearchPage() {
  const { projectId } = useParams();
  const toast = useToast();
  const user = useAuthStore((state) => state.user);

  const [query, setQuery] = useState('');
  const [mode, setMode] = useState<'search' | 'agent'>('search');
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [maxResults, setMaxResults] = useState<number>(20);
  const [recency, setRecency] = useState<RecencyOption['value']>('5y');
  const [openAccessOnly, setOpenAccessOnly] = useState(false);
  const [loading, setLoading] = useState(false);
  const [pageError, setPageError] = useState<string | null>(null);
  const [data, setData] = useState<SearchResponse | null>(null);
  const [resultStates, setResultStates] = useState<Record<string, ResultUiState>>({});
  const [selected, setSelected] = useState<Record<string, boolean>>({});
  const [batchJobId, setBatchJobId] = useState<string | null>(null);
  const [batchJob, setBatchJob] = useState<{ status: string; progress: number; error?: string | null; output?: BatchJobOutput | null } | null>(null);
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
  const userName = user?.full_name || user?.email?.split('@')[0] || 'investigador';

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
    } catch (error: unknown) {
      setPageError(apiErrorDetail(error, 'La búsqueda falló'));
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
      const payload: Record<string, unknown> = { project_id: projectId, title: result.title };
      if (result.doi) payload.doi = result.doi;
      if (result.pmid) payload.pmid = result.pmid;

      const response = await api.post('/papers/download', payload);
      const duplicate = Boolean(response.data?.duplicate);
      patchResultState(key, { saveStatus: duplicate ? 'duplicate' : 'saved', error: null });
      toast.info(
        duplicate ? 'Duplicado' : 'Guardado',
        duplicate ? 'El paper ya existe en este proyecto.' : 'PDF guardado en la biblioteca del proyecto.',
      );
    } catch (error: unknown) {
      patchResultState(key, { saveStatus: 'error', error: apiErrorDetail(error, 'La descarga falló') });
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
      setBatchJob({ status: 'queued', progress: 0, error: null, output: null });
      setBatchModalOpen(true);
    } catch (error: unknown) {
      setPageError(apiErrorDetail(error, 'La descarga por lote falló'));
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
        const output = normalizeBatchOutput(result?.output || result?.rq_result?.output);
        if (alive) setBatchJob({ status, progress, error, output });
        if (status === 'completed' || status === 'failed' || status === 'cancelled') return;
      } catch (error: unknown) {
        if (alive) {
          setBatchJob((prev) => prev || { status: 'queued', progress: 0, error: apiErrorDetail(error, 'La consulta del job falló') });
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

  function applyExample(question: string) {
    setQuery(question);
    setData(null);
    setPageError(null);
  }

  function renderResultCard(result: PaperMetadata) {
    const key = resultKey(result);
    const uiState = resultStates[key] || {};
    const detailsLabel = result.has_abstract ? 'Ver abstract' : 'Ver detalle';
    const statusBadge =
      uiState.saveStatus === 'saved'
        ? 'Guardado'
        : uiState.saveStatus === 'duplicate'
          ? 'Ya está en la biblioteca'
          : contentStateLabel(result);

    return (
      <article
        key={key}
        data-testid={`search-result-card-${result._uiIndex}`}
        data-pub-year={typeof result.pub_year === 'number' ? result.pub_year : ''}
        className="rc-discover-result-card"
      >
        <div className="rc-discover-result-card__header">
          <div style={{ flex: 1, minWidth: 260 }}>
            <h3 className="rc-discover-result-card__title">{result.title}</h3>
            <div className="rc-discover-result-card__byline">
              {result.authors?.length ? result.authors.slice(0, 6).join(', ') : 'Autor no disponible'}
            </div>
            <div className="rc-discover-result-card__journal">
              {result.journal || 'Revista no disponible'}
              {result.pub_year ? ` · ${result.pub_year}` : ' · Año no disponible'}
            </div>
          </div>
          <div className="rc-discover-badges">
            <span className="rc-discover-badge">{providerLabel(result.source)}</span>
            {isRecent(result, recency) ? <span className="rc-discover-badge rc-discover-badge--strong">Reciente</span> : null}
            {result.has_abstract ? <span className="rc-discover-badge">Tiene abstract</span> : <span className="rc-discover-badge">Sin abstract</span>}
            {result.is_open_access ? <span className="rc-discover-badge rc-discover-badge--strong">Open access</span> : null}
            {result.can_save_pdf ? <span className="rc-discover-badge rc-discover-badge--strong">PDF disponible</span> : null}
            {!result.can_save_pdf && !result.has_abstract && !result.can_open_external ? (
              <span className="rc-discover-badge">Solo metadata</span>
            ) : null}
          </div>
        </div>

        <div className="rc-discover-result-card__meta">
          <span>Estado: {statusBadge}</span>
          {result.doi ? <span>DOI: {result.doi}</span> : null}
          {result.pmid ? <span>PMID: {result.pmid}</span> : null}
          {result.pmcid ? <span>PMCID: {result.pmcid}</span> : null}
        </div>

        <p className="rc-discover-result-card__summary">{describeResult(result)}</p>
        {uiState.error ? <div className="rc-error">{uiState.error}</div> : null}

        <div className="rc-discover-result-card__actions">
          <button
            data-testid={`search-details-${result._uiIndex}`}
            className="rc-btn rc-btn--subtle"
            type="button"
            onClick={() => toggleExpanded(key)}
          >
            {uiState.expanded ? 'Ocultar detalle' : detailsLabel}
          </button>

          {result.open_targets?.map((target) => (
            <a
              key={`${key}-${target.kind}`}
              data-testid={`search-open-${result._uiIndex}-${target.kind}`}
              className="rc-btn rc-btn--subtle"
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
                  ? 'Ya está en la biblioteca'
                  : uiState.saveStatus === 'error'
                    ? 'Reintentar guardado'
                    : uiState.saveStatus === 'saving'
                      ? 'Guardando…'
                      : 'Guardar PDF'}
            </button>
          ) : (
            <span className="rc-discover-result-card__disabled">No disponible para guardar</span>
          )}
        </div>

        {uiState.expanded ? (
          <div className="rc-discover-result-card__detail">
            <div className="rc-discover-result-card__detail-grid">
              <div>
                <div className="rc-kicker">Abstract</div>
                {result.has_abstract ? (
                  <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.65 }}>{result.abstract}</div>
                ) : (
                  <div className="rc-help">
                    PaperFlow no recuperó abstract para este paper. Si existe una fuente externa, revísala antes de decidir si merece entrar a tu flujo.
                  </div>
                )}
              </div>

              <div>
                <div className="rc-kicker">Disponibilidad</div>
                <div className="rc-help">Proveedor: {providerLabel(result.source)}</div>
                <div className="rc-help">Contenido: {contentStateLabel(result)}</div>
                <div className="rc-help">Fuente externa: {result.can_open_external ? 'Sí' : 'No'}</div>
                <div className="rc-help">PDF guardable: {result.can_save_pdf ? 'Sí' : 'No'}</div>
                <div className="rc-help">Open access: {result.is_open_access ? 'Sí' : 'No'}</div>
              </div>
            </div>
          </div>
        ) : null}
      </article>
    );
  }

  return (
    <div className="rc-discover-page">
      <div className="rc-discover-topbar">
        <div className="rc-discover-topbar__project">Proyecto activo · Descubrir</div>
        <Link className="rc-discover-topbar__cta" to={`/projects/${projectId}/drafts`}>
          Mejorar
        </Link>
      </div>

      <section className="rc-discover-hero">
        <div className="rc-discover-hero__copy">
          <h1>Hola {userName}, ¿Qué te gustaría investigar hoy?</h1>
          <p>
            Formula una pregunta, ajusta la recencia y separa con claridad qué papers puedes abrir, revisar o guardar
            de inmediato.
          </p>
        </div>

        <div className="rc-discover-composer">
          <textarea
            data-testid="search-query-input"
            className="rc-discover-composer__input"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={
              mode === 'search'
                ? 'Haz una pregunta de investigación o ingresa un tema…'
                : 'Describe qué quieres investigar y priorizar…'
            }
          />

          <div className="rc-discover-composer__footer">
            <div className="rc-discover-mode-toggle">
              <button
                type="button"
                className={`rc-discover-mode-toggle__option ${mode === 'search' ? 'is-active' : ''}`}
                onClick={() => setMode('search')}
              >
                Search
              </button>
              <button
                type="button"
                className={`rc-discover-mode-toggle__option ${mode === 'agent' ? 'is-active' : ''}`}
                onClick={() => setMode('agent')}
              >
                Agent
              </button>
            </div>

            <button
              type="button"
              className={`rc-discover-filter-toggle ${filtersOpen ? 'is-open' : ''}`}
              onClick={() => setFiltersOpen((current) => !current)}
            >
              Filtros
            </button>

            <button
              data-testid="search-submit-button"
              className="rc-discover-submit"
              disabled={!canSearch || loading}
              onClick={() => void runSearch()}
            >
              {loading ? '…' : '→'}
            </button>
          </div>

          <div className={`rc-discover-filter-panel ${filtersOpen ? 'is-open' : ''}`}>
            <label className="rc-discover-filter-field">
              <span>Recencia</span>
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

            <label className="rc-discover-filter-field">
              <span>Máximo</span>
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

            <label className="rc-discover-toggle">
              <input
                data-testid="search-open-access-toggle"
                type="checkbox"
                checked={openAccessOnly}
                onChange={(event) => setOpenAccessOnly(event.target.checked)}
              />
              <span>Solo acceso abierto</span>
            </label>
          </div>
        </div>

        <div className="rc-discover-agent-strip">
          <span>Our Research Agents:</span>
          <button type="button" className="rc-discover-mini-chip" onClick={() => { setMode('agent'); applyExample('Generate a literature review outline for this topic'); }}>
            Literature Review
          </button>
          <button type="button" className="rc-discover-mini-chip" onClick={() => { setMode('agent'); applyExample('Create a deep research report plan for this question'); }}>
            Deep Research Report
          </button>
          <Link className="rc-discover-mini-chip" to={`/projects/${projectId}/reader`}>
            Chat with PDF
          </Link>
        </div>
      </section>

      {!data ? (
        <section className="rc-discover-suggestions">
          <div className="rc-discover-suggestions__heading">Explora preguntas de investigación de ejemplo</div>
          {EXAMPLE_GROUPS.map((group) => (
            <div key={group.label} className="rc-discover-suggestions__group">
              <div className="rc-discover-suggestions__label">{group.label}</div>
              <div className="rc-discover-suggestions__list">
                {group.questions.map((question) => (
                  <button key={question} type="button" className="rc-discover-question-pill" onClick={() => applyExample(question)}>
                    {question}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </section>
      ) : null}

      {pageError ? <div className="rc-error">{String(pageError)}</div> : null}

      {loading ? (
        <div className="rc-card rc-discover-loading-card">
          <Skeleton height={14} width="40%" />
          <div style={{ height: 14 }} />
          <SkeletonLines lines={7} lineHeight={12} lastLineWidth="58%" />
        </div>
      ) : null}

      {data ? (
        <div className="rc-discover-results-shell">
          <section className="rc-discover-summary-card">
            <div>
              <div className="rc-card-title" style={{ marginBottom: 4 }}>
                {mode === 'search' ? 'Resultados de búsqueda' : 'Resultados priorizados'}
              </div>
              <div className="rc-help">
                {data.count} resultados · rango {currentRangeLabel(recency)} ·{' '}
                {openAccessOnly ? 'solo acceso abierto' : 'todas las fuentes disponibles'}
              </div>
            </div>

            <div className="rc-discover-badges">
              <span className="rc-discover-badge">{saveableResults.length} guardables</span>
              <span className="rc-discover-badge">{reviewableResults.length} para revisar</span>
              <span className="rc-discover-badge">{metadataOnlyResults.length} solo referencia</span>
              {data.cached ? <span className="rc-discover-badge">Cache</span> : null}
              {data.partial_success ? <span className="rc-discover-badge">Búsqueda parcial</span> : null}
            </div>

            {providerWarnings.length ? (
              <div className="rc-discover-warning-list">
                {providerWarnings.map((warning) => (
                  <div key={warning} className="rc-help">
                    {warning}
                  </div>
                ))}
              </div>
            ) : null}
          </section>

          {saveableResults.length ? (
            <section className="rc-discover-result-group">
              <div className="rc-discover-result-group__header">
                <div>
                  <div className="rc-discover-section-label">Listos para guardar</div>
                  <p>Los mejores para empezar: tienen PDF OA y pueden entrar directo a tu biblioteca.</p>
                </div>
                <div className="rc-row">
                  <button className="rc-btn rc-btn--subtle" onClick={selectAllSaveable}>
                    Seleccionar todos
                  </button>
                  <button className="rc-btn rc-btn--subtle" onClick={clearSelection} disabled={selectedCount === 0}>
                    Limpiar ({selectedCount})
                  </button>
                  <button className="rc-btn rc-btn--primary" onClick={() => void startBatchDownload()} disabled={selectedCount === 0}>
                    Guardar seleccionados ({selectedCount})
                  </button>
                </div>
              </div>

              <div className="rc-discover-card-list">
                {saveableResults.map((result) => {
                  const key = resultKey(result);
                  return (
                    <div key={`saveable-${key}`} className="rc-discover-selectable">
                      <label className="rc-discover-checkline">
                        <input
                          type="checkbox"
                          checked={Boolean(selected[key])}
                          onChange={() => setSelected((prev) => ({ ...prev, [key]: !prev[key] }))}
                        />
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
            <section className="rc-discover-result-group">
              <div className="rc-discover-result-group__header">
                <div>
                  <div className="rc-discover-section-label">Listos para revisar</div>
                  <p>Tienen abstract o fuente externa útil, pero no un PDF guardable desde PaperFlow.</p>
                </div>
              </div>
              <div className="rc-discover-card-list">{reviewableResults.map(renderResultCard)}</div>
            </section>
          ) : null}

          {metadataOnlyResults.length ? (
            <section className="rc-discover-result-group">
              <div className="rc-discover-result-group__header">
                <div>
                  <div className="rc-discover-section-label">Solo referencia bibliográfica</div>
                  <p>Sirven para contexto, pero no se muestran como si PaperFlow ya tuviera el artículo completo.</p>
                </div>
              </div>
              <div className="rc-discover-card-list">{metadataOnlyResults.map(renderResultCard)}</div>
            </section>
          ) : null}

          {normalizedResults.length === 0 ? (
            <div className="rc-empty-state">
              <div style={{ fontWeight: 800, marginBottom: 6 }}>No encontramos resultados en este rango</div>
              <div className="rc-help">Prueba una consulta más amplia, aumenta el rango temporal o quita el filtro de acceso abierto.</div>
            </div>
          ) : null}

          <section className="rc-discover-next-step">
            <div>
              <div className="rc-kicker">Siguiente paso sugerido</div>
              <div className="rc-card-title" style={{ marginTop: 4 }}>
                Sigue con lectura o biblioteca
              </div>
              <div className="rc-help">
                Cuando ya tengas una base útil, abre el lector para comparar hallazgos o pasa a la biblioteca para trabajar con los PDFs guardados.
              </div>
            </div>
            <div className="rc-row">
              <Link className="rc-btn rc-btn--subtle" to={`/projects/${projectId}/library`}>
                Abrir biblioteca
              </Link>
              <Link className="rc-btn rc-btn--primary" to={`/projects/${projectId}/reader`}>
                Ir al lector
              </Link>
            </div>
          </section>
        </div>
      ) : null}

      {batchModalOpen ? (
        <div className="rc-modal-backdrop" onClick={() => setBatchModalOpen(false)}>
          <div
            className="rc-card rc-modal-card"
            role="dialog"
            aria-modal="true"
            aria-label="Guardado por lote"
            data-testid="batch-trace-modal"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="rc-toolbar">
              <div className="rc-card-title" data-testid="batch-trace-title">
                Guardado por lote
              </div>
              <button className="rc-btn rc-btn--subtle" onClick={() => setBatchModalOpen(false)}>
                Cerrar
              </button>
            </div>
            <div className="rc-help">
              Job {batchJobId || '—'} · estado {batchJob?.status || 'queued'} · progreso {batchJob?.progress ?? 0}%
            </div>
            {batchJob?.error ? <div className="rc-error">{String(batchJob.error)}</div> : null}
            <div className="rc-row" style={{ marginTop: 10 }}>
              <button className="rc-btn rc-btn--subtle" disabled={!batchJobId} onClick={() => void cancelBatch()}>
                Cancelar job
              </button>
            </div>
            <div style={{ height: 12 }} />
            {batchJob?.output ? (
              <div className="rc-batch-trace">
                <div className="rc-discover-badges">
                  <span className="rc-discover-badge rc-discover-badge--strong">
                    Descargados: {batchJob.output?.downloaded?.length ?? 0}
                  </span>
                  <span className="rc-discover-badge">Ya existen: {batchJob.output?.already_exists?.length ?? 0}</span>
                  <span className="rc-discover-badge">No disponibles: {batchJob.output?.not_available?.length ?? 0}</span>
                  <span className="rc-discover-badge">Fallidos: {batchJob.output?.failed?.length ?? 0}</span>
                </div>

                {batchJob.output.items.length ? (
                  <div className="rc-batch-trace__list">
                    {batchJob.output.items.map((item, index) => (
                      <article key={`${item.title}-${index}`} data-testid={`batch-trace-row-${index}`} className="rc-batch-trace__card">
                        <div className="rc-batch-trace__header">
                          <div>
                            <div className="rc-card-title" style={{ marginBottom: 4 }}>
                              {item.title}
                            </div>
                            <div className="rc-help">
                              {item.source_provider ? `Proveedor: ${providerLabel(item.source_provider)}` : 'Proveedor no resuelto'}
                              {item.paper_id ? ` · Paper ID ${item.paper_id}` : ''}
                            </div>
                          </div>
                          <div className="rc-discover-badges">
                            <span className={batchStatusClass(item.final_status)}>{batchStatusLabel(item.final_status)}</span>
                            {item.used_fallback ? <span className="rc-discover-badge">Usó fallback</span> : null}
                          </div>
                        </div>

                        <div className="rc-batch-trace__meta">
                          {item.doi ? <span>DOI: {item.doi}</span> : null}
                          {item.pmid ? <span>PMID: {item.pmid}</span> : null}
                          {item.pmcid ? <span>PMCID: {item.pmcid}</span> : null}
                        </div>

                        <div className="rc-batch-trace__grid">
                          <div>
                            <div className="rc-kicker">OA URL</div>
                            {item.oa_url ? (
                              <a href={item.oa_url} target="_blank" rel="noopener noreferrer">
                                {item.oa_url}
                              </a>
                            ) : (
                              <div className="rc-help">No disponible</div>
                            )}
                          </div>
                          <div>
                            <div className="rc-kicker">Landing URL</div>
                            {item.landing_url ? (
                              <a href={item.landing_url} target="_blank" rel="noopener noreferrer">
                                {item.landing_url}
                              </a>
                            ) : (
                              <div className="rc-help">No disponible</div>
                            )}
                          </div>
                          <div>
                            <div className="rc-kicker">URL final usada</div>
                            {item.resolved_url ? (
                              <a href={item.resolved_url} target="_blank" rel="noopener noreferrer">
                                {item.resolved_url}
                              </a>
                            ) : (
                              <div className="rc-help">No se llegó a resolver</div>
                            )}
                          </div>
                          <div>
                            <div className="rc-kicker">Motivo final</div>
                            <div className="rc-help">
                              {item.failure_reason ||
                                (item.final_status === 'downloaded'
                                  ? 'PDF guardado en la biblioteca.'
                                  : item.final_status === 'existing'
                                    ? 'El paper ya existía en el proyecto.'
                                    : 'No hubo un PDF OA descargable para este paper.')}
                            </div>
                          </div>
                        </div>
                      </article>
                    ))}
                  </div>
                ) : (
                  <div className="rc-help">Todavía no hay papers procesados en este batch.</div>
                )}
              </div>
            ) : (
              <div className="rc-help">El resumen aparecerá cuando el job termine o avance lo suficiente.</div>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
