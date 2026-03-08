import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
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
  is_open_access?: boolean;
  oa_url?: string | null;
};

type SearchResponse = {
  count: number;
  results: PaperMetadata[];
  query_translation?: string | null;
  cached: boolean;
  sources?: string[];
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

  const [selected, setSelected] = useState<Record<string, boolean>>({});

  const [batchJobId, setBatchJobId] = useState<string | null>(null);
  const [batchJob, setBatchJob] = useState<{ status: string; progress: number; error?: string | null; output?: any } | null>(null);
  const [batchModalOpen, setBatchModalOpen] = useState(false);

  const canSearch = useMemo(() => Boolean(projectId && query.trim().length >= 3), [projectId, query]);

  async function runSearch() {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    try {
      const r = await api.post('/search/federated', {
        project_id: projectId,
        query: query.trim(),
        max_results: maxResults,
      });
      setData(r.data as SearchResponse);
      setSelected({});
      setBatchJobId(null);
      setBatchJob(null);
      setBatchModalOpen(false);
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

      const resp = await api.post('/papers/download', payload);
      const duplicate = Boolean(resp.data?.duplicate);
      toast.info(duplicate ? 'Duplicate' : 'Saved', duplicate ? 'Paper already exists in this project.' : 'Downloaded and saved.');
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Download failed');
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
        const canDownload = Boolean(r.is_open_access) && Boolean(r.doi || r.pmid);
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
      const key = r.doi || r.pmid || String(idx);
      const canDownload = Boolean(r.is_open_access) && Boolean(r.doi || r.pmid);
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
    return () => {
      alive = false;
      if (t) clearTimeout(t);
    };
  }, [batchJobId, batchModalOpen]);

  return (
    <div className="rc-section-shell">
      <div className="rc-hero-card">
        <div style={{ maxWidth: 760 }}>
          <div className="rc-stage-label rc-stage-label--teal">Step 1 · Discover</div>
          <h1 className="rc-page-title" style={{ marginTop: 12 }}>Find the right evidence</h1>
          <div className="rc-subtitle">Search across PubMed, Europe PMC and DOAJ, then move promising papers into the project library.</div>
          <div className="rc-help" style={{ marginTop: 12 }}>
            Use a question-like query, then save OA papers directly. Once you have a core reading list, switch to Reader to ask grounded questions.
          </div>
        </div>
        <div className="rc-metric-grid" style={{ minWidth: 300 }}>
          <div className="rc-metric-tile"><strong>{data?.count ?? '—'}</strong><span>Results</span></div>
          <div className="rc-metric-tile"><strong>{selectedCount}</strong><span>Selected OA papers</span></div>
        </div>
      </div>

      <div className="rc-shelf">
        <div className="rc-card">
          <div className="rc-card-title">Search query</div>
          <div className="rc-row" style={{ alignItems: 'flex-end' }}>
            <div style={{ flex: 1, minWidth: 260 }}>
              <div className="rc-kicker">Research question</div>
              <input className="rc-input" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="e.g. ACL reconstruction hamstring vs BPTB meta-analysis" />
            </div>
            <div style={{ width: 140 }}>
              <div className="rc-kicker">Max results</div>
              <input className="rc-input" type="number" value={maxResults} min={1} max={100} onChange={(e) => setMaxResults(Number(e.target.value))} />
            </div>
            <button className="rc-btn rc-btn--primary" disabled={!canSearch || loading} onClick={runSearch}>
              {loading ? 'Searching…' : 'Search'}
            </button>
          </div>
          <div className="rc-help" style={{ marginTop: 8 }}>Tip: use phrases, outcomes, populations and study types. The app merges duplicate hits across providers.</div>
        </div>

        <div className="rc-next-step">
          <div className="rc-kicker">Suggested next step</div>
          <div style={{ fontWeight: 800, letterSpacing: '-0.02em', marginTop: 4 }}>Build your reading set</div>
          <div className="rc-help" style={{ marginTop: 8 }}>
            Save OA papers first, then open Reader to compare findings with citations. Library keeps the long list; Reader helps you decide what matters.
          </div>
          <div className="rc-row" style={{ marginTop: 12 }}>
            <Link className="rc-btn" to={`/projects/${projectId}/library`}>Open library</Link>
            <Link className="rc-btn rc-btn--primary" to={`/projects/${projectId}/reader`}>Go to reader</Link>
          </div>
        </div>
      </div>

      {error ? <div className="rc-error">{String(error)}</div> : null}

      {data ? (
        <div className="rc-card-list">
          <div className="rc-soft-card">
            <div className="rc-help">
              Results: <b>{data.count}</b> {data.cached ? '(cached)' : ''}
              {data.query_translation ? ` · Translation: ${data.query_translation}` : ''}
              {data.sources?.length ? ` · Sources: ${data.sources.join(', ')}` : ''}
            </div>
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

          <div className="rc-card-list">
            {data.results.map((r, idx) => {
              const key = r.doi || r.pmid || String(idx);
              const canDownload = Boolean(r.is_open_access) && Boolean(r.doi || r.pmid);
              const isSelected = Boolean(selected[key]);
              return (
                <div key={key} className="rc-card" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                    <input type="checkbox" disabled={!canDownload} checked={isSelected} onChange={() => toggleSelect(key)} title={canDownload ? 'Select for batch download' : 'Not eligible for batch download'} style={{ marginTop: 3 }} />
                    <div style={{ fontWeight: 850, flex: 1, lineHeight: 1.25 }}>{r.title}</div>
                    {r.is_open_access ? <span className="rc-badge rc-badge--success">OA</span> : <span className="rc-badge">Closed</span>}
                  </div>

                  <div className="rc-help">
                    {(r.journal || '—')}{r.pub_year ? ` · ${r.pub_year}` : ''}
                    {r.doi ? ` · DOI: ${r.doi}` : ''}
                    {r.pmid ? ` · PMID: ${r.pmid}` : ''}
                  </div>

                  {r.abstract ? <div style={{ fontSize: 13, whiteSpace: 'pre-wrap' }}>{r.abstract}</div> : null}

                  <div className="rc-row">
                    <button className="rc-btn" disabled={!canDownload || downloadingKey === (r.doi || r.pmid || r.title)} onClick={() => downloadOA(r)}>
                      {downloadingKey === (r.doi || r.pmid || r.title) ? 'Downloading…' : 'Download OA PDF'}
                    </button>
                    {r.oa_url ? <a href={r.oa_url} target="_blank" rel="noreferrer">OA link</a> : null}
                    {!r.is_open_access ? <span className="rc-help">Not marked OA by PubMed metadata.</span> : null}
                    {r.is_open_access && !canDownload ? <span className="rc-help">OA, but missing DOI/PMID to resolve PDF.</span> : null}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        <div className="rc-muted">Run a PubMed search to see results.</div>
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
              <div style={{ fontWeight: 900 }}>Batch OA download</div>
              <button className="rc-btn" onClick={() => setBatchModalOpen(false)}>Close</button>
            </div>
            <div style={{ height: 10 }} />
            <div className="rc-help">
              Job: <span style={{ fontFamily: 'monospace' }}>{batchJobId || '—'}</span>
            </div>
            <div className="rc-help">
              Status: <b>{batchJob?.status || '—'}</b> · Progress: <b>{batchJob?.progress ?? 0}%</b>
            </div>
            {batchJob?.error ? <div className="rc-error" style={{ marginTop: 8 }}>{String(batchJob.error)}</div> : null}

            <div className="rc-row" style={{ marginTop: 10 }}>
              <button className="rc-btn rc-btn--ghost" disabled={!batchJobId} onClick={cancelBatch}>
                Cancel job
              </button>
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
