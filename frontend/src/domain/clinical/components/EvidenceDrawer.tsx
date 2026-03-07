import type { EvidenceSummary } from '../types';

export default function EvidenceDrawer({ summary }: { summary: EvidenceSummary }) {
  return (
    <div className="rc-card">
      <div className="rc-card-title">Evidence</div>

      <div className="rc-row" style={{ gap: 8 }}>
        <span className="rc-badge">Sources: <b>{summary.sourcesCount}</b></span>
        {summary.evidenceStrength && summary.evidenceStrength !== 'na' ? (
          <span className="rc-badge">Strength: <b>{summary.evidenceStrength}</b></span>
        ) : (
          <span className="rc-badge">Strength: <b>N/A</b></span>
        )}
      </div>

      <div style={{ height: 10 }} />
      <div style={{ fontWeight: 850, marginBottom: 6 }}>Citations</div>
      {summary.projectPapers.length === 0 ? <div className="rc-muted">No project papers linked.</div> : null}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {summary.projectPapers.slice(0, 12).map((p) => (
          <div key={p.paper_id} className="rc-card" style={{ padding: 10 }}>
            <div style={{ fontWeight: 850, lineHeight: 1.25 }}>{p.title || p.paper_id}</div>
            <div className="rc-help">
              {p.year ? `${p.year} · ` : ''}
              {p.pmid ? `PMID:${p.pmid} ` : ''}
              {p.doi ? `DOI:${p.doi}` : ''}
              {p.oa ? ' · OA' : ''}
            </div>
          </div>
        ))}
      </div>

      {summary.onlineSources.length ? (
        <>
          <div style={{ height: 12 }} />
          <div style={{ fontWeight: 850, marginBottom: 6 }}>Online sources</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {summary.onlineSources.map((s, i) => (
              <div key={s.label + i} className="rc-help">
                {s.url ? (
                  <a href={s.url} target="_blank" rel="noreferrer">{s.label}</a>
                ) : (
                  <span>{s.label}</span>
                )}
              </div>
            ))}
          </div>
        </>
      ) : null}

      {summary.gaps?.length ? (
        <>
          <div style={{ height: 12 }} />
          <div style={{ fontWeight: 850, marginBottom: 6 }}>Evidence gaps (transparent)</div>
          <ul style={{ margin: 0, paddingLeft: 18 }}>
            {summary.gaps.slice(0, 6).map((g, i) => (
              <li key={i} className="rc-help">{String(g)}</li>
            ))}
          </ul>
        </>
      ) : null}
    </div>
  );
}
