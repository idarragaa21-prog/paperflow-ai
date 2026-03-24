import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';
import { useSearch } from '../hooks/useSearch';
import { useSearchFilters } from '../hooks/useSearchFilters';
import { useSearchHistory } from '../hooks/useSearchHistory';
import { useBatchDownload } from '../hooks/useBatchDownload';
import { SearchResultCard } from '../components/search/SearchResultCard';
import { Skeleton, SkeletonLines } from '../ui/Skeleton/Skeleton';

const SEARCH_PAGE_SIZE = 10;

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

  // Load project info for context banner
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

  function handleSearch() {
    search.runSearch(filters.buildPayload(), history.loadHistory);
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div>
        <h1 className="rc-page-title">Research Search</h1>
        <div className="rc-subtitle">
          Federated literature search across PubMed, Europe PMC and DOAJ.
          {projectId && project && (
            <> Results can be downloaded directly to <Link to={`/projects/${projectId}/library`} style={{ color: 'var(--rc-primary)' }}>{project.title}</Link>.</>
          )}
        </div>
      </div>

      {/* Flow hint when in project context */}
      {projectId && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--rc-muted)' }}>
          <span style={{ padding: '3px 10px', borderRadius: 20, background: 'var(--rc-primary-weak)', color: 'var(--rc-primary)', fontWeight: 700, fontSize: 11 }}>1 Search</span>
          <span>→</span>
          <Link to={`/projects/${projectId}/library`} style={{ padding: '3px 10px', borderRadius: 20, background: 'var(--rc-surface-3)', color: 'var(--rc-text-secondary)', textDecoration: 'none', fontSize: 11, fontWeight: 600 }}>2 Library</Link>
          <span>→</span>
          <Link to={`/projects/${projectId}/reader`} style={{ padding: '3px 10px', borderRadius: 20, background: 'var(--rc-surface-3)', color: 'var(--rc-text-secondary)', textDecoration: 'none', fontSize: 11, fontWeight: 600 }}>3 Reader</Link>
          <span>→</span>
          <Link to={`/projects/${projectId}/meta`} style={{ padding: '3px 10px', borderRadius: 20, background: 'var(--rc-surface-3)', color: 'var(--rc-text-secondary)', textDecoration: 'none', fontSize: 11, fontWeight: 600 }}>4 Extract</Link>
        </div>
      )}

      {/* ── Query ── */}
      <div className="rc-card">
        <div className="rc-card-title">Query</div>
        <div className="rc-row" style={{ alignItems: 'flex-end' }}>
          <div style={{ flex: 1, minWidth: 260 }}>
            <div className="rc-kicker">Research query</div>
            <input
              className="rc-input"
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
          <button className="rc-btn" onClick={filters.toggleFilters}>{filters.showFilters ? 'Hide Filters' : 'Filters'}</button>
          <button className="rc-btn rc-btn--primary" disabled={!search.canSearch || search.loading} onClick={handleSearch}>
            {search.loading ? 'Searching…' : 'Search'}
          </button>
        </div>

        {filters.showFilters && (
          <div style={{ marginTop: 12, display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'flex-end' }}>
            <div style={{ width: 100 }}><div className="rc-kicker">Year from</div><input className="rc-input" type="number" value={filters.yearFrom} min={1900} max={2030} placeholder="2018" onChange={(e) => filters.setYearFrom(e.target.value)} /></div>
            <div style={{ width: 100 }}><div className="rc-kicker">Year to</div><input className="rc-input" type="number" value={filters.yearTo} min={1900} max={2030} placeholder="2025" onChange={(e) => filters.setYearTo(e.target.value)} /></div>
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
      </div>

      {search.error && <div className="rc-error">{String(search.error)}</div>}

      {/* ── History ── */}
      {history.searchHistory.length > 0 && (
        <div className="rc-card" style={{ padding: history.showHistory ? 14 : 10 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }} onClick={() => history.setShowHistory(!history.showHistory)}>
            <div style={{ fontWeight: 700, fontSize: 13 }}>Search History ({history.searchHistory.length})</div>
            <span style={{ fontSize: 12, color: 'var(--rc-muted)' }}>{history.showHistory ? '▲ Hide' : '▼ Show'}</span>
          </div>
          {history.showHistory && (
            <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 6 }}>
              {history.historyLoading
                ? <Skeleton height={12} width="50%" />
                : history.searchHistory.slice(0, 20).map((h) => {
                    const dt = h.executed_at ? new Date(h.executed_at) : null;
                    const dateStr = dt
                      ? dt.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }) + ' ' + dt.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
                      : '—';
                    return (
                      <div key={h.id} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '6px 8px', borderRadius: 6, background: 'var(--rc-surface-2)', fontSize: 13 }}>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <span style={{ fontWeight: 700 }}>{h.query}</span>
                          <span className="rc-help" style={{ marginLeft: 8 }}>{h.source} · {h.results_count ?? 0} results · {dateStr}</span>
                        </div>
                        <button className="rc-btn rc-btn--sm" onClick={(e) => { e.stopPropagation(); history.reloadPastSearch(h.id, h.query); }}>Reload</button>
                      </div>
                    );
                  })}
            </div>
          )}
        </div>
      )}

      {/* ── Results ── */}
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

      {/* ── Batch modal ── */}
      {batch.batchModalOpen && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.35)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20, zIndex: 50 }} onClick={() => batch.setBatchModalOpen(false)}>
          <div className="rc-card" style={{ width: 'min(520px, 96vw)' }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <div style={{ fontWeight: 800, fontFamily: 'var(--font-display)' }}>Batch OA Download</div>
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
            {batch.batchJob?.error && (
              <div style={{ marginBottom: 8 }}>
                <div className="rc-error">{String(batch.batchJob.error)}</div>
                <button className="rc-btn rc-btn--sm" style={{ marginTop: 8 }} onClick={() => batch.setBatchModalOpen(false)}>Close</button>
              </div>
            )}
            {batch.batchJob?.output && (
              <div className="rc-row" style={{ gap: 8, marginBottom: 12 }}>
                <span className="rc-badge rc-badge--success">Downloaded: <b>{(batch.batchJob.output as { downloaded?: unknown[] })?.downloaded?.length ?? 0}</b></span>
                <span className="rc-badge">Already exists: <b>{(batch.batchJob.output as { already_exists?: unknown[] })?.already_exists?.length ?? 0}</b></span>
                <span className="rc-badge rc-badge--danger">Failed: <b>{(batch.batchJob.output as { failed?: unknown[] })?.failed?.length ?? 0}</b></span>
              </div>
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
