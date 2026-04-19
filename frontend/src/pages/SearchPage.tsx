import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';
import { useToast } from '../ui/Toast/ToastProvider';
import { useSearch } from '../hooks/useSearch';
import { useSearchFilters } from '../hooks/useSearchFilters';
import { useSearchHistory } from '../hooks/useSearchHistory';
import { useBatchDownload } from '../hooks/useBatchDownload';
import { SearchResultCard } from '../components/search/SearchResultCard';
import { getTechnicalDownloadFailure, humanizeDownloadFailure } from '../components/search/downloadMessaging';
import { Skeleton, SkeletonLines } from '../ui/Skeleton/Skeleton';
import type { BatchDownloadTraceItem } from '../types/api';

const SEARCH_PAGE_SIZE = 10;

const SOURCE_LABELS: Record<string, string> = {
  pubmed: 'PubMed',
  europepmc: 'Europe PMC',
  doaj: 'DOAJ',
  semantic_scholar: 'Semantic Scholar',
  unpaywall: 'Unpaywall',
  doi_content_negotiation: 'DOI direct',
  user_provided_oa: 'OA provista por el usuario',
};

function providerLabel(source?: string | null) {
  return SOURCE_LABELS[String(source || '').toLowerCase()] || 'Fuente externa';
}

function batchStatusLabel(status: BatchDownloadTraceItem['final_status']) {
  if (status === 'downloaded') return 'Descargado';
  if (status === 'existing') return 'Ya existía';
  if (status === 'unavailable') return 'No disponible';
  return 'Fallido';
}

function batchStatusClass(status: BatchDownloadTraceItem['final_status']) {
  if (status === 'downloaded') return 'rc-badge rc-badge--success';
  if (status === 'existing') return 'rc-badge';
  return 'rc-badge rc-badge--danger';
}

