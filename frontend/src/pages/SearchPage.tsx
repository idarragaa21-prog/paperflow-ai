import { useParams } from 'react-router-dom';
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
        <div className="rc-subtitle">Federated literature search across PubMed, Europe PMC and DOAJ with OA-aware saving.</div>
      </div>

      {/* ── Query ── */}
      <div className="rc-card">
        <div className="rc-card-title">Query</div>
        <div className="rc-row" style={{ alignItems: 'flex-end' }}>
          <div style={{ flex: 1, minWidth: 260 }}>
            <div className="rc-kicker">Research query</div>
            <input className="rc-input" value={search.query} onChange={(e) => search.setQuery(e.target.value)}
              placeholder="e.g. ACL reconstruction hamstring vs BPTB meta-analysis"
              onKeyDown={(e) => { if (e.key === 'Enter' && search.canSearch && !search.loading) handleSearch(); }} />
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
            <div style={{ width: 100 }}><div className="rc-kicker">Year from</div><input className="rc-input" type="number" value={filters.yearFrom} min={1900} max={2026} placeholder="e.g. 2018" onChange={(e) => filters.setYearFrom(e.target.value)} /></div>
            <div style={{ width: 100 }}><div className="rc-kicker">Year to</div><input className="rc-input" type="number" value={filters.yearTo} min={1900} max={2026} placeholder="e.g. 2025" onChange={(e) => filters.setYearTo(e.target.value)} /></div>
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
            <div style={{ fontWeight: 800, fontSize: 13 }}>Search History ({history.searchHistory.length})</div>
            <span style={{ fontSize: 12, color: 'var(--rc-muted)' }}>{history.showHistory ? '▲ Hide' : '▼ Show'}</span>
          </div>
          {history.showHistory && (
            <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 6 }}>
              {history.historyLoading ? <Skeleton height={12} width="50%" /> : history.searchHistory.slice(0, 20).map((h) => {
                const dt = h.executed_at ? new Date(h.executed_at) : null;
                const dateStr = dt ? dt.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }) + ' ' + dt.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' }) : '—';
                return (
                  <div key={h.id} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '6px 8px', borderRadius: 6, background: 'var(--rc-bg-secondary, rgba(0,0,0,0.03))', fontSize: 13 }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <span style={{ fontWeight: 700 }}>{h.query}</span>
                      <span className="rc-help" style={{ marginLeft: 8 }}>{h.source} · {h.results_count ?? 0} results · {dateStr}</span>
                    </div>
                    <button className="rc-btn" style={{ padding: '2px 10px', fontSize: 12 }} onClick={(e) => { e.stopPropagation(); history.reloadPastSearch(h.id, h.query); }}>Reload</button>
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
          <div className="rc-help">Results: <b>{search.data.count}</b>{search.data.cached ? ' (cached)' : ''}</div>
          {search.loading && <div className="rc-card"><Skeleton height={14} width="40%" /><div style={{ height: 10 }} /><SkeletonLines lines={6} lineHeight={12} lastLineWidth="60%" /></div>}

          <div className="rc-card" style={{ padding: 10 }}>
            <div className="rc-row">
              <button className="rc-btn" onClick={search.selectAllOA} disabled={!search.data.results.length}>Select all OA</button>
              <button className="rc-btn" onClick={search.clearSelection} disabled={search.selectedCount === 0}>Clear ({search.selectedCount})</button>
              <button className="rc-btn rc-btn--primary" disabled={search.selectedCount === 0}
                onClick={() => projectId && batch.startBatchDownload(projectId, search.selectedPapers, search.setError)}>
                Download Selected ({search.selectedCount})
              </button>
              {batch.batchJobId && <button className="rc-btn" onClick={() => batch.setBatchModalOpen(true)}>View batch job</button>}
            </div>
          </div>

          {pageResults.map((r, i) => (
            <SearchResultCard key={r.doi || r.pmid || String(search.searchPage * SEARCH_PAGE_SIZE + i)} r={r} idx={search.searchPage * SEARCH_PAGE_SIZE + i} search={search} />
          ))}

          {totalPages > 1 && (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 12, padding: '10px 0' }}>
              <button className="rc-btn" disabled={search.searchPage === 0} onClick={() => search.setSearchPage(Math.max(0, search.searchPage - 1))}>← Prev</button>
              <span style={{ fontSize: 13, color: 'var(--rc-muted)' }}>Page {search.searchPage + 1} of {totalPages} ({search.data.results.length} results)</span>
              <button className="rc-btn" disabled={search.searchPage >= totalPages - 1} onClick={() => search.setSearchPage(Math.min(totalPages - 1, search.searchPage + 1))}>Next →</button>
            </div>
          )}
        </div>
      ) : (
        <div style={{ textAlign: 'center', padding: '48px 24px' }}>
          <svg width="72" height="72" viewBox="0 0 72 72" fill="none" style={{ margin: '0 auto 14px', display: 'block' }}>
            <circle cx="32" cy="32" r="22" fill="rgba(99,102,241,0.07)" stroke="rgba(99,102,241,0.2)" strokeWidth="1.5"/>
            <line x1="49" y1="49" x2="62" y2="62" stroke="rgba(99,102,241,0.4)" strokeWidth="2.5" strokeLinecap="round"/>
          </svg>
          <div style={{ fontWeight: 700, fontSize: 15 }}>Federated Research Search</div>
          <div style={{ fontSize: 13, color: 'var(--rc-muted)', marginTop: 5 }}>Search across PubMed, Europe PMC and DOAJ. Results ranked by relevance.</div>
        </div>
      )}

      {/* ── Batch modal ── */}
      {batch.batchModalOpen && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.35)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20, zIndex: 50 }} onClick={() => batch.setBatchModalOpen(false)}>
          <div className="rc-card" style={{ width: 'min(900px, 96vw)', maxHeight: '88vh', overflow: 'auto' }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ fontWeight: 900 }}>Batch OA download</div>
              <button className="rc-btn" onClick={() => batch.setBatchModalOpen(false)}>Close</button>
            </div>
            <div style={{ height: 10 }} />
            <div className="rc-help">Job: <span style={{ fontFamily: 'monospace' }}>{batch.batchJobId}</span></div>
            <div className="rc-help">Status: <b>{batch.batchJob?.status || '—'}</b> · Progress: <b>{batch.batchJob?.progress ?? 0}%</b></div>
            {batch.batchJob?.error && <div className="rc-error" style={{ marginTop: 8 }}>{String(batch.batchJob.error)}</div>}
            <div className="rc-row" style={{ marginTop: 10 }}><button className="rc-btn rc-btn--ghost" onClick={batch.cancelBatch}>Cancel job</button></div>
            {batch.batchJob?.output && (() => {
              const out = batch.batchJob.output as { downloaded?: any[]; already_exists?: any[]; not_available?: any[]; failed?: any[] };
              const downloaded = out.downloaded ?? [];
              const alreadyExists = out.already_exists ?? [];
              const notAvailable = out.not_available ?? [];
              const failed = out.failed ?? [];
              const allPapers = [...downloaded, ...alreadyExists, ...notAvailable, ...failed];
              return (
                <div style={{ marginTop: 14 }}>
                  <div className="rc-row" style={{ gap: 8, marginBottom: 14 }}>
                    <span className="rc-badge rc-badge--success">Downloaded: <b>{downloaded.length}</b></span>
                    <span className="rc-badge">Already exists: <b>{alreadyExists.length}</b></span>
                    <span className="rc-badge rc-badge--info">Unavailable: <b>{notAvailable.length}</b></span>
                    <span className="rc-badge rc-badge--danger">Failed: <b>{failed.length}</b></span>
                  </div>
                  {allPapers.length > 0 && (
                    <div style={{ overflowX: 'auto' }}>
                      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                        <thead>
                          <tr style={{ background: 'var(--rc-bg-secondary, rgba(0,0,0,0.04))', textAlign: 'left' }}>
                            <th style={{ padding: '6px 8px', fontWeight: 700 }}>Title</th>
                            <th style={{ padding: '6px 8px', fontWeight: 700 }}>Status</th>
                            <th style={{ padding: '6px 8px', fontWeight: 700 }}>Source</th>
                            <th style={{ padding: '6px 8px', fontWeight: 700 }}>Fallback</th>
                            <th style={{ padding: '6px 8px', fontWeight: 700 }}>Reason / URL</th>
                          </tr>
                        </thead>
                        <tbody>
                          {allPapers.map((p: any, i: number) => {
                            const statusClass = p.final_status === 'downloaded' ? 'rc-badge--success'
                              : p.final_status === 'existing' ? ''
                              : p.final_status === 'unavailable' ? 'rc-badge--info'
                              : 'rc-badge--danger';
                            return (
                              <tr key={p.paper_id ?? `row-${i}`} style={{ borderBottom: '1px solid var(--rc-border, rgba(0,0,0,0.08))' }}>
                                <td style={{ padding: '6px 8px', maxWidth: 260, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={p.title ?? undefined}>{p.title || <span className="rc-muted">—</span>}</td>
                                <td style={{ padding: '6px 8px' }}><span className={`rc-badge ${statusClass}`} style={{ fontSize: 11 }}>{p.final_status}</span></td>
                                <td style={{ padding: '6px 8px', color: 'var(--rc-muted)' }}>{p.source_provider || '—'}</td>
                                <td style={{ padding: '6px 8px', textAlign: 'center' }}>{p.used_fallback ? '✓' : ''}</td>
                                <td style={{ padding: '6px 8px', maxWidth: 280, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                  {p.reason ? <span style={{ color: 'var(--rc-danger, #dc2626)' }}>{p.reason}</span>
                                    : p.resolved_url ? <a href={p.resolved_url} target="_blank" rel="noreferrer" style={{ color: 'var(--rc-link, #4f46e5)', fontSize: 11 }}>{p.resolved_url}</a>
                                    : <span className="rc-muted">—</span>}
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              );
            })()}
          </div>
        </div>
      )}
    </div>
  );
}
