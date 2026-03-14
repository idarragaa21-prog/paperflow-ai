import { Download, ExternalLink, Search as SearchIcon } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../services/api';
import { Skeleton, SkeletonLines } from '../ui/Skeleton/Skeleton';
import { useToast } from '../ui/Toast/ToastProvider';

type PaperMeta = {
  pmid?: string | null; pmcid?: string | null; doi?: string | null;
  title: string; authors?: string[] | null; journal?: string | null;
  pub_year?: number | null; abstract?: string | null;
  is_open_access?: boolean; oa_url?: string | null;
};
type SearchResponse = {
  count: number; results: PaperMeta[];
  query_translation?: string | null; cached: boolean; sources?: string[];
};

const EXAMPLES = [
  { query: 'ACL reconstruction hamstring vs BPTB meta-analysis', label: 'ACL Reconstruction', sub: 'Systematic review · RCT' },
  { query: 'tibial osteotomy return to sport outcomes',          label: 'Tibial Osteotomy',   sub: 'Outcomes research · Cohort' },
  { query: 'hip arthroplasty dislocation risk factors',         label: 'Hip Arthroplasty',   sub: 'Risk factors · Case-control' },
];

function ResultCard({
  r, idx, selected, canDownload, onToggle, onDownload, downloadingKey,
}: {
  r: PaperMeta; idx: number; selected: boolean; canDownload: boolean;
  onToggle: () => void; onDownload: () => void; downloadingKey: string | null;
}) {
  const [expanded, setExpanded] = useState(false);
  const key = r.doi || r.pmid || String(idx);
  const busy = downloadingKey === key;

  const authorsStr = r.authors && r.authors.length > 0
    ? r.authors.slice(0, 3).join(', ') + (r.authors.length > 3 ? ' et al.' : '')
    : null;

  return (
    <div className="rc-result-card">
      <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
        <input
          type="checkbox"
          disabled={!canDownload}
          checked={selected}
          onChange={onToggle}
          style={{ marginTop: 3, accentColor: 'var(--rc-primary)', flexShrink: 0, cursor: canDownload ? 'pointer' : 'not-allowed' }}
        />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{
            fontWeight: 700, fontSize: 14, lineHeight: 1.35, color: 'var(--rc-text)',
            letterSpacing: '-0.01em', display: '-webkit-box',
            WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden',
          }}>
            {r.title}
          </div>
        </div>
        <span className={`rc-tag ${r.is_open_access ? 'rc-tag--green' : 'rc-tag--slate'}`} style={{ flexShrink: 0 }}>
          {r.is_open_access ? 'OA' : 'Closed'}
        </span>
      </div>

      <div style={{ fontSize: 12, color: 'var(--rc-text-tertiary)', display: 'flex', gap: 8, flexWrap: 'wrap', paddingLeft: 24 }}>
        {authorsStr && <span>{authorsStr}</span>}
        {r.journal && <><span style={{ opacity: 0.4 }}>·</span><span style={{ fontStyle: 'italic' }}>{r.journal}</span></>}
        {r.pub_year && <><span style={{ opacity: 0.4 }}>·</span><span>{r.pub_year}</span></>}
        {r.doi && <><span style={{ opacity: 0.4 }}>·</span><span style={{ fontFamily: 'monospace', fontSize: 11 }}>DOI:{r.doi}</span></>}
      </div>

      {r.abstract && (
        <div style={{ paddingLeft: 24 }}>
          <div style={{
            fontSize: 13, color: 'var(--rc-text-secondary)', lineHeight: 1.6,
            display: expanded ? 'block' : '-webkit-box',
            WebkitLineClamp: expanded ? undefined : 3,
            WebkitBoxOrient: 'vertical',
            overflow: expanded ? 'visible' : 'hidden',
          }}>
            {r.abstract}
          </div>
          <button className="rc-btn rc-btn--ghost"
            style={{ padding: '2px 0', fontSize: 11, color: 'var(--rc-primary)', marginTop: 2 }}
            onClick={() => setExpanded(!expanded)}>
            {expanded ? 'Show less' : 'Show more'}
          </button>
        </div>
      )}

      <div style={{ display: 'flex', gap: 7, paddingLeft: 24 }}>
        <button
          className={`rc-btn${r.is_open_access ? '' : ''}`}
          style={{ fontSize: 12, padding: '6px 12px' }}
          disabled={busy || !r.is_open_access}
          title={!r.is_open_access ? 'Not open access' : undefined}
          onClick={r.is_open_access ? onDownload : undefined}
        >
          <Download size={13} /> {busy ? 'Saving…' : 'Save PDF'}
        </button>
        {r.oa_url && (
          <a href={r.oa_url} target="_blank" rel="noreferrer"
            className="rc-btn"
            style={{ fontSize: 12, padding: '6px 12px', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
            <ExternalLink size={12} /> View
          </a>
        )}
      </div>
    </div>
  );
}

export default function SearchPage() {
  const { projectId } = useParams();
  const toast = useToast();

  const [query, setQuery]         = useState('');
  const [maxResults, setMaxResults] = useState(20);
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState<string | null>(null);
  const [data, setData]           = useState<SearchResponse | null>(null);
  const [downloadingKey, setDownloadingKey] = useState<string | null>(null);
  const [selected, setSelected]   = useState<Record<string, boolean>>({});
  const [batchJobId, setBatchJobId] = useState<string | null>(null);
  const [batchJob, setBatchJob]   = useState<any>(null);
  const [batchModalOpen, setBatchModalOpen] = useState(false);

  const canSearch     = useMemo(() => Boolean(projectId && query.trim().length >= 3), [projectId, query]);
  const selectedCount = useMemo(() => Object.values(selected).filter(Boolean).length, [selected]);

  const selectedPapers = useMemo(() => {
    if (!data) return [];
    return data.results
      .map((r, idx) => ({ r, idx }))
      .filter(({ r, idx }) => {
        const key = r.doi || r.pmid || String(idx);
        return selected[key] && r.is_open_access && (r.doi || r.pmid);
      })
      .map(({ r }) => ({ pmid: r.pmid || undefined, pmcid: r.pmcid || undefined, doi: r.doi || undefined, title: r.title }));
  }, [data, selected]);

  async function runSearch(overrideQuery?: string) {
    const q = (overrideQuery ?? query).trim();
    if (!projectId || q.length < 3) return;
    if (overrideQuery) setQuery(overrideQuery);
    setLoading(true); setError(null);
    try {
      const r = await api.post('/search/federated', { project_id: projectId, query: q, max_results: maxResults });
      setData(r.data as SearchResponse);
      setSelected({}); setBatchJobId(null); setBatchJob(null); setBatchModalOpen(false);
    } catch (e: any) { setError(e?.response?.data?.detail || 'Search failed'); }
    finally { setLoading(false); }
  }

  async function downloadOA(r: PaperMeta, idx: number) {
    if (!projectId) return;
    const key = r.doi || r.pmid || String(idx);
    setDownloadingKey(key); setError(null);
    try {
      const payload: any = { project_id: projectId, title: r.title };
      if (r.doi) payload.doi = r.doi;
      if (r.pmid) payload.pmid = r.pmid;
      const resp = await api.post('/papers/download', payload);
      const dup = Boolean(resp.data?.duplicate);
      toast.info(dup ? 'Duplicate' : 'Saved ✓', dup ? 'Already in this project.' : 'PDF downloaded and saved.');
    } catch (e: any) { setError(e?.response?.data?.detail || 'Download failed'); }
    finally { setDownloadingKey(null); }
  }

  function toggleSelect(key: string) { setSelected(prev => ({ ...prev, [key]: !prev[key] })); }

  function selectAllOA() {
    if (!data) return;
    const next: Record<string, boolean> = {};
    data.results.forEach((r, idx) => {
      if (r.is_open_access && (r.doi || r.pmid)) next[r.doi || r.pmid || String(idx)] = true;
    });
    setSelected(next);
  }

  async function startBatchDownload() {
    if (!projectId || !selectedPapers.length) return;
    setError(null);
    try {
      const resp = await api.post('/papers/batch-download', { project_id: projectId, papers: selectedPapers });
      const jid = String(resp.data?.job_id || '');
      setBatchJobId(jid); setBatchJob({ status: 'queued', progress: 0 }); setBatchModalOpen(true);
    } catch (e: any) { setError(e?.response?.data?.detail || 'Batch download failed'); }
  }

  useEffect(() => {
    if (!batchJobId || !batchModalOpen) return;
    let alive = true; let t: any = null;
    async function poll() {
      try {
        const r = await api.get(`/jobs/${batchJobId}`);
        const status = String(r.data?.status || 'queued');
        const progress = Number(r.data?.progress_percent || 0);
        const output = (r.data?.result || {})?.output || (r.data?.result || {})?.rq_result?.output;
        if (alive) setBatchJob({ status, progress, output });
        if (status === 'completed' || status === 'failed') return;
      } catch {}
      t = setTimeout(poll, 1000);
    }
    poll();
    return () => { alive = false; if (t) clearTimeout(t); };
  }, [batchJobId, batchModalOpen]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div>
        <h1 className="rc-page-title">Research Search</h1>
        <div className="rc-subtitle">Federated search across PubMed · EuropePMC · DOAJ with deduplication and OA-aware saving.</div>
      </div>

      {error && <div className="rc-error">{error}</div>}

      <div className="rc-search-layout">
        {/* ── Left: search panel ── */}
        <div className="rc-search-panel">
          <div className="rc-card" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div className="rc-card-title">Query</div>

            <div>
              <div className="rc-kicker">Research question</div>
              <textarea
                className="rc-input rc-textarea"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="e.g. tibial osteotomy return to sport outcomes RCT"
                style={{ minHeight: 88, fontSize: 14, lineHeight: 1.5 }}
                onKeyDown={(e) => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) runSearch(); }}
              />
              <div className="rc-help" style={{ marginTop: 4 }}>⌘+Enter to search</div>
            </div>

            <div>
              <div className="rc-kicker">Max results</div>
              <input
                className="rc-input"
                type="number" value={maxResults} min={1} max={100}
                onChange={(e) => setMaxResults(Number(e.target.value))}
              />
            </div>

            <button
              className="rc-btn rc-btn--primary"
              style={{ width: '100%', justifyContent: 'center', padding: '11px', fontSize: 14 }}
              disabled={!canSearch || loading}
              onClick={() => runSearch()}
            >
              <SearchIcon size={15} />
              {loading ? 'Searching…' : 'Search'}
            </button>

            {/* Results summary + batch */}
            {data && (
              <>
                <div className="rc-divider-h" />
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 13, fontWeight: 650, color: 'var(--rc-text)' }}>
                    {data.count} results
                  </span>
                  <div style={{ display: 'flex', gap: 6 }}>
                    {data.cached && <span className="rc-tag rc-tag--slate">cached</span>}
                    {data.sources?.map(s => <span key={s} className="rc-tag rc-tag--blue">{s}</span>)}
                  </div>
                </div>

                <div className="rc-divider-h" />
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  <div className="rc-kicker">Batch download</div>
                  <div className="rc-row" style={{ gap: 6 }}>
                    <button className="rc-btn" style={{ flex: 1, justifyContent: 'center', fontSize: 12, padding: '7px 10px' }} onClick={selectAllOA}>
                      Select all OA
                    </button>
                    <button className="rc-btn" style={{ fontSize: 12, padding: '7px 10px' }}
                      disabled={selectedCount === 0} onClick={() => setSelected({})}>
                      Clear ({selectedCount})
                    </button>
                  </div>
                  <button
                    className="rc-btn rc-btn--primary"
                    style={{ width: '100%', justifyContent: 'center', fontSize: 13 }}
                    disabled={selectedCount === 0}
                    onClick={startBatchDownload}
                  >
                    <Download size={13} />
                    Download {selectedCount > 0 ? `(${selectedCount})` : 'selected'}
                  </button>
                  {batchJobId && (
                    <button className="rc-btn rc-btn--ghost" style={{ fontSize: 12, justifyContent: 'center', color: 'var(--rc-primary)' }}
                      onClick={() => setBatchModalOpen(true)}>
                      View batch job →
                    </button>
                  )}
                </div>
              </>
            )}
          </div>
        </div>

        {/* ── Right: results ── */}
        <div className="rc-search-results">
          {loading ? (
            <>
              {[1,2,3].map(i => (
                <div key={i} className="rc-card" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  <Skeleton height={14} width="60%" />
                  <SkeletonLines lines={3} lineHeight={12} lastLineWidth="75%" />
                </div>
              ))}
            </>
          ) : data ? (
            data.results.map((r, idx) => {
              const key = r.doi || r.pmid || String(idx);
              const canDownload = Boolean(r.is_open_access) && Boolean(r.doi || r.pmid);
              return (
                <ResultCard
                  key={key} r={r} idx={idx}
                  selected={Boolean(selected[key])}
                  canDownload={canDownload}
                  onToggle={() => toggleSelect(key)}
                  onDownload={() => downloadOA(r, idx)}
                  downloadingKey={downloadingKey}
                />
              );
            })
          ) : (
            /* Empty state with example cards */
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div className="rc-help" style={{ fontSize: 13 }}>
                Run a search to see results. Try one of these examples:
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px,1fr))', gap: 10 }}>
                {EXAMPLES.map((ex) => (
                  <div
                    key={ex.query}
                    className="rc-card rc-card--interactive"
                    style={{ cursor: 'pointer', padding: 14 }}
                    onClick={() => runSearch(ex.query)}
                  >
                    <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 4, color: 'var(--rc-text)' }}>
                      {ex.label}
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--rc-text-tertiary)', marginBottom: 8 }}>{ex.sub}</div>
                    <div style={{ fontSize: 12, color: 'var(--rc-text-secondary)', lineHeight: 1.4 }}>{ex.query}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Batch job modal ── */}
      {batchModalOpen && (
        <div className="rc-overlay" onClick={() => setBatchModalOpen(false)}>
          <div className="rc-modal" onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <span style={{ fontWeight: 800, fontSize: 15 }}>Batch OA download</span>
              <button className="rc-btn rc-btn--ghost" style={{ padding: 6 }} onClick={() => setBatchModalOpen(false)}>✕</button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                <span className={`rc-tag ${batchJob?.status === 'completed' ? 'rc-tag--green' : batchJob?.status === 'failed' ? 'rc-tag--red' : 'rc-tag--blue'}`}>
                  {batchJob?.status || 'queued'}
                </span>
                <span className="rc-help" style={{ fontFamily: 'monospace', fontSize: 11 }}>{batchJobId}</span>
              </div>

              {batchJob?.status !== 'completed' && batchJob?.status !== 'failed' && (
                <div className="rc-progress">
                  <div style={{ width: `${batchJob?.progress ?? 0}%`, background: 'var(--rc-primary)' }} />
                </div>
              )}

              {batchJob?.output && (
                <div className="rc-row" style={{ gap: 7, marginTop: 4 }}>
                  <span className="rc-tag rc-tag--green">Downloaded: {batchJob.output?.downloaded?.length ?? 0}</span>
                  <span className="rc-tag rc-tag--slate">Already exists: {batchJob.output?.already_exists?.length ?? 0}</span>
                  <span className="rc-tag rc-tag--amber">Not available: {batchJob.output?.not_available?.length ?? 0}</span>
                  <span className="rc-tag rc-tag--red">Failed: {batchJob.output?.failed?.length ?? 0}</span>
                </div>
              )}

              <button className="rc-btn rc-btn--ghost" style={{ fontSize: 12, width: 'fit-content' }}
                onClick={async () => { if (batchJobId) { try { await api.post(`/jobs/${batchJobId}/cancel`); } catch {} } }}>
                Cancel job
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
