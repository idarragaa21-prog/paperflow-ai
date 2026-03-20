import { useCallback, useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../services/api';
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
  source?: string | null;
  is_open_access?: boolean;
  oa_url?: string | null;
  relevance_score?: number | null;
};

type SearchResponse = {
  count: number;
  results: PaperMetadata[];
  query_translation?: string | null;
  cached: boolean;
  sources?: string[];
};

type SearchRecord = {
  id: string;
  project_id: string;
  query: string;
  source: string;
  results_count: number | null;
  executed_at: string | null;
};

const SOURCE_LABELS: Record<string, string> = {
  pubmed: 'PubMed',
  europepmc: 'Europe PMC',
  doaj: 'DOAJ',
};

const SOURCE_COLORS: Record<string, string> = {
  pubmed: '#2563eb',
  europepmc: '#059669',
  doaj: '#d97706',
};

export default function SearchPage() {
  const { projectId } = useParams();
  const toast = useToast();

  const [query, setQuery] = useState('');
  const [maxResults, setMaxResults] = useState<number>(20);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<SearchResponse | null>(null);
  const [downloadingKey, setDownloadingKey] = useState<string | null>(null);

  // Per-result download traceability
  type DownloadInfo = {
    status: 'saved' | 'duplicate' | 'error';
    source_provider?: string | null;
    oa_url?: string | null;
    error?: string | null;
  };
  const [downloadResults, setDownloadResults] = useState<Record<string, DownloadInfo>>({});

  // Pagination
  const SEARCH_PAGE_SIZE = 10;
  const [searchPage, setSearchPage] = useState(0);

  // Expandable abstracts
  const [expandedAbstracts, setExpandedAbstracts] = useState<Record<string, boolean>>({});

  // Filters
  const [yearFrom, setYearFrom] = useState<string>('');
  const [yearTo, setYearTo] = useState<string>('');
  const [oaOnly, setOaOnly] = useState(false);
  const [journalFilter, setJournalFilter] = useState('');
  const [sourceFilter, setSourceFilter] = useState('');
  const [showFilters, setShowFilters] = useState(false);

  const [selected, setSelected] = useState<Record<string, boolean>>({});
  const [batchJobId, setBatchJobId] = useState<string | null>(null);
  const [batchJob, setBatchJob] = useState<{ status: string; progress: number; error?: string | null; output?: any } | null>(null);
  const [batchModalOpen, setBatchModalOpen] = useState(false);

  // Search history
  const [searchHistory, setSearchHistory] = useState<SearchRecord[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);

  const loadHistory = useCallback(async () => {
    if (!projectId) return;
    setHistoryLoading(true);
    try {
      const r = await api.get(`/search/projects/${projectId}/searches`);
      setSearchHistory(r.data as SearchRecord[]);
    } catch {
      // non-blocking
    } finally {
      setHistoryLoading(false);
    }
  }, [projectId]);

  // Load history on mount and after each search
  useEffect(() => { loadHistory(); }, [loadHistory]);

  async function reloadPastSearch(searchId: string, pastQuery: string) {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    try {
      const r = await api.get(`/search/${searchId}/results`);
      const results = r.data as PaperMetadata[];
      setData({
        count: results.length,
        results,
        query_translation: null,
        cached: false,
        sources: [],
      });
      setQuery(pastQuery);
      setSelected({});
      setSearchPage(0);
      setBatchJobId(null);
      setBatchJob(null);
      setBatchModalOpen(false);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to load search results');
    } finally {
      setLoading(false);
    }
  }

  const canSearch = useMemo(() => Boolean(projectId && query.trim().length >= 3), [projectId, query]);

  function buildFilters() {
    const f: Record<string, any> = {};
    const yf = parseInt(yearFrom, 10);
    const yt = parseInt(yearTo, 10);
    if (!isNaN(yf) && yf > 1900) f.year_from = yf;
    if (!isNaN(yt) && yt > 1900) f.year_to = yt;
    if (oaOnly) f.open_access_only = true;
    if (journalFilter.trim()) f.journal = journalFilter.trim();
    if (sourceFilter) f.source = sourceFilter;
    return Object.keys(f).length > 0 ? f : undefined;
  }

  async function runSearch() {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    try {
      const payload: any = {
        project_id: projectId,
        query: query.trim(),
        max_results: maxResults,
      };
      const filters = buildFilters();
      if (filters) payload.filters = filters;

      const r = await api.post('/search/federated', payload);
      setData(r.data as SearchResponse);
      setSelected({});
      setSearchPage(0);
      setBatchJobId(null);
      setBatchJob(null);
      setBatchModalOpen(false);
      loadHistory(); // refresh history panel
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Search failed');
    } finally {
      setLoading(false);
    }
  }

  async function downloadOA(r: PaperMetadata) {
    if (!projectId) return;
    const key = r.doi || r.pmid || r.title;
    setDownloadingKey(key);
    setError(null);
    try {
      const payload: any = {
        project_id: projectId,
        title: r.title,
      };
      if (r.doi) payload.doi = r.doi;
      if (r.pmid) payload.pmid = r.pmid;
      if (r.oa_url) payload.oa_url = r.oa_url;

      const resp = await api.post('/papers/download', payload);
      const duplicate = Boolean(resp.data?.duplicate);
      const srcProvider = resp.data?.source_provider || null;
      const usedUrl = resp.data?.oa_url || null;

      setDownloadResults((prev) => ({
        ...prev,
        [key]: {
          status: duplicate ? 'duplicate' : 'saved',
          source_provider: srcProvider,
          oa_url: usedUrl,
        },
      }));

      const providerLabel = srcProvider
        ? srcProvider === 'user_provided_oa' ? 'direct OA link'
        : srcProvider === 'unpaywall' ? 'Unpaywall'
        : srcProvider === 'europepmc' ? 'Europe PMC'
        : srcProvider
        : null;

      if (duplicate) {
        toast.info('Duplicate', 'Paper already exists in this project.');
      } else {
        toast.info(
          'Downloaded',
          providerLabel
            ? `Saved via ${providerLabel}${usedUrl ? ` — ${usedUrl.slice(0, 60)}…` : ''}`
            : 'Downloaded and saved.',
        );
      }
    } catch (e: any) {
      const errMsg = e?.response?.data?.detail || 'Download failed';
      setDownloadResults((prev) => ({
        ...prev,
        [key]: { status: 'error', error: errMsg },
      }));
      setError(errMsg);
    } finally {
      setDownloadingKey(null);
    }
  }

  const selectedCount = useMemo(() => Object.values(selected).filter(Boolean).length, [selected]);

  const selectedPapers = useMemo(() => {
    if (!data) return [] as any[];
    return data.results
      .map((r, idx) => ({ r, idx }))
      .filter(({ r, idx }) => {
        const key = r.doi || r.pmid || String(idx);
        const canDownload = Boolean(r.is_open_access) && Boolean(r.doi || r.pmid || r.oa_url);
        return Boolean(selected[key]) && canDownload;
      })
      .map(({ r }) => ({
        pmid: r.pmid || undefined,
        pmcid: r.pmcid || undefined,
        doi: r.doi || undefined,
        title: r.title,
        oa_url: r.oa_url || undefined,
      }));
  }, [data, selected]);

  function toggleSelect(key: string, next?: boolean) {
    setSelected((prev) => ({ ...prev, [key]: next ?? !prev[key] }));
  }

  function selectAllOA() {
    if (!data) return;
    const next: Record<string, boolean> = {};
    data.results.forEach((r, idx) => {
      const key = r.doi || r.pmid || String(idx);
      const canDownload = Boolean(r.is_open_access) && Boolean(r.doi || r.pmid || r.oa_url);
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
      toast.info('No papers selected', 'Select at least one OA-eligible paper first.');
      return;
    }
    setError(null);
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
      setError(e?.response?.data?.detail || 'Batch download failed');
    }
  }

  async function cancelBatch() {
    if (!batchJobId) return;
    try {
      await api.post(`/jobs/${batchJobId}/cancel`);
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
        if (status === 'completed' || status === 'failed') return;
      } catch (e: any) {
        if (alive) setBatchJob((prev) => prev || { status: 'queued', progress: 0, error: e?.message || 'Poll failed' });
      }
      t = setTimeout(poll, 1000);
    }
    poll();
    return () => { alive = false; if (t) clearTimeout(t); };
  }, [batchJobId, batchModalOpen]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div>
        <h1 className="rc-page-title">Research Search</h1>
        <div className="rc-subtitle">Federated literature search across PubMed, Europe PMC and DOAJ with deduplication, relevance ranking and OA-aware saving.</div>
      </div>

      <div className="rc-card">
        <div className="rc-card-title">Query</div>
        <div className="rc-row" style={{ alignItems: 'flex-end' }}>
          <div style={{ flex: 1, minWidth: 260 }}>
            <div className="rc-kicker">Research query</div>
            <input className="rc-input" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="e.g. ACL reconstruction hamstring vs BPTB meta-analysis" onKeyDown={(e) => { if (e.key === 'Enter' && canSearch && !loading) runSearch(); }} />
          </div>
          <div style={{ width: 110 }}>
            <div className="rc-kicker">Max results</div>
            <input className="rc-input" type="number" value={maxResults} min={1} max={100} onChange={(e) => setMaxResults(Number(e.target.value))} />
          </div>
          <button className="rc-btn" onClick={() => setShowFilters((p) => !p)} style={{ whiteSpace: 'nowrap' }}>
            {showFilters ? 'Hide Filters' : 'Filters'}
          </button>
          <button className="rc-btn rc-btn--primary" disabled={!canSearch || loading} onClick={runSearch}>
            {loading ? 'Searching…' : 'Search'}
          </button>
        </div>

        {showFilters && (
          <div style={{ marginTop: 12, display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'flex-end' }}>
            <div style={{ width: 100 }}>
              <div className="rc-kicker">Year from</div>
              <input className="rc-input" type="number" value={yearFrom} min={1900} max={2026} placeholder="e.g. 2018" onChange={(e) => setYearFrom(e.target.value)} />
            </div>
            <div style={{ width: 100 }}>
              <div className="rc-kicker">Year to</div>
              <input className="rc-input" type="number" value={yearTo} min={1900} max={2026} placeholder="e.g. 2025" onChange={(e) => setYearTo(e.target.value)} />
            </div>
            <div style={{ width: 180 }}>
              <div className="rc-kicker">Journal</div>
              <input className="rc-input" value={journalFilter} placeholder="e.g. Lancet" onChange={(e) => setJournalFilter(e.target.value)} />
            </div>
            <div style={{ width: 140 }}>
              <div className="rc-kicker">Source</div>
              <select className="rc-input" value={sourceFilter} onChange={(e) => setSourceFilter(e.target.value)} style={{ height: 36 }}>
                <option value="">All sources</option>
                <option value="pubmed">PubMed</option>
                <option value="europepmc">Europe PMC</option>
                <option value="doaj">DOAJ</option>
              </select>
            </div>
            <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, cursor: 'pointer', paddingBottom: 4 }}>
              <input type="checkbox" checked={oaOnly} onChange={(e) => setOaOnly(e.target.checked)} />
              Open Access only
            </label>
          </div>
        )}
        <div className="rc-help" style={{ marginTop: 8 }}>Tip: use phrases, outcomes, populations and study types. Results are ranked by relevance, recency, metadata quality and OA availability.</div>
      </div>

      {error ? <div className="rc-error">{String(error)}</div> : null}

      {/* ── Search History Panel ── */}
      {searchHistory.length > 0 && (
        <div className="rc-card" style={{ padding: showHistory ? 14 : 10 }}>
          <div
            style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }}
            onClick={() => setShowHistory((p) => !p)}
          >
            <div style={{ fontWeight: 800, fontSize: 13 }}>
              Search History ({searchHistory.length})
            </div>
            <span style={{ fontSize: 12, color: 'var(--rc-muted)' }}>
              {showHistory ? '▲ Hide' : '▼ Show'}
            </span>
          </div>
          {showHistory && (
            <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 6 }}>
              {historyLoading ? (
                <Skeleton height={12} width="50%" />
              ) : (
                searchHistory.slice(0, 20).map((h) => {
                  const dt = h.executed_at ? new Date(h.executed_at) : null;
                  const dateStr = dt
                    ? dt.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }) +
                      ' ' +
                      dt.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
                    : '—';
                  return (
                    <div
                      key={h.id}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 10,
                        padding: '6px 8px',
                        borderRadius: 6,
                        background: 'var(--rc-bg-secondary, rgba(0,0,0,0.03))',
                        fontSize: 13,
                      }}
                    >
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <span style={{ fontWeight: 700 }}>{h.query}</span>
                        <span className="rc-help" style={{ marginLeft: 8 }}>
                          {h.source} · {h.results_count ?? 0} results · {dateStr}
                        </span>
                      </div>
                      <button
                        className="rc-btn"
                        style={{ padding: '2px 10px', fontSize: 12, flexShrink: 0 }}
                        onClick={(e) => {
                          e.stopPropagation();
                          reloadPastSearch(h.id, h.query);
                        }}
                      >
                        Reload
                      </button>
                    </div>
                  );
                })
              )}
            </div>
          )}
        </div>
      )}

      {data ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div className="rc-help">
            Results: <b>{data.count}</b> {data.cached ? '(cached)' : ''}
            {data.query_translation ? ` · Translation: ${data.query_translation}` : ''}
            {data.sources?.length ? ` · Sources: ${data.sources.join(', ')}` : ''}
          </div>

          {loading ? (
            <div className="rc-card">
              <Skeleton height={14} width="40%" />
              <div style={{ height: 10 }} />
              <SkeletonLines lines={6} lineHeight={12} lastLineWidth="60%" />
            </div>
          ) : null}

          <div className="rc-card" style={{ padding: 10 }}>
            <div className="rc-row">
              <button className="rc-btn" onClick={selectAllOA} disabled={!data.results.length}>Select all OA</button>
              <button className="rc-btn" onClick={clearSelection} disabled={selectedCount === 0}>Clear ({selectedCount})</button>
              <button className="rc-btn rc-btn--primary" onClick={startBatchDownload} disabled={selectedCount === 0}>Download Selected ({selectedCount})</button>
              {batchJobId ? (
                <button className="rc-btn" onClick={() => setBatchModalOpen(true)}>View batch job</button>
              ) : null}
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {(() => {
              const totalPages = Math.ceil((data.results.length || 1) / SEARCH_PAGE_SIZE);
              const start = searchPage * SEARCH_PAGE_SIZE;
              const pageResults = data.results.slice(start, start + SEARCH_PAGE_SIZE);

              return (<>
                {pageResults.map((r, localIdx) => {
                  const idx = start + localIdx;
                  const key = r.doi || r.pmid || String(idx);
                  const canDownload = Boolean(r.is_open_access) && Boolean(r.doi || r.pmid || r.oa_url);
                  const isSelected = Boolean(selected[key]);
                  const srcLabel = SOURCE_LABELS[r.source || ''] || r.source || '—';
                  const srcColor = SOURCE_COLORS[r.source || ''] || '#6b7280';
                  const isExpanded = Boolean(expandedAbstracts[key]);
                  return (
                    <div key={key} className="rc-card" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                      <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                        <input type="checkbox" disabled={!canDownload} checked={isSelected} onChange={() => toggleSelect(key)} title={canDownload ? 'Select for batch download' : 'Not eligible'} style={{ marginTop: 3 }} />
                        <div style={{ fontWeight: 850, flex: 1, lineHeight: 1.25 }}>{r.title}</div>
                        <div style={{ display: 'flex', gap: 4, flexShrink: 0 }}>
                          <span style={{ fontSize: 11, fontWeight: 700, padding: '2px 7px', borderRadius: 4, background: srcColor + '18', color: srcColor, border: `1px solid ${srcColor}40`, whiteSpace: 'nowrap' }}>
                            {srcLabel}
                          </span>
                          {r.is_open_access ? <span className="rc-badge rc-badge--success">OA</span> : <span className="rc-badge">Closed</span>}
                        </div>
                      </div>

                      <div className="rc-help">
                        {(r.journal || '—')}{r.pub_year ? ` · ${r.pub_year}` : ''}
                        {r.doi ? ` · DOI: ${r.doi}` : ''}
                        {r.pmid ? ` · PMID: ${r.pmid}` : ''}
                        {r.relevance_score != null ? ` · Score: ${(r.relevance_score * 100).toFixed(0)}%` : ''}
                      </div>

                      {r.abstract ? (
                        <div>
                          <div style={{
                            fontSize: 13,
                            whiteSpace: 'pre-wrap',
                            ...(isExpanded ? {} : {
                              maxHeight: 80,
                              overflow: 'hidden',
                              maskImage: 'linear-gradient(to bottom, black 60%, transparent 100%)',
                              WebkitMaskImage: 'linear-gradient(to bottom, black 60%, transparent 100%)',
                            }),
                          }}>
                            {r.abstract}
                          </div>
                          {r.abstract.length > 200 && (
                            <button
                              onClick={() => setExpandedAbstracts((p) => ({ ...p, [key]: !p[key] }))}
                              style={{ background: 'none', border: 'none', color: 'var(--rc-accent, #6366f1)', cursor: 'pointer', fontSize: 12, fontWeight: 600, padding: '2px 0', marginTop: 2 }}
                            >
                              {isExpanded ? 'Show less ▲' : 'Show more ▼'}
                            </button>
                          )}
                        </div>
                      ) : null}

                      <div className="rc-row" style={{ flexWrap: 'wrap', gap: 6 }}>
                        <button className="rc-btn" disabled={!canDownload || downloadingKey === (r.doi || r.pmid || r.title)} onClick={() => downloadOA(r)}>
                          {downloadingKey === (r.doi || r.pmid || r.title) ? 'Downloading…' : 'Download OA PDF'}
                        </button>
                        {r.oa_url ? (
                          <a href={r.oa_url} target="_blank" rel="noreferrer" style={{ fontSize: 12, wordBreak: 'break-all' }}>OA link ↗</a>
                        ) : null}
                        {!r.is_open_access ? <span className="rc-help">Not marked OA by provider metadata.</span> : null}
                        {r.is_open_access && !canDownload ? <span className="rc-help">OA, but missing DOI/PMID/URL to download PDF.</span> : null}
                      </div>

                  {/* Download traceability */}
                  {(() => {
                    const dlInfo = downloadResults[key];
                    if (!dlInfo) return null;
                    const providerLabel =
                      dlInfo.source_provider === 'user_provided_oa' ? 'Direct OA link (from search result)'
                      : dlInfo.source_provider === 'unpaywall' ? 'Unpaywall (resolved via DOI)'
                      : dlInfo.source_provider === 'europepmc' ? 'Europe PMC (resolved via PMID)'
                      : dlInfo.source_provider || null;

                    if (dlInfo.status === 'saved') return (
                      <div style={{ fontSize: 12, padding: '5px 8px', borderRadius: 5, background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.2)', display: 'flex', flexDirection: 'column', gap: 2 }}>
                        <span style={{ fontWeight: 700, color: '#059669' }}>✓ Downloaded</span>
                        {providerLabel && <span style={{ color: 'var(--rc-muted)' }}>Source: {providerLabel}</span>}
                        {dlInfo.oa_url && <span style={{ color: 'var(--rc-muted)', wordBreak: 'break-all' }}>URL: {dlInfo.oa_url}</span>}
                      </div>
                    );
                    if (dlInfo.status === 'duplicate') return (
                      <div style={{ fontSize: 12, padding: '5px 8px', borderRadius: 5, background: 'rgba(99,102,241,0.06)', border: '1px solid rgba(99,102,241,0.15)' }}>
                        <span style={{ fontWeight: 700, color: '#6366f1' }}>↻ Already in project</span>
                      </div>
                    );
                    if (dlInfo.status === 'error') return (
                      <div style={{ fontSize: 12, padding: '5px 8px', borderRadius: 5, background: 'rgba(239,68,68,0.06)', border: '1px solid rgba(239,68,68,0.15)' }}>
                        <span style={{ fontWeight: 700, color: '#ef4444' }}>✗ Failed</span>
                        {dlInfo.error && <span style={{ color: 'var(--rc-muted)', marginLeft: 6 }}>{dlInfo.error}</span>}
                      </div>
                    );
                    return null;
                  })()}
                </div>
              );
            })}

                {/* Pagination controls */}
                {totalPages > 1 && (
                  <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 12, padding: '10px 0' }}>
                    <button className="rc-btn" disabled={searchPage === 0} onClick={() => setSearchPage((p) => Math.max(0, p - 1))} style={{ padding: '4px 12px', fontSize: 12 }}>
                      ← Prev
                    </button>
                    <span style={{ fontSize: 13, color: 'var(--rc-muted)' }}>
                      Page {searchPage + 1} of {totalPages} ({data.results.length} results)
                    </span>
                    <button className="rc-btn" disabled={searchPage >= totalPages - 1} onClick={() => setSearchPage((p) => Math.min(totalPages - 1, p + 1))} style={{ padding: '4px 12px', fontSize: 12 }}>
                      Next →
                    </button>
                  </div>
                )}
              </>);
            })()}
          </div>
        </div>
      ) : (
        <div style={{ textAlign: 'center', padding: '48px 24px' }}>
          <svg width="72" height="72" viewBox="0 0 72 72" fill="none" style={{ margin: '0 auto 14px', display: 'block' }}>
            <circle cx="32" cy="32" r="22" fill="rgba(99,102,241,0.07)" stroke="rgba(99,102,241,0.2)" strokeWidth="1.5"/>
            <circle cx="32" cy="32" r="14" fill="rgba(99,102,241,0.05)" stroke="rgba(99,102,241,0.15)" strokeWidth="1.5"/>
            <line x1="24" y1="32" x2="40" y2="32" stroke="rgba(99,102,241,0.3)" strokeWidth="1.5" strokeLinecap="round"/>
            <line x1="32" y1="24" x2="32" y2="40" stroke="rgba(99,102,241,0.3)" strokeWidth="1.5" strokeLinecap="round"/>
            <line x1="49" y1="49" x2="62" y2="62" stroke="rgba(99,102,241,0.4)" strokeWidth="2.5" strokeLinecap="round"/>
          </svg>
          <div style={{ fontWeight: 700, fontSize: 15, fontFamily: 'var(--font-display)', letterSpacing: '-0.02em' }}>Federated Research Search</div>
          <div style={{ fontSize: 13, color: 'var(--rc-muted)', marginTop: 5 }}>Search across PubMed, Europe PMC and DOAJ. Results are ranked by relevance.</div>
        </div>
      )}

      {batchModalOpen ? (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.35)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20, zIndex: 50 }} onClick={() => setBatchModalOpen(false)}>
          <div className="rc-card" style={{ width: 'min(860px, 96vw)', maxHeight: '85vh', overflow: 'auto' }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'center' }}>
              <div style={{ fontWeight: 900 }}>Batch OA download</div>
              <button className="rc-btn" onClick={() => setBatchModalOpen(false)}>Close</button>
            </div>
            <div style={{ height: 10 }} />
            <div className="rc-help">Job: <span style={{ fontFamily: 'monospace' }}>{batchJobId || '—'}</span></div>
            <div className="rc-help">Status: <b>{batchJob?.status || '—'}</b> · Progress: <b>{batchJob?.progress ?? 0}%</b></div>
            {batchJob?.error ? <div className="rc-error" style={{ marginTop: 8 }}>{String(batchJob.error)}</div> : null}
            <div className="rc-row" style={{ marginTop: 10 }}>
              <button className="rc-btn rc-btn--ghost" disabled={!batchJobId} onClick={cancelBatch}>Cancel job</button>
            </div>
            <div style={{ height: 12 }} />
            <div style={{ fontWeight: 850, marginBottom: 6 }}>Summary</div>
            {batchJob?.output ? (
              <div className="rc-row" style={{ gap: 8 }}>
                <span className="rc-badge rc-badge--success">Downloaded: <b>{batchJob.output?.downloaded?.length ?? 0}</b></span>
                <span className="rc-badge">Already exists: <b>{batchJob.output?.already_exists?.length ?? 0}</b></span>
                <span className="rc-badge">Not available: <b>{batchJob.output?.not_available?.length ?? 0}</b></span>
                <span className="rc-badge rc-badge--danger">Failed: <b>{batchJob.output?.failed?.length ?? 0}</b></span>
              </div>
            ) : (
              <div className="rc-muted">Waiting for job output…</div>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
