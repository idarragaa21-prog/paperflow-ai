import type { PaperSearchResult } from '../../types/api';
import type { DownloadInfo, UseSearchReturn } from '../../hooks/useSearch';

const SOURCE_LABELS: Record<string, string> = { pubmed: 'PubMed', europepmc: 'Europe PMC', doaj: 'DOAJ' };
const SOURCE_COLORS: Record<string, string> = { pubmed: '#2563eb', europepmc: '#059669', doaj: '#d97706' };

export function DownloadTrace({ info }: { info: DownloadInfo }) {
  const providerLabel =
    info.source_provider === 'user_provided_oa' ? 'Direct OA link'
    : info.source_provider === 'unpaywall' ? 'Unpaywall'
    : info.source_provider === 'europepmc' ? 'Europe PMC'
    : info.source_provider || null;

  if (info.status === 'saved') return (
    <div style={{ fontSize: 12, padding: '5px 8px', borderRadius: 5, background: info.used_fallback ? 'rgba(234,179,8,0.08)' : 'rgba(16,185,129,0.08)', border: `1px solid ${info.used_fallback ? 'rgba(234,179,8,0.25)' : 'rgba(16,185,129,0.2)'}` }}>
      <span style={{ fontWeight: 700, color: info.used_fallback ? '#b45309' : '#059669' }}>
        {info.used_fallback ? '⚠ Downloaded (fallback)' : '✓ Downloaded'}
      </span>
      {providerLabel && <span style={{ color: 'var(--rc-muted)', marginLeft: 8 }}>via {providerLabel}</span>}
      {info.oa_url && <span style={{ color: 'var(--rc-muted)', marginLeft: 8, wordBreak: 'break-all' }}>{info.oa_url}</span>}
      {info.used_fallback && info.original_oa_url && (
        <span style={{ color: 'var(--rc-muted)', marginLeft: 8, wordBreak: 'break-all' }}>
          Original: {info.original_oa_url}
        </span>
      )}
    </div>
  );
  if (info.status === 'duplicate') return (
    <div style={{ fontSize: 12, padding: '5px 8px', borderRadius: 5, background: 'rgba(99,102,241,0.06)', border: '1px solid rgba(99,102,241,0.15)' }}>
      <span style={{ fontWeight: 700, color: '#6366f1' }}>↻ Already in project</span>
    </div>
  );
  return (
    <div style={{ fontSize: 12, padding: '5px 8px', borderRadius: 5, background: 'rgba(239,68,68,0.06)', border: '1px solid rgba(239,68,68,0.15)' }}>
      <span style={{ fontWeight: 700, color: '#ef4444' }}>✗ Failed</span>
      {info.error && <span style={{ color: 'var(--rc-muted)', marginLeft: 6 }}>{info.error}</span>}
    </div>
  );
}

export function SearchResultCard({
  r, idx, search,
}: { r: PaperSearchResult; idx: number; search: UseSearchReturn }) {
  const key = r.doi || r.pmid || String(idx);
  const canDownload = Boolean(r.is_open_access) && Boolean(r.doi || r.pmid || r.oa_url);
  const isSelected = Boolean(search.selected[key]);
  const isExpanded = Boolean(search.expandedAbstracts[key]);
  const dlInfo = search.downloadResults[key];
  const srcColor = SOURCE_COLORS[r.source || ''] || '#6b7280';

  return (
    <div className="rc-card" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
        <input type="checkbox" disabled={!canDownload} checked={isSelected}
          onChange={() => search.setSelected((p) => ({ ...p, [key]: !p[key] }))} style={{ marginTop: 3 }} />
        <div style={{ fontWeight: 850, flex: 1, lineHeight: 1.25 }}>{r.title}</div>
        <div style={{ display: 'flex', gap: 4, flexShrink: 0 }}>
          <span style={{ fontSize: 11, fontWeight: 700, padding: '2px 7px', borderRadius: 4, background: srcColor + '18', color: srcColor, border: `1px solid ${srcColor}40` }}>
            {SOURCE_LABELS[r.source || ''] || r.source || '—'}
          </span>
          {r.is_open_access
            ? <span className="rc-badge rc-badge--success">OA</span>
            : <span className="rc-badge">Closed</span>}
        </div>
      </div>
      <div className="rc-help">
        {r.journal || '—'}{r.pub_year ? ` · ${r.pub_year}` : ''}
        {r.doi ? ` · DOI: ${r.doi}` : ''}{r.pmid ? ` · PMID: ${r.pmid}` : ''}
        {r.relevance_score != null ? ` · Score: ${(r.relevance_score * 100).toFixed(0)}%` : ''}
      </div>
      {r.abstract && (
        <div>
          <div style={{ fontSize: 13, whiteSpace: 'pre-wrap', ...(isExpanded ? {} : { maxHeight: 80, overflow: 'hidden', maskImage: 'linear-gradient(to bottom, black 60%, transparent 100%)', WebkitMaskImage: 'linear-gradient(to bottom, black 60%, transparent 100%)' }) }}>
            {r.abstract}
          </div>
          {r.abstract.length > 200 && (
            <button onClick={() => search.toggleAbstract(key)} style={{ background: 'none', border: 'none', color: 'var(--rc-accent,#6366f1)', cursor: 'pointer', fontSize: 12, fontWeight: 600, padding: '2px 0', marginTop: 2 }}>
              {isExpanded ? 'Show less ▲' : 'Show more ▼'}
            </button>
          )}
        </div>
      )}
      <div className="rc-row" style={{ flexWrap: 'wrap', gap: 6 }}>
        <button className="rc-btn" disabled={!canDownload || search.downloadingKey === key} onClick={() => search.downloadOA(r)}>
          {search.downloadingKey === key ? 'Downloading…' : 'Download OA PDF'}
        </button>
        {r.oa_url && <a href={r.oa_url} target="_blank" rel="noreferrer" style={{ fontSize: 12 }}>OA link ↗</a>}
      </div>
      {dlInfo && <DownloadTrace info={dlInfo} />}
    </div>
  );
}