export default function SearchPage() {
  const { projectId } = useParams();
    const toast = useToast();
  const search = useSearch(projectId);
  const [synthesis, setSynthesis] = useState<{ answer?: string, loading?: boolean, error?: string | null }>({});

  const filters = useSearchFilters();
  const batch = useBatchDownload();
  const history = useSearchHistory({
    projectId,
    setLoading: () => {},
    setError: search.setError,
    onResults: (data, q) => { search.setData(data); search.setQuery(q); batch.resetBatch(); },
  });

  const { data: project } = useQuery<{ title: string; clinical_area?: string | null }>({
    queryKey: ['project-info', projectId],
    queryFn: async () => {
      const r = await api.get(`/projects/${projectId}`);
      return r.data as { title: string; clinical_area?: string | null };
    },
    enabled: !!projectId,
    staleTime: 300_000,
  });

  const pageResults = (search.data?.results || []).slice(
    search.searchPage * SEARCH_PAGE_SIZE,
    (search.searchPage + 1) * SEARCH_PAGE_SIZE,
  );
  const totalPages = Math.ceil(((search.data?.results.length) || 1) / SEARCH_PAGE_SIZE);
  const activeFilterChips = [
    filters.yearFrom ? `Desde ${filters.yearFrom}` : null,
    filters.yearTo ? `Hasta ${filters.yearTo}` : null,
    filters.journalFilter ? `Revista: ${filters.journalFilter}` : null,
    filters.sourceFilter ? `Fuente: ${filters.sourceFilter}` : null,
    filters.oaOnly ? 'Solo Open Access' : null,
  ].filter(Boolean) as string[];

  function handleSearch() {
    setSynthesis({});
    search.runSearch(filters.buildPayload(), history.loadHistory);
  }

  async function synthesizeResults() {
    if (!search.data?.results.length) return;
    setSynthesis({ loading: true, error: null });
    try {
      const response = await api.post('/search/synthesize', {
        query: search.query,
        papers: search.data.results.slice(0, 10),
      });
      setSynthesis({ answer: response.data.answer, loading: false });
    } catch (e: any) {
      setSynthesis({ error: e?.response?.data?.detail || 'Failed to synthesize search results.', loading: false });
    }
  }

  async function saveSynthesisToWriting() {
    if (!projectId || !synthesis.answer) return;
    try {
      const documentRes = await api.post('/writing/documents', {
        project_id: projectId,
        title: search.query || 'Search grounded synthesis',
        mode: 'systematic_review',
      });
      const documentId = String(documentRes.data?.id || '');
      if (!documentId) throw new Error('Writing document was created without id');

      const markdown = [
        '## Grounded search synthesis',
        '',
        synthesis.answer,
        '',
        '_This section was generated from the Search stage and saved to Writing for full traceable drafting._',
      ].join('\n');
      await api.patch(`/writing/documents/${documentId}/sections/introduction`, {
        content_markdown: markdown,
      });

      toast.success('Saved to Writing', 'The synthesis was saved in a new writing document under Introduction.');
    } catch (e: any) {
      toast.error('Save failed', e?.response?.data?.detail || 'The server could not save this synthesis into writing.');
    }
  }

  return (
    <div className="pg-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
      <div className="pg-row-between">
        <div>
          <div className="pg-kicker" style={{ marginBottom: 4 }}>Etapa 1 · Búsqueda</div>
          <h1 className="pg-h1">Búsqueda federada</h1>
          <p className="pg-muted" style={{ marginTop: 4, fontSize: 14, maxWidth: 620 }}>
            PubMed, Europe PMC y DOAJ en una sola consulta.
            {projectId && project ? ` Los resultados se guardan directamente en ${project.title}.` : ''}
          </p>
        </div>
        <div className="pg-row">
          <button className="pg-btn pg-btn--sm" data-testid="search-filters-toggle" onClick={filters.toggleFilters}>
            {filters.showFilters ? 'Ocultar filtros' : 'Filtros'}
          </button>
          {projectId ? (
            <Link className="pg-btn pg-btn--sm" style={{ textDecoration: 'none' }} to={`/projects/${projectId}/library`}>
              Biblioteca →
            </Link>
          ) : null}
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <div className="pg-card" style={{ padding: 18 }}>
            <div className="pg-row" style={{ alignItems: 'flex-end', gap: 10 }}>
              <div style={{ flex: 1, minWidth: 260 }}>
                <label htmlFor="search-query" className="pg-label">Pregunta de investigación</label>
                <datalist id="search-query-suggestions">
                  {history.searchHistory.slice(0, 10).map((item, i) => (
                    <option key={i} value={item.query} />
                  ))}
                </datalist>
                <input
                  id="search-query"
                  className="pg-input"
                  data-testid="search-query-input"
                  list="search-query-suggestions"
                  value={search.query}
                  onChange={(e) => search.setQuery(e.target.value)}
                  placeholder="ej. ACL reconstruction hamstring vs BPTB meta-analysis"
                  onKeyDown={(e) => { if (e.key === 'Enter' && search.canSearch && !search.loading) handleSearch(); }}
                />
              </div>
              <div style={{ width: 100 }}>
                <label htmlFor="search-max-results" className="pg-label">Máx.</label>
                <input id="search-max-results" className="pg-input" type="number" value={search.maxResults} min={1} max={100} onChange={(e) => search.setMaxResults(Number(e.target.value))} />
              </div>
              <button className="pg-btn pg-btn--primary" data-testid="search-submit-button" disabled={!search.canSearch || search.loading} onClick={handleSearch}>
                {search.loading ? 'Buscando…' : 'Buscar'}
              </button>
            </div>

            {filters.showFilters && (
              <div style={{ marginTop: 14, display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'flex-end', paddingTop: 14, borderTop: '1px solid var(--pg-line)' }}>
                <div style={{ width: 100 }}><label htmlFor="search-year-from" className="pg-label">Desde</label><input id="search-year-from" className="pg-input" data-testid="search-year-from-input" type="number" value={filters.yearFrom} min={1900} max={2030} placeholder="2018" onChange={(e) => filters.setYearFrom(e.target.value)} /></div>
                <div style={{ width: 100 }}><label htmlFor="search-year-to" className="pg-label">Hasta</label><input id="search-year-to" className="pg-input" data-testid="search-year-to-input" type="number" value={filters.yearTo} min={1900} max={2030} placeholder="2025" onChange={(e) => filters.setYearTo(e.target.value)} /></div>
                <div style={{ width: 180 }}><label htmlFor="search-journal" className="pg-label">Revista</label><input id="search-journal" className="pg-input" value={filters.journalFilter} placeholder="e.g. Lancet" onChange={(e) => filters.setJournalFilter(e.target.value)} /></div>
                <div style={{ width: 140 }}>
                  <label htmlFor="search-source" className="pg-label">Fuente</label>
                  <select id="search-source" className="pg-input" value={filters.sourceFilter} onChange={(e) => filters.setSourceFilter(e.target.value)}>
                    <option value="">Todas</option>
                    <option value="pubmed">PubMed</option>
                    <option value="europepmc">Europe PMC</option>
                    <option value="doaj">DOAJ</option>
                  </select>
                </div>
                <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, cursor: 'pointer', paddingBottom: 8 }}>
                  <input type="checkbox" checked={filters.oaOnly} onChange={(e) => filters.setOaOnly(e.target.checked)} /> Open Access
                </label>
              </div>
            )}

            {activeFilterChips.length > 0 && (
              <div className="pg-chips" style={{ marginTop: 12 }}>
                {activeFilterChips.map((chip) => (
                  <span key={chip} className="pg-chip" style={{ cursor: 'default' }}>{chip}</span>
                ))}
              </div>
            )}
          </div>

          {search.error ? (
            <div style={{ padding: '10px 12px', borderRadius: 10, background: '#FEF2F2', border: '1px solid #FECACA', color: '#B91C1C', fontSize: 13 }}>{String(search.error)}</div>
          ) : null}

          {search.data ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div className="pg-row-between">
                <div className="pg-muted" style={{ fontSize: 13 }}>
                  <strong style={{ color: 'var(--pg-ink)' }}>{search.data.count}</strong> resultado{search.data.count !== 1 ? 's' : ''}
                  {search.data.cached && <span> (cached)</span>}
                  {search.data.sources && search.data.sources.length > 0 && (
                    <span> · {search.data.sources.join(', ')}</span>
                  )}
                </div>
                {search.data.query_translation && (
                  <div className="pg-soft" style={{ fontStyle: 'italic' }}>Traducción: "{search.data.query_translation}"</div>
                )}
              </div>

              {search.data.warnings && search.data.warnings.length > 0 && (
                <div
                  className="pg-card"
                  data-testid="search-warning-banner"
                  style={{
                    borderColor: 'rgba(217,119,6,0.3)',
                    background: 'rgba(217,119,6,0.06)',
                    padding: 14,
                  }}
                >
                  <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 4 }}>Advertencias</div>
                  {search.data.warnings.map((warning, index) => (
                    <div key={`${warning}-${index}`} className="pg-muted" style={{ fontSize: 13 }}>
                      {warning}
                    </div>
                  ))}
                </div>
              )}

              {search.loading && (
                <div className="pg-card" style={{ padding: 16 }}>
                  <Skeleton height={14} width="40%" />
                  <div style={{ height: 10 }} />
                  <SkeletonLines lines={6} lineHeight={12} lastLineWidth="60%" />
                </div>
              )}

              {!search.loading && search.data.results.length > 0 && (
                <div className="pg-card" style={{ padding: 18, background: 'var(--pg-surface)' }}>
                  <div className="pg-row-between" style={{ flexWrap: 'wrap', gap: 10 }}>
                    <div style={{ flex: 1, minWidth: 240 }}>
                      <div className="pg-kicker" style={{ marginBottom: 4 }}>Síntesis IA</div>
                      <div className="pg-muted" style={{ fontSize: 13 }}>
                        Resume los {Math.min(search.data.results.length, 10)} mejores resultados en un párrafo respaldado.
                      </div>
                    </div>
                    {!synthesis.answer && !synthesis.loading && (
                      <button className="pg-btn pg-btn--primary pg-btn--sm" onClick={synthesizeResults}>
                        Sintetizar evidencia
                      </button>
                    )}
                  </div>

                  {synthesis.loading && (
                    <div className="pg-muted" style={{ marginTop: 12, fontSize: 13 }}>Analizando papers…</div>
                  )}

                  {synthesis.error && (
                    <div style={{ marginTop: 12, padding: '10px 12px', borderRadius: 10, background: '#FEF2F2', border: '1px solid #FECACA', color: '#B91C1C', fontSize: 13 }}>{synthesis.error}</div>
                  )}

                  {synthesis.answer && (
                    <div style={{ marginTop: 14 }}>
                      <div style={{
                        whiteSpace: 'pre-wrap', fontSize: 14, lineHeight: 1.65, color: 'var(--pg-text)',
                        background: '#fff', borderRadius: 10, padding: 14,
                        border: '1px solid var(--pg-line)',
                      }}>
                        {synthesis.answer}
                      </div>
                      {projectId && (
                        <div style={{ marginTop: 12, display: 'flex', justifyContent: 'flex-end' }}>
                          <button className="pg-btn pg-btn--sm" onClick={saveSynthesisToWriting}>
                            Guardar en Escritura
                          </button>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              <div className="pg-card" style={{ padding: 12 }}>
                <div className="pg-row">
                  <button className="pg-btn pg-btn--sm" onClick={search.selectAllOA} disabled={!search.data.results.length}>Seleccionar todos OA</button>
                  <button className="pg-btn pg-btn--sm" onClick={search.clearSelection} disabled={search.selectedCount === 0}>Limpiar ({search.selectedCount})</button>
                  {projectId ? (
                    <button
                      className="pg-btn pg-btn--primary pg-btn--sm"
                      data-testid="batch-download-button"
                      disabled={search.selectedCount === 0}
                      onClick={() => batch.startBatchDownload(projectId, search.selectedPapers, search.setError)}
                    >
                      Añadir {search.selectedCount > 0 ? `(${search.selectedCount})` : ''} a Biblioteca
                    </button>
                  ) : (
                    <span className="pg-muted" style={{ fontSize: 13 }}>Abre un proyecto para guardar.</span>
                  )}
                  {batch.batchJobId && (
                    <button className="pg-btn pg-btn--sm" onClick={() => batch.setBatchModalOpen(true)}>Ver descarga</button>
                  )}
                </div>
              </div>

              {pageResults.map((r, i) => (
                <SearchResultCard key={r.doi || r.pmid || String(search.searchPage * SEARCH_PAGE_SIZE + i)} r={r} idx={search.searchPage * SEARCH_PAGE_SIZE + i} search={search} />
              ))}

              {totalPages > 1 && (
                <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 12, padding: '10px 0' }}>
                  <button className="pg-btn pg-btn--sm" disabled={search.searchPage === 0} onClick={() => search.setSearchPage(Math.max(0, search.searchPage - 1))}>← Anterior</button>
                  <span className="pg-muted" style={{ fontSize: 13 }}>Página {search.searchPage + 1} de {totalPages}</span>
                  <button className="pg-btn pg-btn--sm" disabled={search.searchPage >= totalPages - 1} onClick={() => search.setSearchPage(Math.min(totalPages - 1, search.searchPage + 1))}>Siguiente →</button>
                </div>
              )}
            </div>
          ) : !search.loading ? (
            <div style={{ textAlign: 'center', padding: '56px 24px' }}>
              <div className="pg-h3" style={{ marginBottom: 6 }}>Busca en PubMed, Europe PMC y DOAJ</div>
              <div className="pg-muted" style={{ fontSize: 14, maxWidth: 420, margin: '0 auto' }}>
                Escribe una consulta arriba para encontrar papers relevantes. Ordenados por relevancia.
              </div>
            </div>
          ) : null}
      </div>

      {batch.batchModalOpen && (
        <div data-testid="batch-trace-modal" style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.35)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20, zIndex: 50 }} onClick={() => batch.setBatchModalOpen(false)}>
          <div className="rc-card" style={{ width: 'min(520px, 96vw)' }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <div data-testid="batch-trace-title" style={{ fontWeight: 800, fontFamily: 'var(--font-display)' }}>Batch OA Download</div>
              <button className="rc-btn rc-btn--sm rc-btn--ghost" aria-label="Close" title="Close" onClick={() => batch.setBatchModalOpen(false)}>✕</button>
            </div>
            <div className="rc-help" style={{ marginBottom: 8 }}>Job: <span style={{ fontFamily: 'monospace' }}>{batch.batchJobId}</span></div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
              <span className="rc-help">Status: <b>{batch.batchJob?.status || '—'}</b></span>
              <span className="rc-help">Progress: <b>{batch.batchJob?.progress ?? 0}%</b></span>
            </div>
            {(batch.batchJob?.progress ?? 0) > 0 && (
              <div className="rc-progress" style={{ marginBottom: 10 }}>
                <div style={{ width: `${batch.batchJob?.progress ?? 0}%` }} />
              </div>
            )}
            {batch.batchJob?.error && <div className="rc-error" style={{ marginBottom: 8 }}>{String(batch.batchJob.error)}</div>}
            {batch.batchJob?.output && (
              <>
                <div className="rc-row" style={{ gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
                  <span className="rc-badge rc-badge--success">Descargados: <b>{batch.batchJob.output.downloaded.length}</b></span>
                  <span className="rc-badge">Ya existían: <b>{batch.batchJob.output.already_exists.length}</b></span>
                  <span className="rc-badge">No disponibles: <b>{batch.batchJob.output.not_available.length}</b></span>
                  <span className="rc-badge rc-badge--danger">Fallidos: <b>{batch.batchJob.output.failed.length}</b></span>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10, maxHeight: '48vh', overflowY: 'auto', paddingRight: 4 }}>
                  {batch.batchJob.output.items.map((item, index) => {
                    const humanizedFailure = humanizeDownloadFailure(item.failure_reason);
                    const technicalFailure = getTechnicalDownloadFailure(item.failure_reason);
                    return (
                      <div
                        key={`${item.paper_id || item.doi || item.pmid || item.title}-${index}`}
                        className="rc-card"
                        data-testid={`batch-trace-row-${index}`}
                        style={{ padding: 12 }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'flex-start', marginBottom: 8 }}>
                          <div>
                            <div style={{ fontWeight: 700 }}>{item.title}</div>
                            <div className="rc-help">
                              {item.paper_id ? `Paper ID: ${item.paper_id}` : 'Paper aún no persistido'}
                            </div>
                            <div className="rc-help">
                              {item.source_provider ? `Proveedor: ${providerLabel(item.source_provider)}` : 'Proveedor no resuelto'}
                            </div>
                          </div>
                          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                            <span className={batchStatusClass(item.final_status)}>{batchStatusLabel(item.final_status)}</span>
                            {item.used_fallback ? <span className="rc-badge">Usó fallback</span> : null}
                          </div>
                        </div>
                        <div className="rc-help" style={{ display: 'grid', gap: 6 }}>
                          <div>DOI: {item.doi || '—'}</div>
                          <div>PMID: {item.pmid || '—'}</div>
                          <div>OA URL: {item.oa_url ? <a href={item.oa_url} target="_blank" rel="noopener noreferrer">{item.oa_url}</a> : '—'}</div>
                          <div>Landing URL: {item.landing_url ? <a href={item.landing_url} target="_blank" rel="noopener noreferrer">{item.landing_url}</a> : '—'}</div>
                          <div>Resolved URL: {item.resolved_url ? <a href={item.resolved_url} target="_blank" rel="noopener noreferrer">{item.resolved_url}</a> : '—'}</div>
                          <div>Resultado: {humanizedFailure || batchStatusLabel(item.final_status)}</div>
                          {technicalFailure ? <div>Detalle técnico: {technicalFailure}</div> : null}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </>
            )}
            {batch.batchJob?.status === 'completed' && projectId && (
              <div style={{ display: 'flex', gap: 10, marginTop: 14 }}>
                <Link
                  to={`/projects/${projectId}/library`}
                  className="rc-btn rc-btn--primary rc-btn--sm"
                  style={{ textDecoration: 'none', flex: 1, textAlign: 'center' }}
                  onClick={() => batch.setBatchModalOpen(false)}
                >
                  📚 Ir a Library
                </Link>
                <Link
                  to={`/projects/${projectId}/reader`}
                  className="rc-btn rc-btn--sm"
                  style={{ textDecoration: 'none', flex: 1, textAlign: 'center' }}
                  onClick={() => batch.setBatchModalOpen(false)}
                >
                  📖 Ir a Reader
                </Link>
              </div>
            )}
            <div style={{ marginTop: 10 }}>
              <button className="rc-btn rc-btn--ghost rc-btn--sm" onClick={batch.cancelBatch}>Cancel job</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
