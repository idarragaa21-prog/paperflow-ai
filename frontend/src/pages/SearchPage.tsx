import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';
import { useSearch } from '../hooks/useSearch';
import { useSearchFilters } from '../hooks/useSearchFilters';
import { useSearchHistory } from '../hooks/useSearchHistory';
import { useBatchDownload } from '../hooks/useBatchDownload';
import { SearchResultCard } from '../components/search/SearchResultCard';
import { getTechnicalDownloadFailure, humanizeDownloadFailure } from '../components/search/downloadMessaging';
import { Skeleton, SkeletonLines } from '../ui/Skeleton/Skeleton';
import type { BatchDownloadTraceItem } from '../types/api';
import { InsightCard, PageHero } from '../components/WorkflowPrimitives';

const SEARCH_PAGE_SIZE = 10;

const SOURCE_LABELS: Record<string, string> = {
  pubmed: 'PubMed',
  europepmc: 'Europe PMC',
  doaj: 'DOAJ',
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
  const search = useSearch(projectId);
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

  const { data: projectDashboard } = useQuery<{ counts: { papers: number; notes: number; references: number; meta_studies_current: number } }>({
    queryKey: ['project-dashboard-search', projectId],
    queryFn: async () => {
      const r = await api.get(`/projects/${projectId}/dashboard`);
      return r.data as { counts: { papers: number; notes: number; references: number; meta_studies_current: number } };
    },
    enabled: !!projectId,
    staleTime: 60_000,
  });

  const pageResults = (search.data?.results || []).slice(
    search.searchPage * SEARCH_PAGE_SIZE,
    (search.searchPage + 1) * SEARCH_PAGE_SIZE,
  );
  const totalPages = Math.ceil(((search.data?.results.length) || 1) / SEARCH_PAGE_SIZE);
  const activeFilterChips = [
    filters.yearFrom ? `From ${filters.yearFrom}` : null,
    filters.yearTo ? `To ${filters.yearTo}` : null,
    filters.journalFilter ? `Journal: ${filters.journalFilter}` : null,
    filters.sourceFilter ? `Source: ${filters.sourceFilter}` : null,
    filters.oaOnly ? 'Open access only' : null,
  ].filter(Boolean) as string[];
  const shortlistPreview = search.selectedPapers.slice(0, 5);

  function handleSearch() {
    search.runSearch(filters.buildPayload(), history.loadHistory);
  }

  return (
    <div className="rc-page-enter" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <PageHero
        eyebrow="Stage 1 · Research"
        title="Research Search"
        subtitle={`Federated literature search across PubMed, Europe PMC and DOAJ.${projectId && project ? ` Results can be downloaded directly to ${project.title}.` : ''}`}
        metrics={[
          { label: 'selected papers', value: search.selectedCount, tone: 'primary' },
          { label: 'saved in library', value: projectDashboard?.counts?.papers ?? 0, tone: 'success' },
          { label: 'notes captured', value: projectDashboard?.counts?.notes ?? 0, tone: 'neutral' },
        ]}
        actions={(
          <>
            <button className="rc-btn" data-testid="search-filters-toggle" onClick={filters.toggleFilters}>
              {filters.showFilters ? 'Hide filters' : 'Show filters'}
            </button>
            {projectId ? (
              <Link className="rc-btn" style={{ textDecoration: 'none' }} to={`/projects/${projectId}/library`}>
                Go to Library
              </Link>
            ) : null}
          </>
        )}
      />

      <div className="rc-composer-shell">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div className="rc-card">
            <div className="rc-card-title">Build your query</div>
            <div className="rc-row" style={{ alignItems: 'flex-end' }}>
              <div style={{ flex: 1, minWidth: 260 }}>
                <div className="rc-kicker">Research question</div>
                <input
                  className="rc-input"
                  data-testid="search-query-input"
                  value={search.query}
                  onChange={(e) => search.setQuery(e.target.value)}
                  placeholder="e.g. ACL reconstruction hamstring vs BPTB meta-analysis"
                  onKeyDown={(e) => { if (e.key === 'Enter' && search.canSearch && !search.loading) handleSearch(); }}
                />
              </div>
              <div style={{ width: 110 }}>
                <div className="rc-kicker">Max results</div>
                <input className="rc-input" type="number" value={search.maxResults} min={1} max={100} onChange={(e) => search.setMaxResults(Number(e.target.value))} />
              </div>
              <button className="rc-btn rc-btn--primary" data-testid="search-submit-button" disabled={!search.canSearch || search.loading} onClick={handleSearch}>
                {search.loading ? 'Searching…' : 'Search'}
              </button>
            </div>

            {filters.showFilters && (
              <div style={{ marginTop: 12, display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'flex-end' }}>
                <div style={{ width: 100 }}><div className="rc-kicker">Year from</div><input className="rc-input" data-testid="search-year-from-input" type="number" value={filters.yearFrom} min={1900} max={2030} placeholder="2018" onChange={(e) => filters.setYearFrom(e.target.value)} /></div>
                <div style={{ width: 100 }}><div className="rc-kicker">Year to</div><input className="rc-input" data-testid="search-year-to-input" type="number" value={filters.yearTo} min={1900} max={2030} placeholder="2025" onChange={(e) => filters.setYearTo(e.target.value)} /></div>
                <div style={{ width: 180 }}><div className="rc-kicker">Journal</div><input className="rc-input" value={filters.journalFilter} placeholder="e.g. Lancet" onChange={(e) => filters.setJournalFilter(e.target.value)} /></div>
                <div style={{ width: 140 }}>
                  <div className="rc-kicker">Source</div>
                  <select className="rc-input" value={filters.sourceFilter} onChange={(e) => filters.setSourceFilter(e.target.value)} style={{ height: 36 }}>
                    <option value="">All sources</option>
                    <option value="pubmed">PubMed</option>
                    <option value="europepmc">Europe PMC</option>
                    <option value="doaj">DOAJ</option>
                  </select>
                </div>
                <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, cursor: 'pointer', paddingBottom: 4 }}>
                  <input type="checkbox" checked={filters.oaOnly} onChange={(e) => filters.setOaOnly(e.target.checked)} /> Open Access only
                </label>
              </div>
            )}

            <div className="rc-help" style={{ marginTop: 8 }}>Tip: use phrases, outcomes, populations and study types. Results ranked by relevance.</div>
            {activeFilterChips.length > 0 && (
              <div className="rc-filter-chips" style={{ marginTop: 12 }}>
                {activeFilterChips.map((chip) => (
                  <span key={chip} className="rc-filter-chip">{chip}</span>
                ))}
              </div>
            )}
          </div>

          {search.error ? <div className="rc-error">{String(search.error)}</div> : null}

          {search.data ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
                <div className="rc-help">
                  <b>{search.data.count}</b> result{search.data.count !== 1 ? 's' : ''}
                  {search.data.cached && <span> (cached)</span>}
                  {search.data.sources && search.data.sources.length > 0 && (
                    <span> · from {search.data.sources.join(', ')}</span>
                  )}
                </div>
                {search.data.query_translation && (
                  <div className="rc-help" style={{ fontStyle: 'italic' }}>Translated: "{search.data.query_translation}"</div>
                )}
              </div>

              {search.data.warnings && search.data.warnings.length > 0 && (
                <div
                  className="rc-card"
                  data-testid="search-warning-banner"
                  style={{
                    borderColor: 'rgba(245,158,11,0.3)',
                    background: 'rgba(245,158,11,0.08)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 4,
                  }}
                >
                  <div style={{ fontWeight: 800, fontSize: 13 }}>Partial search warnings</div>
                  {search.data.warnings.map((warning, index) => (
                    <div key={`${warning}-${index}`} className="rc-help" style={{ color: 'var(--rc-text)' }}>
                      {warning}
                    </div>
                  ))}
                </div>
              )}

              {search.loading && (
                <div className="rc-card">
                  <Skeleton height={14} width="40%" />
                  <div style={{ height: 10 }} />
                  <SkeletonLines lines={6} lineHeight={12} lastLineWidth="60%" />
                </div>
              )}

              <div className="rc-card" style={{ padding: 10 }}>
                <div className="rc-row">
                  <button className="rc-btn rc-btn--sm" onClick={search.selectAllOA} disabled={!search.data.results.length}>Select all OA</button>
                  <button className="rc-btn rc-btn--sm" onClick={search.clearSelection} disabled={search.selectedCount === 0}>Clear ({search.selectedCount})</button>
                  {projectId ? (
                    <button
                      className="rc-btn rc-btn--primary rc-btn--sm"
                      data-testid="batch-download-button"
                      disabled={search.selectedCount === 0}
                      onClick={() => batch.startBatchDownload(projectId, search.selectedPapers, search.setError)}
                    >
                      Add {search.selectedCount > 0 ? `(${search.selectedCount})` : ''} to Library
                    </button>
                  ) : (
                    <span className="rc-help">Open from a project to save papers directly.</span>
                  )}
                  {batch.batchJobId && (
                    <button className="rc-btn rc-btn--sm" onClick={() => batch.setBatchModalOpen(true)}>View download job</button>
                  )}
                </div>
              </div>

              {pageResults.map((r, i) => (
                <SearchResultCard key={r.doi || r.pmid || String(search.searchPage * SEARCH_PAGE_SIZE + i)} r={r} idx={search.searchPage * SEARCH_PAGE_SIZE + i} search={search} />
              ))}

              {totalPages > 1 && (
                <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 12, padding: '10px 0' }}>
                  <button className="rc-btn rc-btn--sm" disabled={search.searchPage === 0} onClick={() => search.setSearchPage(Math.max(0, search.searchPage - 1))}>← Prev</button>
                  <span style={{ fontSize: 13, color: 'var(--rc-muted)' }}>Page {search.searchPage + 1} of {totalPages}</span>
                  <button className="rc-btn rc-btn--sm" disabled={search.searchPage >= totalPages - 1} onClick={() => search.setSearchPage(Math.min(totalPages - 1, search.searchPage + 1))}>Next →</button>
                </div>
              )}
            </div>
          ) : !search.loading ? (
            <div style={{ textAlign: 'center', padding: '48px 24px' }}>
              <svg width="64" height="64" viewBox="0 0 64 64" fill="none" style={{ margin: '0 auto 16px', display: 'block' }}>
                <circle cx="28" cy="28" r="20" fill="rgba(99,102,241,0.07)" stroke="rgba(99,102,241,0.2)" strokeWidth="1.5"/>
                <line x1="43" y1="43" x2="56" y2="56" stroke="rgba(99,102,241,0.35)" strokeWidth="2.5" strokeLinecap="round"/>
              </svg>
              <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 6 }}>Search across PubMed, Europe PMC and DOAJ</div>
              <div style={{ fontSize: 13, color: 'var(--rc-muted)', maxWidth: 400, margin: '0 auto' }}>
                Enter a query above to find relevant papers. Results are ranked by relevance and can be downloaded as PDFs.
              </div>
            </div>
          ) : null}
        </div>

        <div className="rc-workspace-rail">
          <InsightCard
            eyebrow="Selection rail"
            title={search.selectedCount > 0 ? `${search.selectedCount} paper(s) selected` : 'No papers selected yet'}
            body={search.selectedCount > 0
              ? 'Your shortlist is ready to move into the project library. From there you can process, read and extract.'
              : 'Use the checkboxes on the results list to create a focused shortlist before adding papers to the project library.'}
            tone={search.selectedCount > 0 ? 'primary' : 'neutral'}
            action={projectId ? (
              <div className="rc-row" style={{ gap: 6 }}>
                <button
                  className="rc-btn rc-btn--primary rc-btn--sm"
                  disabled={search.selectedCount === 0}
                  onClick={() => batch.startBatchDownload(projectId, search.selectedPapers, search.setError)}
                >
                  Add to Library
                </button>
                <Link className="rc-btn rc-btn--sm" style={{ textDecoration: 'none' }} to={`/projects/${projectId}/library`}>
                  Open Library
                </Link>
              </div>
            ) : undefined}
          />

          {shortlistPreview.length > 0 && (
            <div className="rc-card">
              <div className="rc-card-title" style={{ marginBottom: 8 }}>Shortlist preview</div>
              <div className="rc-shortlist-list">
                {shortlistPreview.map((paper, index) => (
                  <div key={`${paper.doi || paper.pmid || paper.title}-${index}`} className="rc-shortlist-item">
                    <div className="rc-shortlist-item__title">{paper.title}</div>
                    <div className="rc-shortlist-item__meta">{paper.doi || paper.pmid || 'Open-access candidate'}</div>
                  </div>
                ))}
                {search.selectedCount > shortlistPreview.length ? (
                  <div className="rc-help">+ {search.selectedCount - shortlistPreview.length} more selected</div>
                ) : null}
              </div>
            </div>
          )}

          {project ? (
            <InsightCard
              eyebrow="Project context"
              title={project.title}
              body={project.clinical_area
                ? `${project.clinical_area}. Search should feed a tighter paper set into the working library, not become a dead-end list.`
                : 'Search should feed a tighter paper set into the working library, not become a dead-end list.'}
              tone="success"
            />
          ) : null}

          {history.searchHistory.length > 0 && (
            <div className="rc-card" style={{ padding: history.showHistory ? 14 : 10 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }} onClick={() => history.setShowHistory(!history.showHistory)}>
                <div style={{ fontWeight: 700, fontSize: 13 }}>Recent searches</div>
                <span style={{ fontSize: 12, color: 'var(--rc-muted)' }}>{history.showHistory ? '▲ Hide' : '▼ Show'}</span>
              </div>
              {history.showHistory && (
                <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {history.historyLoading
                    ? <Skeleton height={12} width="50%" />
                    : history.searchHistory.slice(0, 6).map((h) => {
                        const dt = h.executed_at ? new Date(h.executed_at) : null;
                        const dateStr = dt ? dt.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : '—';
                        return (
                          <div key={h.id} style={{ display: 'flex', flexDirection: 'column', gap: 6, padding: '8px 10px', borderRadius: 10, background: 'var(--rc-surface-2)', fontSize: 13 }}>
                            <div style={{ fontWeight: 700 }}>{h.query}</div>
                            <div className="rc-help">{h.source} · {h.results_count ?? 0} results · {dateStr}</div>
                            <button className="rc-btn rc-btn--sm" onClick={() => history.reloadPastSearch(h.id, h.query)}>Reload</button>
                          </div>
                        );
                      })}
                </div>
              )}
            </div>
          )}

          {projectId ? (
            <InsightCard
              eyebrow="Next stage"
              title="Move the shortlist into Library"
              body="Search is discovery. The workflow only becomes real when you commit selected papers to the project library and process them."
              tone="success"
              action={<Link className="rc-btn rc-btn--sm" style={{ textDecoration: 'none' }} to={`/projects/${projectId}/library`}>Continue to Library</Link>}
            />
          ) : null}
        </div>
      </div>

      {batch.batchModalOpen && (
        <div data-testid="batch-trace-modal" style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.35)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20, zIndex: 50 }} onClick={() => batch.setBatchModalOpen(false)}>
          <div className="rc-card" style={{ width: 'min(520px, 96vw)' }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <div data-testid="batch-trace-title" style={{ fontWeight: 800, fontFamily: 'var(--font-display)' }}>Batch OA Download</div>
              <button className="rc-btn rc-btn--sm rc-btn--ghost" onClick={() => batch.setBatchModalOpen(false)}>✕</button>
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
              <Link
                to={`/projects/${projectId}/library`}
                className="rc-btn rc-btn--primary rc-btn--sm"
                style={{ textDecoration: 'none' }}
                onClick={() => batch.setBatchModalOpen(false)}
              >
                View in Library →
              </Link>
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
